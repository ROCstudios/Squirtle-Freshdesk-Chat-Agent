import os
import time
from pinecone import Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from typing import List, Dict

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

api_key = os.environ.get("PINECONE_API_KEY")
openai_api_key = os.environ.get("OPENAI_API_KEY") or "OPENAI_API_KEY"
model_name = "text-embedding-ada-002"

index_name = "freshdesk-tickets-v1"
# configure client
pc = Pinecone(api_key=api_key)
cloud = os.environ.get("PINECONE_CLOUD") or "aws"
region = os.environ.get("PINECONE_REGION") or "us-east-1"

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

# wait for index to be initialized
while not pc.describe_index(index_name).status["ready"]:
    time.sleep(1)

index = pc.Index(index_name)

print("🚀 Index created successfully")
print(index.describe_index_stats())

embeddings = OpenAIEmbeddings(model=model_name, openai_api_key=openai_api_key)
vector_store = PineconeVectorStore(index=index, embedding=embeddings)


def upload_to_pinecone(docs, ids):
    """Upload JSON data to Pinecone and return the index"""
    uploads = vector_store.add_documents(documents=docs, ids=ids)
    return uploads


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


def test_pinecone_data():
    """Test that data is properly stored in Pinecone"""
    # Get index statistics
    stats = index.describe_index_stats()
    print(f"Total vectors in index: {stats['total_vector_count']}")

    # Test a sample query
    query = "high priority tickets"
    vectordb = Pinecone.from_existing_index(
        index_name=index_name, embedding=OpenAIEmbeddings()
    )

    results = vectordb.similarity_search(query, k=2)  # Number of results to return

    print("\nSample search results:")
    for doc in results:
        print(f"\nContent: {doc.page_content}")
        print(f"Metadata: {doc.metadata}")
