import pandas as pd
import os
import time

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from script directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
# Define data directory
DATA_DIR = os.path.join(PROJECT_ROOT, "app/data")


def save_to_csv(data, file_path):
    df = pd.DataFrame(data)
    ticket_file = os.path.join(DATA_DIR, file_path)
    if os.path.exists(ticket_file):
        ticket_file = os.path.join(DATA_DIR, f"{file_path}_{int(time.time())}.csv")
    df.to_csv(ticket_file, index=False)
    print("Tickets data saved to", ticket_file)


def append_to_csv(data, file_path):
    df = pd.DataFrame(data)
    csv_file = os.path.join(DATA_DIR, file_path)
    if os.path.exists(csv_file):
        df.to_csv(csv_file, mode="a", header=False, index=False)
    else:
        df.to_csv(csv_file, index=False)
    print("Appended new tickets to complete_ticket_details.csv")


def get_most_recently_updated_date(file_path):
    df = pd.read_csv(os.path.join(DATA_DIR, file_path))
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
