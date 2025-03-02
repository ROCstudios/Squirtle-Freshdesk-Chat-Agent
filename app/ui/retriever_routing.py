from app.domain.freshdesk_vectordb import (
    clean_tickets_description_upload_to_pinecone,
)
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.prompts import PromptTemplate
from langchain.agents import AgentExecutor
from langchain_openai import OpenAI
from typing import List, Dict
from app.core.db_core import vector_store
import streamlit as st
import pandas as pd
import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "..", "data")

llm = OpenAI(temperature=0)

routing_prompt = PromptTemplate(
    input_variables=["query"],
    template="Classify this query as 'quantitative' or 'qualitative': {query}",
)

pandas_agent = None
docs_agent = None


def get_pandas_agent(file_path: str):
    global pandas_agent
    if pandas_agent is None:
        pandas_agent = configure_retriever_from_pandas(file_path)
    return pandas_agent


def get_doc_retriever_agent():
    global docs_agent
    if docs_agent is None:
        docs_agent = configure_retriever_from_docs()
    return docs_agent


def route_query_with_llm(query: str) -> AgentExecutor:
    classification = llm(routing_prompt.format(query=query)).strip()
    if "quantitative" in classification:
        return pandas_agent
    else:
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


def process_query(query: str) -> None:
    """
    Routes the query to the appropriate retriever and executes it.

    Args:
        query (str): The user query to process.
    """
    # Route to the appropriate retriever
    retriever = route_query_with_llm(query)

    # Execute the query based on retriever type
    if isinstance(retriever, AgentExecutor):
        # For pandas_agent (AgentExecutor)
        result = retriever.invoke({"input": query})
        print("Pandas Agent Result")
        return result
    else:
        # For doc_retriever_agent (Runnable retriever)
        result = retriever.invoke(query)
        print("Document Retriever Result")
        return result


pandas_agent = configure_retriever_from_pandas()
docs_agent = configure_retriever_from_docs()


if __name__ == "__main__":
    # retriever = configure_retriever_from_json()
    # query_retriever(retriever, "What is the status of most of our tickets?")
    test_queries = [
        "Can you tell me how many tickets come from email vs chat?",
        "What is the status of most of our tickets?",
        "What are common customer complaints?",
    ]

    for query in test_queries:
        print(f"\nProcessing query: '{query}'")
        print(process_query(query))
