import argparse
import os
from typing import Optional
from crewai.flow.flow import Flow, listen, router, start, FlowState
from pydantic import BaseModel
import asyncio
import json
from playwright.async_api import async_playwright
from perf_crew import PerfCrew
from agent.src.browser_navigator import BrowserNavigator
from agent.src.utils import url_to_folder_name
from urllib.parse import urlparse, urljoin
import datetime

from agent.src.lcp_filter_tool import LCPFilterTool
import uuid
from pydantic import Field

class PerfCrewFlowState(FlowState):
    url : str = "https://www.ups.com/us/en/home"
    device: str = "mobile"
    headless: bool = False
    report: str = ""
    feedback: Optional[str] = None
    valid: bool = False
    retry_count: int = 0

class PerfCrewFlow(Flow[PerfCrewFlowState]):

    MAX_RETRIES = 0
    
    async def get_webpage_content_and_measure_performance(self):
        
        try:
            url = self.state.url
            navigator = BrowserNavigator(url, self.state.device, self.state.headless, 
                                        auto_save_assets=True)
            await navigator.setup()

            root_hostname = url_to_folder_name(url)
            output_dir = navigator.ensure_output_dirs(root_hostname)

            # inject performance report script
            perf_data, metrics, response = await navigator.eval_performance(output_dir=output_dir)
            
            # Print configuration and basic information
            print(f"\nDevice Configuration:")
            print(f"- Profile: {self.state.device}")
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

            report = sorted(perf_data.get("data"), key=lambda x: (x['start'], x['end']))

            return report, metrics, response
        finally:
            await navigator.close()

    async def retest_performance_with_changed_local_files(self):
        try:    
            url = self.state.url
            navigator = BrowserNavigator(url, self.state.device, self.state.headless, 
                                        auto_save_assets=False,
                                        serve_cached_assets=True)
            await navigator.setup()

            root_hostname = url_to_folder_name(url)
            output_dir = navigator.ensure_output_dirs(root_hostname)

            # inject performance report script
            perf_data, metrics, response = await navigator.eval_performance(output_dir=output_dir)
            report = sorted(perf_data.get("data"), key=lambda x: (x['start'], x['end']))

            print("\nPerformance Metrics:")
            print(f"- DOM Content Loaded: {metrics['metrics'][3]['value']:.2f}ms")
            print(f"- First Paint: {metrics['metrics'][5]['value']:.2f}ms")

            return report, metrics, response
        finally:
            await navigator.close()

    @start("retry")
    async def run_perf_report(self):
        print("Running performance report collection")
        if self.state.retry_count == 0:
            report, metrics, response = await self.get_webpage_content_and_measure_performance()
        else:
            report, metrics, response = await self.retest_performance_with_changed_local_files()

        self.state.report = report
        return "analyze"

    @router(run_perf_report)
    async def analyze_performance(self):
        starting_lcp_score = LCPFilterTool.extract_lcp_score(self.state.report)
        print(f"Improving LCP score which is {starting_lcp_score}")

        result = PerfCrew().crew().kickoff(
            inputs={
                "issue": "keep the LCP fast", 
                "report": LCPFilterTool.extract_lcp_events(self.state.report)
                }
        )
        
        # Store the analysis result
        if hasattr(result, 'raw'):
            self.state.feedback = result.raw
        
        # Run playwright again to verify improvements
        report, metrics, response = await self.retest_performance_with_changed_local_files()
        final_lcp_score = LCPFilterTool.extract_lcp_score(report)
        print(f"Final LCP score is {final_lcp_score}")

        # TODO: save what was done and the result for future fine-tuning
        
        if self.state.retry_count >= self.MAX_RETRIES:
            return "max_retry_exceeded"
            
        self.state.retry_count += 1
        
        # Check if we've made improvements
        if final_lcp_score < starting_lcp_score:
            print(f"✅ LCP improved by {starting_lcp_score - final_lcp_score}ms!")
            return "complete"
        else:
            print(f"❌ No improvement detected. Original: {starting_lcp_score}ms, Final: {final_lcp_score}ms")
            return "max_retry_exceeded"

    @listen("complete")
    async def save_result(self):
        print("Performance analysis is complete")

        # Save the report to a markdown file
        with open("perf_report_completed.md", "w") as file:
            file.write(json.dumps(self.state.report, indent=2))

    @listen("max_retry_exceeded")
    async def max_retry_exceeded_exit(self):
        print("Max retry count exceeded")
        report, metrics, response = await self.retest_performance_with_changed_local_files()
        self.state.report = report

        # Save the report to a markdown file
        report_filename = os.path.join("output", "perf_report_stopped.md")
        with open(report_filename, "w") as file:
            file.write(json.dumps(self.state.report, indent=2))

        print(f"Final report saved to {report_filename}.")

async def kickoff_standalone(initial_state):
    perf_crew_flow = PerfCrewFlow(
        url=initial_state.url,
        device=initial_state.device,
        headless=initial_state.headless
    )
    assert perf_crew_flow.state.url == initial_state.url
    assert perf_crew_flow.state.device == initial_state.device
    assert perf_crew_flow.state.headless == initial_state.headless
    await perf_crew_flow.kickoff_async()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Investigate CWV performance of a URL ')
    parser.add_argument('url', help='The URL to navigate to')
    parser.add_argument('--device', choices=['desktop', 'mobile'], default='desktop',
                      help='Device profile to use (default: desktop)')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    # initial_state = PerfCrewFlowState(url='https://www.ups.com/us/en/home', device='desktop', headless=False)
    initial_state = PerfCrewFlowState(url='https://pgatour.com', device='desktop', headless=False)
    try:
        args = parser.parse_args()
        initial_state = PerfCrewFlowState(url=args.url, device=args.device, headless=args.headless)
    except Exception as e:
        print(f"Warning: {e}")
        print(f"Usage: {parser.format_usage()}")
        print(f"Available devices: {', '.join(['desktop', 'mobile'])}")
        print(f"Available options:")
        print(f"  --device: {parser.get_default('device')}")
        #exit(1)
    finally:
        print(f"Initial state: {initial_state}")
        asyncio.run(kickoff_standalone(initial_state))