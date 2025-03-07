import streamlit as st

from chain import custom_chain, msgs
import os
import dotenv
from app.datastore.update_flag import GlobalFlagUpdater
import sys
import os
from app.pipeline.new_batch_pipeline import get_our_most_recent_tickets

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

dotenv.load_dotenv()

updater = GlobalFlagUpdater()

# st.set_page_config(page_title="AlpineShark Reports", page_icon="🗻")
if st.button("Clear message history", key="clear_button"):
    st.session_state.clear_messages = True
st.title("AlpineShark Reports")

st.sidebar.title("Get Updated Tickets")
st.sidebar.write(
    "This will update the database with the latest tickets. It will take a few minutes to reload this page."
)
if st.sidebar.button("Get New Tickets"):
    st.sidebar.write(
        "⚠️ Warning: This will update the database with the latest tickets. It will take a few minutes to reload this page and possibly charge you for the API call. "
    )
    if st.sidebar.button("Yes, I want to update the database"):
        new_tickets = get_our_most_recent_tickets()
        st.sidebar.write(f"New tickets: {new_tickets}")
        if len(new_tickets) > 0:
            st.rerun()

if len(msgs.messages) == 0 or st.session_state.get("clear_messages", False):
    msgs.clear()
    msgs.add_ai_message("""What can I get started for you today?""")
    st.session_state.clear_messages = False

avatars = {"human": "user", "ai": "assistant"}

for msg in msgs.messages:
    st.chat_message(avatars[msg.type]).write(msg.content)

if user_query := st.chat_input(placeholder="Ask me anything!"):
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        response = custom_chain(user_query)
        msgs.add_ai_message(response)
