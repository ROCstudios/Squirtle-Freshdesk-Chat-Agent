import requests
import dotenv
import requests
import os
from bs4 import BeautifulSoup
import re
import pandas as pd

dotenv.load_dotenv()

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from script directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
# Define data directory
DATA_DIR = os.path.join(PROJECT_ROOT, "app/data")

api_key = os.getenv("FRESHDESK_API_KEY")
domain = os.getenv("FRESHDESK_DOMAIN")

headers = {"Content-Type": "application/json"}


def get_ticket_details(ticket_id: int):
    url = f"https://{domain}/api/v2/tickets/{ticket_id}"
    response = requests.get(url, headers=headers, auth=(api_key, "X"))

    if response and response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    data = response.json()
    return data


def get_all_tickets(
    page: int = 1,
    per_page: int = 25,
    updated_since: str = "2000-01-19T02:00:00Z",
    include: str = "description",
):
    url = f"https://{domain}/api/v2/tickets?page={page}&per_page={per_page}&updated_since={updated_since}&include={include}"
    response = requests.get(url, headers=headers, auth=(api_key, "X"))

    if response and response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    data = response.json()
    return data
