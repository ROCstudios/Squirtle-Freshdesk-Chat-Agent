from typing import List, Dict
import os
import streamlit as st
from app.datastore.db import vector_store
import json

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))


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
    retriever = configure_retriever_from_json()
    query_retriever(retriever, "What is the status of most of our tickets?")
