
import os
from pydantic.types import Json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urljoin
import time
import json


# --- Data Structures ---

@dataclass
class DecisionNotice:
    """Represents the data scraped from a single decision notice page."""
    organisation: str
    date: Optional[date]
    sector: str
    decision: str
    abstract: str
    pdf_url: str
    pdf_filename: str

# --- Configuration ---

BASE_URL = "https://ico.org.uk"
SEARCH_API_URL = "https://ico.org.uk/api/search" # New API endpoint from request.http
DATA_DIR = "ico-decision-notice/data"
START_PAGE = 1
MAX_PAGES = 1 # Set manually as requested
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" # From request.http

# Headers for the POST request to the search API
API_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/json",
    "Referer": "https://ico.org.uk/action-weve-taken/decision-notices/",
    "Origin": "https://ico.org.uk",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=4",
    "TE": "trailers"
}

# --- Main Functions ---

def scrape_all_notices():
    """
    Main function to orchestrate the scraping of the ICO decision notices website.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    case_counter = 1

    total_pages = MAX_PAGES # Set manually as requested

    print(f"Scraping up to {total_pages} pages.")

    for page_num in range(START_PAGE, total_pages + 1):
        print(f"--- Scraping page {page_num} of {total_pages} ---")
        try:
            # get_data_from_json_api now returns a list of dictionaries with parsed data
            notices_data_from_api = get_data_from_json_api(page_num)

            if not notices_data_from_api:
                print(f"No more decision notices found on page {page_num}. Moving on.")
                if page_num > START_PAGE:
                    print(f"Reached end of results at page {page_num - 1}.")
                    break
                continue

            for notice_data in notices_data_from_api:
                detail_url = urljoin(BASE_URL, notice_data['url']) # full URL to the detail page
                print(f"Scraping detail page for PDF: {detail_url}")
                try:
                    scrape_detail_page(detail_url, case_counter, notice_data)
                    case_counter += 1
                    time.sleep(1) # Be a good citizen
                except Exception as e:
                    print(f"Error processing detail for {detail_url}: {e}")

        except Exception as e:
            print(f"Error scraping API for page {page_num}: {e}")


def get_data_from_json_api(page_num: int) -> List[Dict[str, Any]]:
    """
    Makes a POST request to the search API for a given page number and returns parsed notice data.
    """
    payload = {"filters":[],"pageNumber":page_num,"order":"newest","rootPageId":13635}

    try:
        response = requests.post(SEARCH_API_URL, headers=API_HEADERS, json=payload)
        response.raise_for_status()
        json_data = response.json()

        print(json_data)

        notices_data = []
        for item in json_data.get('results', []):
            organisation = item.get('title', 'Unknown Organisation')
            detail_url_path = item.get('url', '')
            abstract = item.get('description', '')

            # Parse date and sector from filterItemMetaData
            filter_meta = item.get('filterItemMetaData', '')
            date_str_raw = ""
            sector = "Not found"

            # Example: "5 December 2025, Education"
            if filter_meta:
                parts = filter_meta.split(',', 1) # Split only on the first comma
                if parts:
                    date_str_raw = parts[0].strip()
                if len(parts) > 1:
                    sector = parts[1].strip()

            parsed_date = None
            if date_str_raw:
                try:
                    parsed_date = datetime.strptime(date_str_raw, "%d %B %Y").date()
                except ValueError:
                    print(f"Could not parse date: {date_str_raw}")

            # Parse decision from filterItemDecisions (which is a list of dicts)
            decisions = []
            for dec_item in item.get('filterItemDecisions', []):
                status = dec_item.get('status', '')
                section = dec_item.get('section', '')
                if status and section:
                    decisions.append(f"{section}: {status}")
            decision_str = ", ".join(decisions) if decisions else "Not found"

            notices_data.append({
                'organisation': organisation,
                'date': parsed_date,
                'sector': sector,
                'decision': decision_str,
                'abstract': abstract,
                'url': detail_url_path # The URL to the detail page, not PDF yet
            })
        return notices_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API for page {page_num}: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON for page {page_num}: {e}")
    return []


def scrape_detail_page(url: str, case_counter: int, notice_data_from_api: Dict[str, Any]):
    """
    Fetches the detail page to extract the PDF link and saves all metadata and the PDF.
    """
    # Use metadata from the API response
    organisation = notice_data_from_api['organisation']
    parsed_date = notice_data_from_api['date']
    sector = notice_data_from_api['sector']
    decision = notice_data_from_api['decision']
    abstract = notice_data_from_api['abstract']

    # --- Scrape only the PDF link from the detail page ---
    headers = {'User-Agent': USER_AGENT}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    pdf_url = "Not found"
    pdf_filename = "document.pdf"
    further_reading_tag = soup.find('further-reading')
    if further_reading_tag and further_reading_tag.has_attr('x-href'):
        relative_pdf_url = str(further_reading_tag['x-href'])
        pdf_url = urljoin(BASE_URL, relative_pdf_url)
        if relative_pdf_url:
            pdf_filename = os.path.basename(relative_pdf_url)

    # --- Store Data ---
    case_dir = os.path.join(DATA_DIR, f"case-{case_counter}")
    os.makedirs(case_dir, exist_ok=True)

    metadata_path = os.path.join(case_dir, "metadata.txt")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(f"Organisation: {organisation}\n")
        f.write(f"Date: {parsed_date.strftime('%Y-%m-%d') if parsed_date else 'N/A'}\n")
        f.write(f"Sector: {sector}\n")
        f.write(f"Decision: {decision}\n")
        f.write(f"Abstract: {abstract}\n")
        f.write(f"PDF URL: {pdf_url}\n")

    print(f"  - Metadata saved to {metadata_path}")

    if pdf_url != "Not found":
        pdf_path = os.path.join(case_dir, pdf_filename)
        try:
            pdf_response = requests.get(pdf_url, headers=headers, stream=True)
            pdf_response.raise_for_status()
            with open(pdf_path, 'wb') as f:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  - PDF saved to {pdf_path}")
        except requests.exceptions.RequestException as e:
            print(f"  - Failed to download PDF from {pdf_url}: {e}")

if __name__ == "__main__":
    scrape_all_notices()
