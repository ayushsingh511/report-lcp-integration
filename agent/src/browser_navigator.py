import asyncio
from playwright.async_api import async_playwright
import argparse
from typing import Dict, Any
import datetime
import json
from pathlib import Path
from urllib.parse import urlparse, urljoin

# Import the new function
from agent.src.utils import url_to_folder_name

# Device configurations
CONFIGS = {
    'desktop': {
        'viewport': {
            'width': 1920,
            'height': 1080,
            'deviceScaleFactor': 1,
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'cpu_throttling': 1,  # No throttling
        'network_conditions': {
            'offline': False,
            'latency': 0,
            'downloadThroughput': -1,  # No limit
            'uploadThroughput': -1     # No limit
        }
    },
    'mobile': {
        'viewport': {
            'width': 412,
            'height': 915,
            'deviceScaleFactor': 2.625,
            'isMobile': True,
            'hasTouch': True
        },
        'user_agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
        'cpu_throttling': 20,  # 20x slowdown
        'network_conditions': {
            'offline': False,
            'latency': 150,  # 200ms for Slow 4G
            'downloadThroughput': 1 * 1024 * 1024 / 8,  # 1Mbps for Slow 4G
            'uploadThroughput': 384 * 1024 / 8  # 384Kbps for Slow 4G
        }
    }
}

class BrowserNavigator:
    
    def __init__(self, url: str = None, device: str = 'desktop', headless: bool = False, auto_save_assets: bool = False, serve_cached_assets: bool = False):
        self.url = url
        self.device = device
        self.headless = headless
        self.config = CONFIGS[device]
        self.browser = None
        self.context = None
        self.page = None
        self.client = None
        self.playwright = None
        self.auto_save_assets = auto_save_assets
        self.serve_cached_assets = serve_cached_assets

    async def setup(self):
        """Setup browser instance"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--start-maximized',
                '--enable-features=LocalOverrides',
                '--auto-open-devtools-for-tabs'
            ]
        )
        self.context = await self.browser.new_context(
            viewport=self.config['viewport'],
            user_agent=self.config['user_agent'],
            extra_http_headers={
                "Accept-Encoding": "gzip, deflate",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "max-age=0"
            }
        )
        self.page = await self.context.new_page()
        self.client = await self.page.context.new_cdp_session(self.page)
        await self._setup_cdp()
        await self.setup_route_handler(self.page)
        return self

    async def _setup_cdp(self):
        """Setup CDP"""
        await self.client.send("Performance.enable")
        await self.client.send('Network.enable')
        await self.client.send('Emulation.setCPUThrottlingRate', {
            'rate': self.config['cpu_throttling']
        })
        await self.client.send('Network.emulateNetworkConditions', 
                             self.config['network_conditions'])

    def ensure_output_dirs(self, timestamp):
        """Create output directories if they don't exist"""
        output_dir = Path("output")
        timestamp_dir = output_dir / timestamp
        for dir_path in [output_dir, timestamp_dir]:
            dir_path.mkdir(exist_ok=True)
        return timestamp_dir

    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def setup_route_handler(self, page, inject_script=None):
        """Set up route handling for JavaScript interception"""
        async def handle_js_css(route):
            try:
                request = route.request
                response = await route.fetch()
                headers = {**response.headers}
                headers['Timing-Allow-Origin'] = '*'

                resource_hostname = urlparse(request.url).hostname
                root_hostname = urlparse(self.url).hostname

                if request.resource_type in ["script", "stylesheet"]:
                    if self.serve_cached_assets and resource_hostname == root_hostname:
                        # load the cached asset and serve it
                        folder_name = url_to_folder_name(self.url)
                        output_dir = self.ensure_output_dirs(folder_name)
                        path = urlparse(request.url).path.lstrip('/')
                        full_path = output_dir / "assets" / path
                        cached_asset_exists = full_path.exists()
                        if cached_asset_exists:
                            print(f"Serving cached asset from: {full_path}")
                            with open(full_path, "r", encoding='utf-8') as f:
                                body = f.read().encode('utf-8')

                            return await route.fulfill(
                                status=200,
                                headers=headers,
                                body=body
                            )   
                            
                    body = await response.body()
                    
                    if self.auto_save_assets and resource_hostname != root_hostname:
                        print(f"Skipping {request.url} because it's from another domain.")

                    if self.auto_save_assets and resource_hostname == root_hostname:
                        folder_name = url_to_folder_name(self.url)
                        output_dir = self.ensure_output_dirs(folder_name)
                        path = urlparse(request.url).path.lstrip('/')
                        full_path = output_dir / "assets" / path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(full_path, "wb") as f:
                            f.write(body)
                            print(f"Saved file: {full_path}.")

                    await route.fulfill(
                        status=response.status,
                        headers=headers,
                        body=body
                    )
            except Exception as e:
                # Handle cases where browser/page is closed
                if "Target page, context or browser has been closed" in str(e):
                    # Silently ignore - this is expected during shutdown
                    pass
                elif "Target closed" in str(e):
                    # Another variant of the closed error
                    pass
                else:
                    # Log other unexpected errors
                    print(f"Error in route handler: {str(e)}")
                    # Try to abort the route if possible
                    try:
                        await route.abort()
                    except:
                        pass

        await page.route("**/*.js", handle_js_css)
        await page.route("**/*.css", handle_js_css)

    async def capture_performance_data(self):
        """Capture performance metrics and data"""
        metrics = await self.client.send("Performance.getMetrics")
        perf_data = await self.page.evaluate("window.PERFORMANCE_REPORT_DATA")
        while perf_data is None:
            print("Waiting for performance data...")
            await asyncio.sleep(1)
            metrics = await self.client.send("Performance.getMetrics")
            perf_data = await self.page.evaluate("window.PERFORMANCE_REPORT_DATA")
        return metrics, perf_data

    async def eval_performance(self, output_dir):
        print(f"\nNavigating to {self.url} with {self.device} configuration...")
        response = await self.page.goto(self.url, wait_until="load")

        """Evaluate performance report script"""
        await self.page.evaluate("""
            window.setTimeout(() => {
                const s = document.createElement('script');
                s.id='hlx-report';
                s.src='https://main--hlxplayground--kptdobe.hlx.live/tools/report/report.js';
                if(document.getElementById('hlx-report')) document.getElementById('hlx-report').replaceWith(s);
                else document.head.append(s);
            }, 6000);
        """)

        # Wait and collect performance data
        await self.page.wait_for_timeout(10000)
        metrics, perf_data = await self.capture_performance_data()
        
        # Save performance report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        perf_report_path = output_dir / f"performance_report_{timestamp}.json"
        with open(perf_report_path, 'w') as f:
            json.dump(perf_data, f, indent=2)
        print(f"\nPerformance report saved to: {perf_report_path}")

        return perf_data, metrics, response

async def navigate_to_url(url: str, device: str = 'desktop', headless: bool = False) -> None:
    """Navigate to URL and collect performance data"""
    try:
        navigator = BrowserNavigator(url, device, headless, 
                                     auto_save_assets=True,
                                     serve_cached_assets=False)
        await navigator.setup()

        folder_name = url_to_folder_name(url)
        output_dir = navigator.ensure_output_dirs(folder_name)

        # inject performance report script
        perf_data, metrics, response = await navigator.eval_performance(output_dir=output_dir)
        
        # Print configuration and basic information
        print(f"\nDevice Configuration:")
        print(f"- Profile: {device}")
        print(f"- Viewport: {navigator.config['viewport']['width']}x{navigator.config['viewport']['height']}")
        print(f"- Scale Factor: {navigator.config['viewport']['deviceScaleFactor']}")
        print(f"- CPU Throttling: {navigator.config['cpu_throttling']}x")
        print(f"- Network Latency: {navigator.config['network_conditions']['latency']}ms")
        
        print(f"\nPage Information:")
        print(f"- Title: {await navigator.page.title()}")
        print(f"- Status: {response.status if response else 'Unknown'}")

        print("\nPerformance Metrics:")
        print(f"- DOM Content Loaded: {metrics['metrics'][3]['value']:.2f}ms")
        print(f"- First Paint: {metrics['metrics'][5]['value']:.2f}ms")
        
        # Save page content
        page_content = await navigator.page.content()
        page_dom_path = output_dir / "page_dom.html"
        with open(page_dom_path, "w") as f:
            f.write(page_content)
        print(f"\nPage content saved to: {page_dom_path}")
        
        if not headless:
            print("\nPress Enter to close the browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)
        else:
            # Allow time for any pending requests to complete
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await navigator.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Navigate to a URL using Playwright')
    parser.add_argument('url', help='The URL to navigate to')
    parser.add_argument('--device', choices=['desktop', 'mobile'], default='desktop',
                      help='Device profile to use (default: desktop)')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    asyncio.run(navigate_to_url(args.url, args.device, args.headless))
    # asyncio.run(navigate_to_url("https://www.ups.com/us/en/home", "desktop", False))
    # asyncio.run(navigate_to_url("https://www.petplace.com/us/en/home", "desktop", False))