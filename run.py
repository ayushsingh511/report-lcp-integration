#!/usr/bin/env python3
"""
Flow - Unified entry point for web performance analysis and optimization
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_report(args):
    """Run the JavaScript report generation tool"""
    cmd = [
        "node", "report/index.js",
        "--action", args.action,
        "--url", args.url,
        "--device", args.device
    ]
    
    if args.skip_cache:
        cmd.append("--skip-cache")
    
    if args.model:
        cmd.extend(["--model", args.model])
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

def apply_report(args):
    """Apply performance suggestions from a report"""
    # Import here to avoid issues if dependencies aren't installed
    from agent.report_apply_flow import ReportApplyFlow
    import asyncio
    
    flow = ReportApplyFlow(
        report_path=args.report_path,
        url=args.url,
        device=args.device,
        headless=args.headless
    )
    
    asyncio.run(flow.run())

def run_agent_script(args):
    """Run the original agent scripts"""
    os.chdir("agent")
    
    if args.script == "perf_crew_flow":
        cmd = ["python", "perf_crew_flow.py", args.url]
    elif args.script == "browser_navigator":
        cmd = ["python", "src/browser_navigator.py", args.url]
    else:
        print(f"Unknown script: {args.script}")
        return
    
    if args.device:
        cmd.extend(["--device", args.device])
    
    if args.headless:
        cmd.append("--headless")
    
    subprocess.run(cmd)
    os.chdir("..")

def run_pipeline(args):
    """Run the complete pipeline: generate report and apply suggestions"""
    import time
    from pathlib import Path
    from agent.report_apply_flow import ReportApplyFlow
    import asyncio
    
    print("🚀 Starting automated performance optimization pipeline")
    print(f"📍 Target URL: {args.url}")
    print(f"📱 Device: {args.device}")
    print(f"🤖 Model: {args.model or 'default'}")
    print("-" * 60)
    
    # Step 1: Generate the report
    print("\n📊 Step 1: Generating performance report...")
    report_cmd = [
        "node", "report/index.js",
        "--action", "prompt",
        "--url", args.url,
        "--device", args.device
    ]
    
    if args.skip_cache:
        report_cmd.append("--skip-cache")
    
    if args.model:
        report_cmd.extend(["--model", args.model])
    
    print(f"Running: {' '.join(report_cmd)}")
    result = subprocess.run(report_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error generating report: {result.stderr}")
        return
    
    # Extract the report path from the output
    report_path = None
    for line in result.stdout.split('\n'):
        if 'Report saved to:' in line or 'reports/' in line:
            # Try to find the path
            parts = line.split()
            for part in parts:
                if 'reports/' in part and '.md' in part:
                    report_path = part.strip()
                    break
    
    # If we couldn't find it in output, look for the most recent report
    if not report_path:
        reports_dir = Path("reports")
        if reports_dir.exists():
            # Get the most recent .summary.md file
            md_files = list(reports_dir.glob("*.summary.md"))
            if md_files:
                report_path = str(max(md_files, key=lambda p: p.stat().st_mtime))
    
    if not report_path or not Path(report_path).exists():
        print("❌ Could not find generated report. Please check the output.")
        return
    
    print(f"✅ Report generated: {report_path}")
    
    # Optional delay to ensure file is fully written
    time.sleep(2)
    
    # Step 2: Apply the suggestions
    print(f"\n🔧 Step 2: Applying performance suggestions...")
    print(f"📄 Using report: {report_path}")
    
    try:
        flow = ReportApplyFlow(
            report_path=report_path,
            url=args.url,
            device=args.device,
            headless=args.headless
        )
        
        asyncio.run(flow.run())
        
        print("\n✅ Pipeline completed successfully!")
        print("\n📈 Summary:")
        print(f"- Report: {report_path}")
        print(f"- Optimized assets: output/{urlparse(args.url).hostname}/")
        print(f"- Git branches created: perf-fix-1 through perf-fix-N")
        print("\nNext steps:")
        print("1. Review the changes in each git branch")
        print("2. Deploy the most effective optimizations")
        print("3. Test in production environment")
        
    except Exception as e:
        print(f"❌ Error applying suggestions: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(
        description="Flow - Web Performance Analysis and Optimization Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a performance report
  python run.py report --url https://example.com --device mobile
  
  # Apply suggestions from a report
  python run.py apply --report reports/example-com.mobile.report.gpt4o.summary.md --url https://example.com
  
  # Run the complete pipeline (report + apply)
  python run.py pipeline --url https://example.com --device mobile --model gpt-4o
  
  # Run browser navigator directly
  python run.py agent --script browser_navigator --url https://example.com
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Report generation command
    report_parser = subparsers.add_parser("report", help="Generate performance report")
    report_parser.add_argument("--url", required=True, help="URL to analyze")
    report_parser.add_argument("--action", default="report", help="Action to perform")
    report_parser.add_argument("--device", choices=["mobile", "desktop"], default="mobile")
    report_parser.add_argument("--skip-cache", action="store_true", help="Skip cache")
    report_parser.add_argument("--model", help="LLM model to use")
    
    # Apply suggestions command
    apply_parser = subparsers.add_parser("apply", help="Apply performance suggestions")
    apply_parser.add_argument("--report", dest="report_path", required=True, help="Path to report file")
    apply_parser.add_argument("--url", required=True, help="URL of the website")
    apply_parser.add_argument("--device", choices=["mobile", "desktop"], default="desktop")
    apply_parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    
    # Pipeline command (new!)
    pipeline_parser = subparsers.add_parser("pipeline", help="Run complete pipeline (report + apply)")
    pipeline_parser.add_argument("--url", required=True, help="URL to analyze and optimize")
    pipeline_parser.add_argument("--device", choices=["mobile", "desktop"], default="mobile")
    pipeline_parser.add_argument("--model", help="LLM model to use (e.g., gpt-4o, gemini-2.0-flash-exp)")
    pipeline_parser.add_argument("--skip-cache", action="store_true", help="Skip cache for report generation")
    pipeline_parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    
    # Agent scripts command
    agent_parser = subparsers.add_parser("agent", help="Run agent scripts")
    agent_parser.add_argument("--script", required=True, help="Script to run (perf_crew_flow, browser_navigator)")
    agent_parser.add_argument("--url", required=True, help="URL to process")
    agent_parser.add_argument("--device", choices=["mobile", "desktop"], default="desktop")
    agent_parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Execute the appropriate command
    if args.command == "report":
        run_report(args)
    elif args.command == "apply":
        apply_report(args)
    elif args.command == "pipeline":
        run_pipeline(args)
    elif args.command == "agent":
        run_agent_script(args)

if __name__ == "__main__":
    main() 