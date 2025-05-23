import os

import requests


def read_report(report_path: str) -> str:
    report_name = report_path.split("/")[-1]
    url = report_name.split(".")[0].replace("-", ".")
    device = report_name.split(".")[1]

    with open(report_path, "r") as f:
        report = f.read()

    return device, url, report


def read_report_with_check(report_path: str) -> str:
    device, url, report = read_report(report_path)
    url = "https://" + url if not url.startswith("https://") else url
    response = requests.get(url)
    if response.status_code == 404:
        raise ValueError(f"URL does not exist: {url}")
    return device, url, report
