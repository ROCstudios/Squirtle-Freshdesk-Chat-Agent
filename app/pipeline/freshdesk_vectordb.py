import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import dotenv
import argparse
import requests
import os
from app.ui.db import upload_to_pinecone, json_to_documents
from bs4 import BeautifulSoup
import re
import json

dotenv.load_dotenv()

api_key = os.getenv("FRESHDESK_API_KEY")
domain = os.getenv("FRESHDESK_DOMAIN")


def clean_html_text(html_string: str) -> str:
    """Clean HTML formatting from text, preserving only essential content"""
    if not html_string:
        return ""

    # Parse HTML and get text content
    soup = BeautifulSoup(html_string, "html.parser")

    # Get text content, stripping HTML tags
    text = soup.get_text(separator=" ", strip=True)

    # Clean up extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def paginate_all_tickets_to_pinecone(per_page: int = 25):

    headers = {"Content-Type": "application/json"}

    tickets = []
    page = 1
    skipped_count = 0

    while True:
        url = f"https://{domain}/api/v2/tickets?page={page}&per_page={per_page}&updated_since=2000-01-19T02:00:00Z&include=description"
        response = requests.get(url, headers=headers, auth=(api_key, "X"))

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            break

        data = response.json()

        if not data:
            break

        for item in data:
            clean_description = clean_html_text(item.get("description_text", ""))
            item["description_text"] = clean_description

        tickets.extend(data)
        print(f"📥 Pulled {len(data)} tickets from page {page}", end="\n")

        try:
            docs, ids = json_to_documents(data)
            store = upload_to_pinecone(docs, ids)
            print(f"📦 Vector batch #{page} saved successfully")
            print(store)
            print("-" * 100)
        except Exception as e:
            skipped_count += 1
            print(f"Error: {e}")

        page += 1

    print(f"Skipped {skipped_count} tickets due to errors")
    print(f"Total tickets fetched: {len(tickets)}")
    return tickets


# Example usage
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch Freshdesk tickets")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of tickets to fetch details for (default: 5)",
    )
    args = parser.parse_args()
    limit = args.limit if args.limit else 5

    # fetcher = FreshdeskBatchFetcher(api_key, domain)

    # # Fetch batch of tickets
    # tickets = fetcher.fetch_ticket_batch(page=1, per_page=100, limit=limit)
    # print(f"Fetched {fetcher.get_last_fetch_count()} tickets")

    # # Utility method examples
    # print(f"Total fetch operations: {fetcher.get_total_fetches()}")
    # print(f"Cache size: {fetcher.get_cache_size()}")
    # if fetcher.get_time_since_last_fetch():
    #     print(
    #         f"Time since last fetch: {fetcher.get_time_since_last_fetch().seconds} seconds"
    #     )

    # print(json.dumps(tickets, indent=4))
    paginate_all_tickets_to_pinecone()
