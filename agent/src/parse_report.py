import json
import os, re
import yaml
from crewai import LLM
from agent.src.utils import read_report_with_check

# Prompt engineering for structured extraction
PROMPT = """
You are an expert web performance analyst. You are given a semi-structured performance report (see below) containing a prioritized recommendations table and detailed technical recommendations. Your task is to extract each unique recommendation and output a YAML list, where each entry contains:
- summary: a concise, but detailed description of the recommendation
- reasoning: a thorough explanation of why this change is needed, what problems it addresses, and its benefits
- technical_implementation: a step-by-step, detailed guide on how to implement the change, including any relevant code examples, configuration snippets, or commands. All code or config examples must be included as markdown code blocks (with language specified if possible, e.g. ```html, ```css, ```js, ```bash, etc). If there are multiple code/config examples, include each in its own markdown block. Be as specific as possible.
- metadata: a dict with keys impact, complexity, and affected_metrics (from the table or inferred from the text)

Order the output so that recommendations with HIGH impact and LOW or MEDIUM complexity (i.e., easy/medium difficulty) come first, followed by others. If two recommendations have the same impact, order by lower complexity first.

If a recommendation appears in both the table and the detailed section, merge the information. If a recommendation is only in one section, include it. Do not include duplicate recommendations. Use your judgment to group similar suggestions.

Output ONLY a valid YAML list, no extra text. Double check that your output is valid YAML.
---

Report:
{}
"""

pattern = re.compile(
    r"\s*- summary:\s*(?P<summary>.*?)\s*"
    r"reasoning:\s*(?P<reasoning>.*?)\s*"
    r"technical_implementation:\s*(?P<technical_implementation>.*?)\s*"
    r"metadata:\s*(?P<metadata>.*?)\s*"
    r"$",
    re.DOTALL,
)

metadata_pattern = re.compile(
    r"impact:\s*(?P<impact>.*?)\s*"
    r"complexity:\s*(?P<complexity>.*?)\s*"
    r"affected_metrics:\s*(?P<affected_metrics>.*?)\s*"
    r"$",
    re.DOTALL,
)


def convert_to_yaml(report_text, llm):
    response = llm.call(
        [
            {"role": "system", "content": "You are a web performance expert."},
            {"role": "user", "content": PROMPT.format(report_text)},
        ]
    )
    return response[response.find("```yaml") + 7 : response.rfind("```")].strip()


def parse_yaml_performance_report(response, save_path=None):
    suggestions = ["- summary: " + s.strip() for s in response.split("- summary: ")[1:]]
    parsed_entries = []
    for suggestion in suggestions:
        matches = re.search(pattern, suggestion).groupdict()
        matches["metadata"] = re.search(
            metadata_pattern, matches["metadata"]
        ).groupdict()
        matches["metadata"]["affected_metrics"] = (
            matches["metadata"]["affected_metrics"].strip("[]").split(",")
        )
        parsed_entries.append(matches)
    parsed_entries = [p for p in parsed_entries if p and len(p["summary"]) > 0]
    if save_path:
        with open(save_path, "w") as f:
            json.dump(parsed_entries, f, indent=4)
    return parsed_entries


if __name__ == "__main__":
    # Load LLM config
    with open("config/endpoints.yaml", "r") as f:
        endpoints_config = yaml.safe_load(f)
    llm = LLM(**endpoints_config["llm"])
    data_dir = "./data/reports"
    output_dir = "./data/parsed_reports"
    report_files = [f for f in os.listdir(data_dir) if f.endswith(".report.summary.md")]
    import random

    reports = random.sample(report_files, 3)

    parsed_reports = []
    for report in reports:
        device, url, report_text = read_report_with_check(
            os.path.join(data_dir, report)
        )
        yaml_response = convert_to_yaml(report_text, llm)
        parsed_report = parse_yaml_performance_report(yaml_response)
        parsed_reports.append(parsed_report)
        # dump as json with device, and url
        with open(os.path.join(output_dir, f"{report}.json"), "w") as f:
            json.dump(
                {"device": device, "url": url, "parsed_report": parsed_report},
                f,
                indent=4,
            )
        print(f"Parsed report {report} saved to {output_dir}")
    print(parsed_reports)
