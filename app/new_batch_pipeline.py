from freshdesk_csv import (
    get_most_recent_tickets_to_append,
    get_all_ticket_details,
)
from freshdesk_vectordb import get_most_recent_tickets_append_to_vector_db


def get_our_most_recent_tickets():
    file_path = get_most_recent_tickets_to_append("test_tickets.csv")
    ticket_details = get_all_ticket_details(file_path, "test_ticket_details.csv")
    get_most_recent_tickets_append_to_vector_db()
    updater.set_update_flag("batch_update", True)
    return ticket_details


if __name__ == "__main__":
    get_our_most_recent_tickets()
