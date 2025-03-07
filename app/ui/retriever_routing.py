from app.domain.freshdesk_vectordb import (
    clean_tickets_description_upload_to_pinecone,
)
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI
from typing import List, Dict
from app.core.csv_core import get_tickets_from_csv
import streamlit as st
import pandas as pd
import os
from app.datastore.update_flag import GlobalFlagUpdater

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "..", "data")

should_update = GlobalFlagUpdater().should_update

llm = OpenAI(temperature=0)

routing_prompt = PromptTemplate(
    input_variables=["query"],
    template="Classify this query as 'quantitative' or 'qualitative': {query}",
)

pandas_agent = None
docs_agent = None


def get_pandas_agent(file_path: str = os.path.join(data_dir, "test_dataset.csv")):
    global pandas_agent
    if pandas_agent is None:
        pandas_agent = configure_retriever_pandas(file_path)
    return pandas_agent


def get_doc_retriever_agent(
    ticket_details: List[Dict] = get_tickets_from_csv(
        os.path.join(data_dir, "test_dataset.csv")
    )
):
    global docs_agent
    if docs_agent is None:
        docs_agent = configure_retriever_docs(ticket_details)
    return docs_agent


def configure_retriever_pandas(file_path: str):
    if should_update:
        configure_retriever_pandas_no_cache(file_path)
    else:
        return configure_retriever_pandas_cache(file_path)


def configure_retriever_pandas_no_cache(file_path: str):
    tickets_details_df = pd.read_csv(file_path)
    tickets_details_df = tickets_details_df.drop(
        columns=["description", "description_text"], errors="ignore"
    )
    if should_update:
        configure_retriever_pandas_cache.clear()
        return configure_retriever_pandas_cache(file_path)
    else:
        local_pandas_agent = create_pandas_dataframe_agent(
            llm,
            tickets_details_df,
            verbose=True,
            allow_dangerous_code=True,
        )
        pandas_agent = local_pandas_agent
        return pandas_agent


@st.cache_data
def configure_retriever_pandas_cache(file_path: str):
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


def configure_retriever_docs(ticket_details: List[Dict]):
    if should_update:
        configure_retriever_docs_no_cache(ticket_details)
    else:
        return configure_retriever_docs_cache(ticket_details)


def configure_retriever_docs_no_cache(ticket_details: List[Dict]):
    if should_update:
        configure_retriever_docs_cache.clear()
        return configure_retriever_docs_cache(ticket_details)
    else:
        docs_agent = clean_tickets_description_upload_to_pinecone(ticket_details)

        retriever = docs_agent.as_retriever(
            search_type="mmr", search_kwargs={"k": 2, "fetch_k": 4}
        )

        return retriever


@st.cache_resource
def configure_retriever_docs_cache(ticket_details: List[Dict]):
    """Configure retriever from JSON data"""
    docs_agent = clean_tickets_description_upload_to_pinecone(ticket_details)

    retriever = docs_agent.as_retriever(
        search_type="mmr", search_kwargs={"k": 2, "fetch_k": 4}
    )

    return retriever
