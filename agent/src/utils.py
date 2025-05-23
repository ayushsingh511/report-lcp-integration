import os
import re
import requests
from urllib.parse import urlparse


def url_to_folder_name(url: str) -> str:
    """
    Convert a URL to a safe folder name that includes path information.
    
    Examples:
    - https://example.com -> example.com
    - https://example.com/products -> example.com_products
    - https://example.com/products/item -> example.com_products_item
    - https://example.com/products/item/ -> example.com_products_item
    """
    parsed = urlparse(url)
    
    # Start with hostname
    folder_name = parsed.hostname or "unknown"
    
    # Add path if it exists
    if parsed.path and parsed.path != "/":
        # Remove leading/trailing slashes and split
        path_parts = parsed.path.strip("/").split("/")
        # Filter out empty parts
        path_parts = [part for part in path_parts if part]
        
        if path_parts:
            # Join with underscores and limit length
            path_str = "_".join(path_parts[:3])  # Limit to 3 levels deep
            # Remove any characters that aren't safe for filenames
            path_str = re.sub(r'[^a-zA-Z0-9_\-]', '-', path_str)
            folder_name = f"{folder_name}_{path_str}"
    
    # Ensure the folder name isn't too long
    if len(folder_name) > 100:
        folder_name = folder_name[:100]
    
    return folder_name


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
