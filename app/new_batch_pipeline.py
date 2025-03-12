from freshdesk_csv import (
    get_most_recent_tickets_to_append,
    get_all_ticket_details,
)
from freshdesk_vectordb import get_most_recent_tickets_append_to_vector_db


def get_our_most_recent_tickets():
    file_path = get_most_recent_tickets_to_append("tickets.csv")
    # ticket_details = get_all_ticket_details(file_path, "tickets.csv")
    get_most_recent_tickets_append_to_vector_db()
    return ticket_details


if __name__ == "__main__":
    get_our_most_recent_tickets()
