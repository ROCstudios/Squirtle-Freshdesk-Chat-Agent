from typing import List, Dict
import os
import streamlit as st

# from app.datastore.db import vector_store
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import OpenAI
import pandas as pd

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

data_dir = os.path.join(script_dir, "..", "data")
tickets_details_df = pd.read_csv(os.path.join(data_dir, "complete_ticket_details.csv"))
tickets_details_df = tickets_details_df.drop(
    columns=["description", "description_text"], errors="ignore"
)


agent = create_pandas_dataframe_agent(
    OpenAI(temperature=0),
    tickets_details_df,
    verbose=True,
    allow_dangerous_code=True,
)


@st.cache_resource
def configure_retriever_from_json():
    """Configure retriever from JSON data"""

    # Define retriever
    retriever = vector_store.as_retriever(
        search_type="mmr", search_kwargs={"k": 2, "fetch_k": 4}
    )

    return retriever


def query_retriever(retriever, query: str):
    """Query the retriever"""
    print(retriever.invoke(query))


if __name__ == "__main__":
    # retriever = configure_retriever_from_json()
    # query_retriever(retriever, "What is the status of most of our tickets?")
    print(agent.invoke({"input": "How many tickets do we have?"}))
