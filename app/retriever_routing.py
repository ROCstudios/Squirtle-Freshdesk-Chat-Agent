from freshdesk_vectordb import (
    clean_tickets_description_upload_to_pinecone,
)
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import OpenAI
from typing import List, Dict
from csv_core import get_tickets_from_csv
import streamlit as st
import pandas as pd
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")

llm = OpenAI(temperature=0, openai_api_key=st.secrets["OPENAI_API_KEY"])

pandas_agent = None
docs_agent = None


def get_pandas_agent(
    file_path: str = os.path.join(data_dir, "complete_ticket_details.csv")
):
    global pandas_agent
    if pandas_agent is None:
        pandas_agent = configure_retriever_from_pandas(file_path)
    return pandas_agent


def get_doc_retriever_agent(
    ticket_details: List[Dict] = get_tickets_from_csv(
        os.path.join(data_dir, "tickets.csv")
    )
):
    global docs_agent
    if docs_agent is None:
        docs_agent = configure_retriever_from_docs(ticket_details)
    return docs_agent


@st.cache_resource
def configure_retriever_from_pandas(file_path: str):
    tickets_details_df = pd.read_csv(file_path)
    tickets_details_df = tickets_details_df.drop(
        columns=["description", "description_text"], errors="ignore"
    )
    local_pandas_agent = create_pandas_dataframe_agent(
        llm,
        tickets_details_df,
        verbose=True,
        allow_dangerous_code=True,
    )
    pandas_agent = local_pandas_agent
    return pandas_agent


@st.cache_resource
def configure_retriever_from_docs(ticket_details: List[Dict]):
    """Configure retriever from JSON data"""
    docs_agent = clean_tickets_description_upload_to_pinecone(ticket_details)

    retriever = docs_agent.as_retriever(
        search_type="mmr", search_kwargs={"k": 2, "fetch_k": 4}
    )

    return retriever
