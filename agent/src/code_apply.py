import os
import re
import uuid
import argparse
import yaml
from crewai import LLM
from agent.src.utils import read_report_with_check
from agent.src.parse_report import convert_to_yaml, parse_yaml_performance_report
from aider.io import InputOutput
from aider.models import Model
from aider.coders.context_coder import ContextCoder
from aider.repomap import find_src_files
from aider.io import InputOutput
import tempfile

io = InputOutput(yes=True)

def url_filter(f):
    if f.endswith(".html"):
        return True
    if f.endswith(".js"):
        if ("/etc.clientlibs/" in f) or (not f.endswith(".min.js")):
            return True
    if f.endswith(".css"):
        if ("/etc.clientlibs/" in f) or (not f.endswith(".min.css")):
            return True
    return False

def format_aider_instruction(summary, reasoning, technical_implementation):
    """Format the instruction for aider to apply the code changes."""
    return f"""

# {summary}

## Reasoning
{reasoning}

## Technical Implementation Instructions
{technical_implementation}
"""

context_prompt = lambda src_files: f"""For the following files, point out the files that need to be edited to fix the performance issue provided at the end.
    {'\n'.join(src_files)}
    Give me the list of files to edit and nothing else, enclose each filename in backticks."""

def get_context_files(output_dir, model, summary, reasoning, technical_implementation):
    context_coder = ContextCoder(main_model=model, io=io, detect_urls=False)
    skiplen = len(output_dir) + (0 if output_dir.endswith("/") else 1)
    src_files = [f[skiplen:] for f in find_src_files(output_dir) if url_filter(f)]
    prompt = context_prompt(src_files) + format_aider_instruction(summary, reasoning, technical_implementation)
    response = context_coder.run(prompt)
    files = re.findall(r'`(.*?)`', response)
    return files

def apply_code_changes(output_dir, suggestion, model_name, suggestion_id):
    model = Model(model_name)
    summary = suggestion.get("summary", "").strip()
    reasoning = suggestion.get("reasoning", "").strip()
    technical_implementation = suggestion.get(
        "technical_implementation", ""
    ).strip()
    edit_files = get_context_files(output_dir, model, summary, reasoning, technical_implementation)
    
    # Create a temporary file with the edit prompt to avoid shell escaping issues
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        edit_prompt = f"Implement the following changes in the webpage\n{format_aider_instruction(summary, reasoning, technical_implementation)}"
        f.write(edit_prompt)
        temp_file = f.name
    
    try:
        # Use message-file instead of message to avoid shell escaping issues
        command = f"cd {output_dir} && git checkout -b {suggestion_id} && aider {' '.join(edit_files)} --model {model_name} --message-file '{temp_file}' --yes && git checkout master"
        print("Command: ", command)
        os.system(command)
        print(f"Applied changes to {edit_files} in branch {suggestion_id}")
    finally:
        # Clean up temp file
        os.unlink(temp_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a performance report and apply code changes using aider.")
    parser.add_argument("--report-path", required=True, help="Path to the performance report file.")
    parser.add_argument("--output-dir", required=True, help="Path to the output directory.")
    parser.add_argument("--model", default="azure/gpt-4o", help="model to use")
    args = parser.parse_args()

    device, url, report_text = read_report_with_check(args.report_path)
    llm = LLM(model=args.model)
    yaml_response = convert_to_yaml(report_text, llm)
    parsed_report = parse_yaml_performance_report(yaml_response)
    
    for suggestion in parsed_report:
        suggestion_id = uuid.uuid4()
        print(f"Applying suggestion: {suggestion['summary']}")
        apply_code_changes(args.output_dir, suggestion, args.model, suggestion_id)