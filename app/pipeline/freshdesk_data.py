import requests
import pandas as pd
import dotenv
import os
import time

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


def get_all_tickets(per_page: int = 100):
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

    df = pd.DataFrame(tickets)
    df.to_csv(os.path.join(DATA_DIR, "tickets.csv"), index=False)
    print("Tickets data saved to tickets.csv")


def get_tickets_with_limit(limit: int = None):
    print(f"Fetching {limit} tickets")

    tickets = []
    page = 1
    per_page = 100

    if limit:
        per_page = min(per_page, limit)
        page = max(1, limit // per_page)

    while len(tickets) < limit:
        url = (
            f"https://{FRESHDESK_DOMAIN}/api/v2/tickets?page={page}&per_page={per_page}"
        )
        response = requests.get(url, headers=HEADERS, auth=AUTH)
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        tickets.extend(data)
        page += 1

    df = pd.DataFrame(tickets)
    ticket_file = os.path.join(DATA_DIR, "tickets.csv")
    if os.path.exists(ticket_file):
        ticket_file = os.path.join(DATA_DIR, f"tickets_{int(time.time())}.csv")
    df.to_csv(ticket_file, index=False)
    print("Tickets data saved to", ticket_file)


# Step 2: Get details of each ticket
def get_all_ticket_details():
    print("Fetching ticket details")

    tickets_df = pd.read_csv(os.path.join(DATA_DIR, "tickets.csv"))
    ticket_details = []

    print(f"Fetched {len(tickets_df)} ticket details")

    # Reverse the order of ticket IDs to process from bottom up
    reversed_ticket_ids = tickets_df["id"].iloc[::-1]
    for ticket_id in reversed_ticket_ids:
        if ticket_id > 4220:
            break

        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"
        response = requests.get(url, headers=HEADERS, auth=AUTH)

        if response.status_code == 200:
            print(f"Ticket {ticket_id} fetched successfully")
            ticket_details.append(response.json())
        else:
            print(f"Error fetching ticket {ticket_id}: {response.status_code}")
        # time.sleep(0.5)  # Avoid rate limiting

    df = pd.DataFrame(ticket_details)
    ticket_details_file = os.path.join(DATA_DIR, "ticket_details.csv")
    if os.path.exists(ticket_details_file):
        ticket_details_file = os.path.join(
            DATA_DIR, f"ticket_details_{int(time.time())}.csv"
        )
    df.to_csv(ticket_details_file, index=False)
    print("Ticket details saved to ticket_details.csv")


def get_most_recent_tickets_append_to_tickets_csv():
    updated_from = get_most_recent_updated_at_from_csv()
    if updated_from:
        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets?updated_since={updated_from.isoformat()}"
        response = requests.get(url, headers=HEADERS, auth=AUTH)

        if response.status_code == 200:
            tickets = response.json()
            df = pd.DataFrame(tickets)
            complete_ticket_details_file = os.path.join(
                DATA_DIR, "../data/complete_ticket_details.csv"
            )
            if os.path.exists(complete_ticket_details_file):
                df.to_csv(
                    complete_ticket_details_file, mode="a", header=False, index=False
                )
            else:
                df.to_csv(complete_ticket_details_file, index=False)
            print("Appended new tickets to complete_ticket_details.csv")
        else:
            print(f"Error fetching tickets: {response.status_code}")
            return []


def get_most_recent_updated_at_from_csv():
    df = pd.read_csv(os.path.join(DATA_DIR, "complete_ticket_details.csv"))
    df["updated_at"] = pd.to_datetime(
        df["updated_at"], errors="coerce"
    )  # Convert to datetime, coerce errors
    df = df.sort_values(
        by="updated_at", ascending=False
    )  # Sort by created_at in descending order
    if not df.empty:
        first_row = df.iloc[0]
        print(first_row["updated_at"])
        return first_row["updated_at"]
    else:
        print("DataFrame is empty")
        return None


if __name__ == "__main__":
    # Execute data fetching
    # get_all_tickets()
    get_most_recent_updated_at_from_csv()
