import asyncio
from playwright.async_api import async_playwright

async def main():
    # The JavaScript we want to serve instead of the original remote file
    patched_js_content = """
        console.log("[Patched JS] This file has been overridden by Playwright!");
        // original code could be appended or replaced entirely
        // ...
    """

    root = "https://www.ups.com/us/en/home"

    async with async_playwright() as p:
        # Launch Chrome, Edge, or Chromium with devtools open
        # (Playwright calls it 'chromium' even when using Chrome/Edge executables)
        browser = await p.chromium.launch(
            headless=False,
            args=["--auto-open-devtools-for-tabs"]
        )
        context = await browser.new_context()

        page = await context.new_page()

        # Define a route handler to intercept JS requests
        async def route_js(route, request):
            url = request.url
            # Check if it's a JS file you want to override
            if (root == url):
                print('requested', root)
                original_response = await route.fetch()

                # 3. Read the original text
                original_body = await original_response.text()

                # 4. Prepend your log statement or any other code
                patched_body = (
                    original_body
                     + """
                        <script>
                            window.setTimeout(() => {
                                const s = document.createElement('script');
                                s.id='hlx-report';
                                s.src='https://main--hlxplayground--kptdobe.hlx.live/tools/report/report.js';
                                if(document.getElementById('hlx-report')) document.getElementById('hlx-report').replaceWith(s);
                                else document.head.append(s);
                            }, 10000);
                        </script>
                       """
                )

                # 5. Fulfill the request with the patched body
                #    Keep as many original response details as possible
                #    Note: We remove certain headers that can conflict (like content-length)
                # headers = [
                #     { "name": name, "value": value }
                #     for name, value in original_response.headers.items()
                #     if name.lower() not in ["content-length", "content-encoding"]
                # ]
                
                await route.fulfill(
                    status=original_response.status,
                    # headers=headers,
                    content_type="text/html",
                    body=patched_body
                )
            elif url.endswith(".js"):
                # print(f"Intercepting JS request: {url}")
                # # Fulfill with custom content
                # await route.fulfill(
                #     status=200,
                #     content_type="application/javascript",
                #     body=patched_js_content
                # )
                # print(f"Intercepting JS request: {url}")

                # 2. Fetch the original response from the server
                original_response = await route.fetch()

                # 3. Read the original text
                original_body = await original_response.text()

                # 4. Prepend your log statement or any other code
                patched_body = (
                    "console.log('[Patched JS] I\\'m patched!');\n"
                    + original_body
                )

                # 5. Fulfill the request with the patched body
                #    Keep as many original response details as possible
                #    Note: We remove certain headers that can conflict (like content-length)
                # headers = [
                #     { "name": name, "value": value }
                #     for name, value in original_response.headers.items()
                #     if name.lower() not in ["content-length", "content-encoding"]
                # ]
                
                await route.fulfill(
                    status=original_response.status,
                    # headers=headers,
                    content_type="application/javascript",
                    body=patched_body
                )
            else:
                # Let all other requests pass through
                await route.continue_()

        # Set up the route; '**/*' means intercept all requests, but
        # you can filter more specifically, e.g. '**/path/to/original.js'
        await page.route("**/*", route_js)

        # Navigate to the target page
        await page.goto(root)

        # Wait or interact as needed; you can measure performance or run Lighthouse here.
        # For example, you might wait a bit or do a typical user flow:
        await page.wait_for_timeout(60000)  # 5 seconds to observe logs

        # If you want to see console logs or measure times, you can attach
        # an event listener, or directly call the performance API in the page.

        # Close the browser
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())