# GitHub Service Scraper

A Python script to scrape service information and GitHub stars from the Model Context Protocol server list.

## About

This script scrapes the following URL to gather a list of first-party and third-party services:
[https://github.com/modelcontextprotocol/servers/tree/main?tab=readme-ov-file](https://github.com/modelcontextprotocol/servers/tree/main?tab=readme-ov-file)

It extracts the service name, repository URL, and the number of stars for each repository. The final list is sorted by the number of stars in descending order and saved to `github_all_services_sorted.csv`.

## Usage

1.  **Install dependencies:**
    ```bash
    pip install requests beautifulsoup4
    ```

2.  **Run the script:**
    ```bash
    python scraper.py
    ```

3.  **Output:**
    The script will generate a file named `github_all_services_sorted.csv` with the scraped data.
