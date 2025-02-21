import requests
import pandas as pd
import dotenv
import os

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


def get_all_tickets(limit: int = None):
    print(f"Fetching {limit} tickets")

    tickets = []
    page = 1
    per_page = 30

    if limit:
        per_page = min(per_page, limit)
        page = max(1, limit // per_page)

    while len(tickets) < limit:

        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets?page={page}&per_page=30"
        response = requests.get(url, headers=HEADERS, auth=AUTH)
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        tickets.extend(data)
        page += 1
        # time.sleep(1)  # To avoid rate limits
    df = pd.DataFrame(tickets)
    df.to_csv(os.path.join(DATA_DIR, "tickets.csv"), index=False)
    print("Tickets data saved to tickets.csv")


# Step 2: Get details of each ticket
def get_all_ticket_details():
    print("Fetching ticket details")

    tickets_df = pd.read_csv(os.path.join(DATA_DIR, "tickets.csv"))
    ticket_details = []

    for ticket_id in tickets_df["id"]:
        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"
        response = requests.get(url, headers=HEADERS, auth=AUTH)
        if response.status_code == 200:
            ticket_details.append(response.json())
        # time.sleep(0.5)  # Avoid rate limiting

    df = pd.DataFrame(ticket_details)
    df.to_csv(os.path.join(DATA_DIR, "ticket_details.csv"), index=False)
    print("Ticket details saved to ticket_details.csv")


# Step 3: Get ticket associations
def get_all_ticket_associations():
    print("Fetching ticket associations")

    tickets_df = pd.read_csv(os.path.join(DATA_DIR, "tickets.csv"))
    ticket_associations = []

    for ticket_id in tickets_df["id"]:
        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}/associations"
        response = requests.get(url, headers=HEADERS, auth=AUTH)
        if response.status_code == 200:
            associations = response.json()
            associations["ticket_id"] = ticket_id
            ticket_associations.append(associations)
        # time.sleep(0.5)  # Avoid rate limiting

    df = pd.DataFrame(ticket_associations)
    df.to_csv(os.path.join(DATA_DIR, "ticket_associations.csv"), index=False)
    print("Ticket associations saved to ticket_associations.csv")


if __name__ == "__main__":
    # Execute data fetching
    get_all_tickets(30)
    get_all_ticket_details()
    get_all_ticket_associations()
