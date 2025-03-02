from app.domain.freshdesk_csv import get_tickets_with_limit, get_most_recent_updated_at_from_csv, get_all_ticket_details
import pandas as pd
import os

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from script directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
# Define data directory
DATA_DIR = os.path.join(PROJECT_ROOT, "app/data_pipeline")

def save_tickets_to_csv(tickets):
    csv_file_path = os.path.join(DATA_DIR, "prod_tickets.csv")
    # Load existing tickets from the CSV file
    try:
        existing_df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        existing_df = pd.DataFrame()  # Create an empty DataFrame if the file does not exist

    # Create a DataFrame from the new tickets
    new_df = pd.DataFrame(tickets)

    # Concatenate the existing tickets with the new tickets
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)

    # Sort the combined DataFrame by the 'id' field to maintain order
    combined_df = combined_df.sort_values(by='id')

    # Save the combined DataFrame to the CSV file
    combined_df.to_csv(csv_file_path, index=False)
    
    return csv_file_path

def get_our_most_recent_tickets():
  # we get the date of the most recent ticket from the local store.
  most_recent_updated_at = get_most_recent_updated_at_from_csv()
  # we pull the information of all the tickets after the most recent date
  # we fetch and store in a dataframe of all the tickets (high level) these include the description_text
  tickets = get_tickets_with_limit(
    updated_since=most_recent_updated_at,
    save_to_csv=False
  )
  # we then use the original ticket to fetch the details of the ticket
  ticket_details = get_all_ticket_details(save_to_csv=False)
  # we then take the details and add them to the end of the dataframe
  csv_file_path = save_tickets_to_csv(ticket_details)
  # the tickets are then stored in the vector database
  
  
  return tickets
  
  


if __name__ == "__main__":
  
  
  
  
  
  
  # we refresh the entire langchain implementation
