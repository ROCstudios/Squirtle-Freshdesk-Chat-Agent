import requests
import pandas as pd
import dotenv
import os
import time
from app.core.csv_core import get_most_recently_updated_date, append_to_csv, save_to_csv
from app.core.freshdesk_core import get_all_tickets, get_ticket_details

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from script directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
# Define data directory
DATA_DIR = os.path.join(PROJECT_ROOT, "app/data")

dotenv.load_dotenv()

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

HEADERS = {"Authorization": f"Basic {FRESHDESK_API_KEY}"}

AUTH = (FRESHDESK_API_KEY, "X")


def get_all_tickets(per_page: int = 100, save: bool = True):
    headers = {"Content-Type": "application/json"}

    tickets = []
    page = 1
    skipped_count = 0

    recent_data_count = 1

    while recent_data_count > 0:
        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets?page={page}&per_page={per_page}&updated_since=2000-01-19T02:00:00Z"
        response = requests.get(url, headers=headers, auth=(FRESHDESK_API_KEY, "X"))

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            break

        data = response.json()
        tickets.extend(data)
        print(f"📥 Pulled {len(data)} tickets from page {page}", end="\n")
        recent_data_count = len(data)

        page += 1

    if save:
        save_to_csv(tickets, "tickets.csv")
        return tickets
    else:
        return tickets


def get_tickets_with_limit(
    limit: int = None,
    updated_since: str = None,
    save: bool = True,
):
    print(f"Fetching {limit} tickets")

    tickets = []
    page = 1
    per_page = 100

    if limit:
        per_page = min(per_page, limit)
        page = max(1, limit // per_page)

    while len(tickets) < limit:
        response = get_all_tickets(
            page=page, per_page=per_page, updated_since=updated_since
        )

        tickets.extend(response)
        page += 1

    if save:
        save_to_csv(tickets, "tickets.csv")
        return tickets
    else:
        return tickets


def get_all_ticket_details(file_path: str, save: bool = True):
    tickets_df = pd.read_csv(os.path.join(DATA_DIR, file_path))
    ticket_details = []

    print(f"Fetched {len(tickets_df)} ticket details")

    # Reverse the order of ticket IDs to process from bottom up
    reversed_ticket_ids = tickets_df["id"].iloc[::-1]
    for ticket_id in reversed_ticket_ids:
        if ticket_id > 4220:
            break

        ticket_details.append(get_ticket_details(ticket_id))
        # time.sleep(0.5)  # Avoid rate limiting

    if save:
        save_to_csv(ticket_details, "ticket_details.csv")
        return ticket_details
    else:
        return ticket_details


def get_most_recent_tickets_to_append(file_path):
    updated_from = get_most_recently_updated_date(file_path)
    if updated_from:
        response = get_all_tickets(updated_since=updated_from.isoformat())

        if response.status_code == 200:
            append_to_csv(response, file_path)
            return response
        else:
            print(f"Error fetching tickets: {response.status_code}")
            return []
