# from helloworld_crew import HelloWorldCrew

# result = HelloWorldCrew().crew().kickoff()
# print(result)

from perf_crew import PerfCrew
import json
import os
with open('report.json') as f:
    report = json.load(f)

# order report by "start" and "end"
report_data = sorted(report.get("data"), key=lambda x: (x['start'], x['end']))

crew = PerfCrew().crew()

result = crew.kickoff(
  inputs={
      "issue": "keep the LCP fast",
      "report": report_data
  }
)
print('Report generated');

os.makedirs('output', exist_ok=True)
with open('output/report.md', 'w') as f:
  f.write(result.raw)

print('Report written to file')