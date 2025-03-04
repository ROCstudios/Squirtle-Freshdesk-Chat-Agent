import streamlit as st
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.chains import ConversationalRetrievalChain
from app.consts import SYSTEM_TEMPLATE, HUMAN_TEMPLATE, REPHRASE_PROMPT
from app.ui.handlers import PrintRetrievalHandler, StreamHandler
from app.ui.retriever_routing import (
    get_doc_retriever_agent,
    get_pandas_agent,
)
from langchain.chains import LLMChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
import os
import dotenv
from app.datastore.update_flag import GlobalFlagUpdater
import sys
import os
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_core.runnables import chain
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List
from langchain.chains import create_history_aware_retriever
from langchain import hub
from langchain.prompts import MessagesPlaceholder
from langchain.chains import create_retrieval_chain
from langchain.schema.output_parser import StrOutputParser


sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

dotenv.load_dotenv()

updater = GlobalFlagUpdater()

st.set_page_config(page_title="AlpineShark Reports", page_icon="🗻")
if st.button("Clear message history", key="clear_button"):
    st.session_state.clear_messages = True
st.title("Alpine Reports")

st.sidebar.title("Get Updated Tickets")
st.sidebar.write(
    "⚠️ This will update the database with the latest tickets. It will take a few minutes to reload this page."
)
if st.sidebar.button("Get New Tickets"):
    st.sidebar.write("Update in Progess!")

# Setup memory for contextual conversation
msgs = StreamlitChatMessageHistory()
memory = ConversationBufferMemory(
    memory_key="chat_history",
    chat_memory=msgs,
    return_messages=True,
    output_key="answer",
)

if "docs_retriever" not in st.session_state:
    st.session_state.docs_retriever = get_doc_retriever_agent()

if "pandas_retriever" not in st.session_state:
    st.session_state.pandas_retriever = get_pandas_agent()


# Setup LLM and QA chain
llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0,
    streaming=True,
)

combine_docs_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_TEMPLATE),
        ("human", HUMAN_TEMPLATE),
    ]
)

combine_docs_chain_llm = LLMChain(llm=llm, prompt=combine_docs_prompt)

combine_docs_chain = StuffDocumentsChain(
    llm_chain=combine_docs_chain_llm,
    document_variable_name="context",
    document_prompt=PromptTemplate(
        input_variables=["page_content"], template="{page_content}"
    ),
)

question_generator = LLMChain(
    llm=llm, prompt=PromptTemplate.from_template(REPHRASE_PROMPT)
)

########################################################


class QueryClassifier(BaseModel):
    """Determine whether the query is quantitative or qualitative."""

    query: str = Field(
        ...,
        description="Query to look up",
    )

    query_type: str = Field(
        ..., description="The type of query. Should be 'quantitative' or 'qualitative'."
    )


def parse_retriever_response(response):
    """
    Parses the retriever response to extract a string.

    If the response is a list of Document objects, it combines their content.
    If the response is a dictionary, it extracts the 'output' value.

    Args:
        response: The response from the retriever, which can be a list of Document objects or a dictionary.

    Returns:
        A string containing the combined content or the output from the dictionary.
    """
    if isinstance(response, list):
        # Assuming response is a list of Document objects
        combined_content = []
        for doc in response:
            # Extracting metadata and page content
            ticket_id = doc.metadata.get("ticket_id")
            created_at = doc.metadata.get("created_at")
            sender_emails = doc.metadata.get("sender_emails")
            status = doc.metadata.get("status")
            page_content = doc.page_content

            # Combine the extracted information into a string
            combined_content.append(
                f"Ticket ID: {ticket_id}\nCreated At: {created_at}\nSender Emails: {sender_emails}\nStatus: {status}\nPage Content: {page_content}\n"
            )

        return "\n".join(combined_content)  # Join all document strings into one

    elif isinstance(response, dict) and "output" in response:
        # Assuming response is a dictionary with an 'output' key
        return response["output"]

    return "No valid response format found."  # Fallback for unexpected formats


choose_retriever_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You have the ability to choose between two retrievers. One is a pandas retriever and the other is a docs retriever. You will be given a question and you will need to decide which retriever to use.",
        ),
        ("human", "{question}"),
    ]
)

structured_llm = llm.with_structured_output(QueryClassifier)

query_analyzer = (
    {
        "question": RunnablePassthrough(),
    }
    | choose_retriever_prompt
    | structured_llm
)

retrievers = {
    "quantitative": st.session_state.pandas_retriever,
    "qualitative": st.session_state.docs_retriever,
}


# @chain
def custom_chain(question: str, retrieval_handler, stream_handler):
    response = query_analyzer.invoke(question)
    retriever = retrievers[response.query_type]

    if response.query_type == "quantitative":
        response = retriever(
            question,
            callbacks=[retrieval_handler, stream_handler],
        )
        return response
    else:
        qa_chain = ConversationalRetrievalChain(
            retriever=retriever,
            combine_docs_chain=combine_docs_chain,
            question_generator=question_generator,
            memory=memory,
            return_source_documents=True,
            verbose=True,
        )
        response = qa_chain(
            {"question": question}, callbacks=[retrieval_handler, stream_handler]
        )
        return response


qa_system_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI assistant that answers user queries based on the conversation history. "
            "Use previous messages as context to generate an accurate and concise response. "
            "If you don't have enough context, ask for clarification.",
        ),
        MessagesPlaceholder("chat_history"),  # Maintains conversation memory
        ("human", "{input}"),  # The processed query from history-aware chain
    ]
)

qa_chain = LLMChain(llm=llm, prompt=qa_system_prompt, output_parser=StrOutputParser())

########################################################


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
        retrieval_handler = PrintRetrievalHandler(st.container())
        stream_handler = StreamHandler(st.empty())

        response = custom_chain(user_query, retrieval_handler, stream_handler)
        print("🚀 ~retriever response:", response)

        # response = qa_chain.invoke(
        #     {
        #         "input": string_response,
        #         "chat_history": msgs.messages,  # Includes past conversation for context
        #     },
        #     callbacks=[retrieval_handler, stream_handler],
        # )

        # print("🚀 ~ final response:", response)
        msgs.add_ai_message(response["answer"])
