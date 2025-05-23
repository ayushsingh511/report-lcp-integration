import streamlit as st
import subprocess
import os
import time
from pathlib import Path
import json
import pandas as pd
from datetime import datetime
import re
from urllib.parse import urlparse

# Page configuration
st.set_page_config(
    page_title="UI for Report and Agent",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton>button {
        background-color: #0066cc;
        color: white;
        font-weight: 500;
        border-radius: 4px;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #0052a3;
    }
    .success-box {
        padding: 12px;
        border-radius: 4px;
        background-color: #f0f9ff;
        border: 1px solid #0066cc;
        color: #0066cc;
        margin: 12px 0;
    }
    .info-box {
        padding: 12px;
        border-radius: 4px;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        color: #495057;
        margin: 12px 0;
    }
    .main > div {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("UI for Report and Agent")
st.markdown("---")

# Main layout - single column
col1, col2 = st.columns([3, 1])

with col1:
    # URL input
    url = st.text_input(
        "Website URL",
        placeholder="https://example.com",
        help="Enter the website URL you want to optimize"
    )
    
    # Device selection
    device = st.radio(
        "Device Type",
        ["mobile", "desktop"],
        horizontal=True,
        help="Choose device profile for analysis"
    )
    
    # Model and options in columns
    opt_col1, opt_col2 = st.columns(2)
    
    with opt_col1:
        st.markdown("**Model Selection**")
        model = "gpt-4o"  # Default model
        st.checkbox("GPT-4o", value=True, disabled=True)
        
    with opt_col2:
        st.markdown("**Options**")
        skip_cache = st.checkbox("Skip Cache", help="Fetch fresh data instead of using cache")
        headless = st.checkbox("Headless Mode", value=True, help="Run browser in background")
    
    # Run button
    if st.button("Run Performance Optimization", type="primary", use_container_width=True):
        if not url:
            st.error("Please enter a website URL")
        else:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            
            # Create progress container
            progress_container = st.container()
            
            with progress_container:
                st.markdown("### Running Pipeline")
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                output_area = st.empty()
                
                # Build command
                cmd = [
                    "python", "run.py", "pipeline",
                    "--url", url,
                    "--device", device,
                    "--model", model
                ]
                
                if skip_cache:
                    cmd.append("--skip-cache")
                
                if headless:
                    cmd.append("--headless")
                
                # Run the pipeline
                try:
                    # Phase 1: Report Generation
                    progress_bar.progress(20)
                    status_text.text("Generating performance report...")
                    
                    # Execute command
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )
                    
                    # Capture output in real-time
                    output_lines = []
                    report_path = None
                    suggestions_count = 0
                    performance_results = {}
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            output_lines.append(line.strip())
                            
                            # Update progress based on output
                            if "Generating performance report" in line:
                                progress_bar.progress(30)
                                status_text.text("Analyzing website performance...")
                            elif "Report generated:" in line:
                                progress_bar.progress(40)
                                status_text.text("Report generated!")
                                # Extract report path
                                if "reports/" in line:
                                    report_path = line.split("reports/")[1].strip()
                            elif "Fetching website assets" in line:
                                progress_bar.progress(50)
                                status_text.text("Downloading website assets...")
                            elif "Found" in line and "suggestions" in line:
                                progress_bar.progress(60)
                                # Extract number of suggestions
                                match = re.search(r'Found (\d+) suggestions', line)
                                if match:
                                    suggestions_count = int(match.group(1))
                                status_text.text(f"Found {suggestions_count} optimization suggestions")
                            elif "Applying" in line and "suggestions" in line:
                                progress_bar.progress(70)
                                status_text.text("Applying optimizations...")
                            elif "Applied suggestion in branch:" in line:
                                progress_bar.progress(80)
                                status_text.text("Testing performance improvements...")
                            elif "Original LCP:" in line:
                                match = re.search(r'Original LCP: (\d+)ms', line)
                                if match:
                                    performance_results['original'] = int(match.group(1))
                            elif "perf-fix-" in line and "LCP:" in line:
                                # Parse performance results
                                match = re.search(r'(perf-fix-\d+) LCP: (\d+)ms.*?([\+\-]\d+)ms.*?([\+\-][\d\.]+)%', line)
                                if match:
                                    branch = match.group(1)
                                    lcp = int(match.group(2))
                                    improvement = match.group(3)
                                    percent = match.group(4)
                                    performance_results[branch] = {
                                        'lcp': lcp,
                                        'improvement': improvement,
                                        'percent': percent
                                    }
                            
                            # Show last few lines of output
                            if len(output_lines) > 10:
                                output_area.code('\n'.join(output_lines[-10:]), language='text')
                    
                    # Wait for process to complete
                    process.wait()
                    
                    progress_bar.progress(100)
                    status_text.text("Pipeline completed!")
                    
                    # Display results
                    st.success("Optimization Complete")
                    
                    # Show performance improvements
                    if performance_results:
                        st.markdown("### Performance Results")
                        
                        # Create a dataframe for results
                        if 'original' in performance_results:
                            original_lcp = performance_results['original']
                            
                            # Results table
                            results_data = []
                            results_data.append({
                                'Version': 'Original',
                                'LCP (ms)': original_lcp,
                                'Improvement': '-',
                                'Percentage': '-'
                            })
                            
                            for branch, data in performance_results.items():
                                if branch != 'original':
                                    results_data.append({
                                        'Version': branch.replace('perf-fix-', 'Optimization '),
                                        'LCP (ms)': data['lcp'],
                                        'Improvement': data['improvement'] + 'ms',
                                        'Percentage': data['percent'] + '%'
                                    })
                            
                            df = pd.DataFrame(results_data)
                            st.dataframe(df, use_container_width=True)
                            
                            # Save results to CSV
                            # Create final_output directory
                            final_output_dir = Path("final_output")
                            final_output_dir.mkdir(exist_ok=True)
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            hostname = urlparse(url).hostname or "unknown"
                            
                            # Create domain-specific subdirectory
                            domain_dir = final_output_dir / hostname
                            domain_dir.mkdir(exist_ok=True)
                            
                            csv_filename = domain_dir / f"performance_results_{timestamp}.csv"
                            
                            # Create CSV data
                            csv_data = []
                            csv_data.append({
                                'version': 'Original',
                                'branch': 'master',
                                'lcp_ms': original_lcp,
                                'improvement_ms': 0,
                                'improvement_percent': 0.0
                            })
                            
                            for branch, data in performance_results.items():
                                if branch != 'original':
                                    idx = branch.replace('perf-fix-', '')
                                    csv_data.append({
                                        'version': f'Optimization {idx}',
                                        'branch': branch,
                                        'lcp_ms': data['lcp'],
                                        'improvement_ms': int(data['improvement'].strip('ms+-')),
                                        'improvement_percent': float(data['percent'].strip('%+'))
                                    })
                            
                            # Save to CSV
                            df_csv = pd.DataFrame(csv_data)
                            df_csv.to_csv(csv_filename, index=False)
                            
                            # Best improvement
                            best_branch = min(
                                [b for b in performance_results if b != 'original'],
                                key=lambda x: performance_results[x]['lcp'],
                                default=None
                            )
                            
                            if best_branch:
                                best_data = performance_results[best_branch]
                                improvement_percent = float(best_data['percent'].strip('%+'))
                                
                                if improvement_percent > 0:
                                    st.markdown(f"""
                                    <div class="success-box">
                                    <strong>Best Result: {abs(improvement_percent):.1f}% Improvement</strong><br>
                                    LCP reduced from {original_lcp}ms to {best_data['lcp']}ms
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            # Show CSV saved message
                            st.markdown(f"""
                            <div class="info-box">
                            <strong>Results saved to:</strong> {csv_filename}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Create comprehensive summary
                            summary = {
                                'url': url,
                                'device': device,
                                'model': model,
                                'timestamp': timestamp,
                                'performance_results': csv_data,
                                'suggestions_count': suggestions_count
                            }
                            
                            summary_filename = domain_dir / f"optimization_summary_{timestamp}.json"
                            with open(summary_filename, 'w') as f:
                                json.dump(summary, f, indent=2)
                            
                            # Check if structured suggestions were saved and copy them
                            output_dir = Path(f"output/{hostname}")
                            if output_dir.exists():
                                suggestions_json = output_dir / "parsed_suggestions.json"
                                if suggestions_json.exists():
                                    import shutil
                                    dest_suggestions = domain_dir / f"parsed_suggestions_{timestamp}.json"
                                    shutil.copy2(suggestions_json, dest_suggestions)
                                    st.markdown(f"""
                                    <div class="info-box">
                                    <strong>Structured suggestions saved to:</strong> {dest_suggestions}
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="success-box">
                            <strong>All results saved to:</strong> final_output/{hostname}/
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Show report location
                    if report_path:
                        st.markdown(f"""
                        <div class="info-box">
                        <strong>Report saved to:</strong> reports/{report_path}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Output details
                    with st.expander("View Full Output"):
                        st.code('\n'.join(output_lines), language='text')
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.code(str(e), language='text')

with col2:
    # Check environment
    st.markdown("**Environment Status**")
    env_status = "Configured" if os.path.exists(".env") else "Not Found"
    if env_status == "Configured":
        st.success(env_status)
    else:
        st.error(env_status) 