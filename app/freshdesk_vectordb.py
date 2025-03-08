from typing import List, Dict
import os
from db_core import (
    upload_to_pinecone,
    json_to_documents,
    get_existing_ticket_ids_from_pinecone,
)
from bs4 import BeautifulSoup
import re
import pandas as pd
from freshdesk_core import get_all_tickets
from csv_core import get_most_recently_updated_date


# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from script directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


def clean_html_text(html_string: str) -> str:
    """Clean HTML formatting from text, preserving only essential content"""
    if not html_string or pd.isna(html_string):
        return ""

    # Parse HTML and get text content
    soup = BeautifulSoup(html_string, "html.parser")

    # Get text content, stripping HTML tags
    text = soup.get_text(separator=" ", strip=True)

    # Clean up extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_tickets_description_upload_to_pinecone(
    tickets: List[Dict], batch_size: int = 100
):
    existing_ticket_ids = get_existing_ticket_ids_from_pinecone()

    # Process tickets in batches
    for i in range(0, len(tickets), batch_size):
        batch = tickets[i : i + batch_size]
        filtered_batch = []

        for item in batch:
            ticket_id = item.get("id")
            if ticket_id in existing_ticket_ids:
                continue

            clean_description = clean_html_text(item.get("description_text", ""))
            item["description_text"] = clean_description

            # Check metadata size
            metadata_size = len(str(item))
            if metadata_size <= 40960:  # Ensure metadata size is within limit
                filtered_batch.append(item)
            else:
                print(f"Skipping ticket ID {ticket_id} due to metadata size")

        if not filtered_batch:
            continue

        try:
            docs, ids = json_to_documents(filtered_batch)
            store = upload_to_pinecone(docs, ids)
            print(f"Uploaded batch of {len(filtered_batch)} tickets to vector database")
            return store
        except Exception as e:
            print(f"Error uploading batch: {e}")


def paginate_all_tickets_to_pinecone(per_page: int = 25):

    tickets = get_all_tickets(per_page=per_page)

    tickets = []
    page = 1
    skipped_count = 0

    while True:
        response = get_all_tickets(page=page, per_page=per_page)

        if not response:
            break

        for item in response:
            clean_description = clean_html_text(item.get("description_text", ""))
            item["description_text"] = clean_description

        tickets.extend(response)
        print(f"📥 Pulled {len(response)} tickets from page {page}", end="\n")

        try:
            docs, ids = json_to_documents(response)
            store = upload_to_pinecone(docs, ids)
            print(f"📦 New tickets added to vector database successfully")
        except Exception as e:
            skipped_count += per_page
            print(f"Error: {e}")

        page += 1

    print(f"Skipped {skipped_count} tickets due to errors")
    print(f"Total tickets fetched: {len(tickets)}")
    return tickets


def get_most_recent_tickets_append_to_vector_db():
    updated_from = get_most_recently_updated_date()
    if updated_from:
        response = get_all_tickets(updated_since=updated_from)

        if response.status_code == 200:
            tickets = response.json()
            docs, ids = json_to_documents(tickets)
            store = upload_to_pinecone(docs, ids)
            print(f"📦 New tickets added to vector database successfully")
            print(store)
        else:
            print(f"Error fetching tickets: {response.status_code}")
            return []
