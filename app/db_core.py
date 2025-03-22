import os
import time
from pinecone import Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from typing import List, Dict
import streamlit as st


# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

api_key = st.secrets["PINECONE_API_KEY"]
openai_api_key = st.secrets["OPENAI_API_KEY"]
model_name = "text-embedding-ada-002"

index_name = "freshdesk-tickets-v1"
# configure client
pc = Pinecone(api_key=api_key)
cloud = st.secrets["PINECONE_CLOUD"] or "aws"
region = st.secrets["PINECONE_REGION"] or "us-east-1"

spec = ServerlessSpec(cloud=cloud, region=region)

# if index_name in pc.list_indexes().names():
# pc.delete_index(index_name)

# we create a new index if one has not been created already
if index_name not in pc.list_indexes().names():
    pc.create_index(
        index_name,
        dimension=1536,  # dimensionality of text-embedding-ada-002
        metric="dotproduct",
        spec=spec,
    )

while not pc.describe_index(index_name).status["ready"]:
    time.sleep(1)

index = pc.Index(index_name)

print("🚀 Index created successfully")
print(index.describe_index_stats())

embeddings = OpenAIEmbeddings(model=model_name, openai_api_key=openai_api_key)
vector_store = PineconeVectorStore(index=index, embedding=embeddings)


def upload_to_pinecone_if_no_items():
    """Upload JSON data to Pinecone and return the index"""
    return vector_store.count() > 0


def upload_to_pinecone(docs, ids):
    """Upload JSON data to Pinecone and return the index"""
    vector_store.add_documents(documents=docs, ids=ids)
    return vector_store


def json_to_documents(json_data: List[Dict]) -> List[Document]:
    """Convert JSON data to Document objects for embedding"""
    documents = []
    for item in json_data:
        content = f"""
        Subject: {item.get('subject', '')}
        Description: {item.get('description_text', '')}
        """

        if item.get("status") == 2:
            item_status = "Open"
        elif item.get("status") == 3:
            item_status = "Pending"
        elif item.get("status") == 4:
            item_status = "Resolved"
        elif item.get("status") == 5:
            item_status = "Closed"

        # Create metadata from other relevant fields
        metadata = {
            "sender_emails": ", ".join(item.get("cc_emails", [])),
            "ticket_id": item.get("id"),
            "created_at": item.get("created_at"),
            "status": item_status,
        }

        doc = Document(page_content=content.strip(), metadata=metadata)
        documents.append(doc)

    ids = [str(item.get("id")) for item in json_data]
    return documents, ids


def get_existing_ticket_ids_from_pinecone() -> set:

    # Fetch all existing vectors' metadata
    existing_ids = set()
    all_vector_ids = index.describe_index_stats()["namespaces"][""]["vector_count"]

    # Fetch metadata in batches
    for i in range(0, all_vector_ids, 100):  # Adjust batch size as needed
        response = index.fetch(
            ids=[str(j) for j in range(i, min(i + 100, all_vector_ids))]
        )
        for vector_id, vector_data in response["vectors"].items():
            ticket_id = vector_data["metadata"].get("id")
            if ticket_id:
                existing_ids.add(ticket_id)

    return existing_ids


if __name__ == "__main__":
    # test_pinecone_data()
    print("Need method to run")
