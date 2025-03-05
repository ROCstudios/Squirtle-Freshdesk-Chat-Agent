import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from app.ui.handlers import (
    PrintRetrievalHandler,
    StreamHandler,
    PrintPandasAgentHandler,
    StreamPandasAgentHandler,
)
from app.ui.retriever_routing import (
    get_doc_retriever_agent,
    get_pandas_agent,
)
from langchain.chains import LLMChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.schema.output_parser import StrOutputParser
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from app.ui.prompts import (
    qa_system_prompt,
    choose_retriever_prompt,
    combine_docs_prompt,
    document_prompt,
    question_prompt,
)
import os

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

combine_docs_chain_llm = LLMChain(llm=llm, prompt=combine_docs_prompt)


combine_docs_chain = StuffDocumentsChain(
    llm_chain=combine_docs_chain_llm,
    document_variable_name="context",
    document_prompt=document_prompt,
)

question_generator = LLMChain(llm=llm, prompt=question_prompt)


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


def custom_chain(question: str):
    response = query_analyzer.invoke(question)
    retriever = retrievers[response.query_type]

    if response.query_type == "quantitative":
        handlers = [
            PrintPandasAgentHandler(st.container()),
            StreamPandasAgentHandler(st.empty()),
        ]
        response = retriever(
            question,
            callbacks=handlers,
        )
        return response["output"]
    else:
        handlers = [PrintRetrievalHandler(st.container()), StreamHandler(st.empty())]
        qa_chain = ConversationalRetrievalChain(
            retriever=retriever,
            combine_docs_chain=combine_docs_chain,
            question_generator=question_generator,
            memory=memory,
            return_source_documents=True,
            verbose=True,
        )
        response = qa_chain({"question": question}, callbacks=handlers)
        return response["answer"]


qa_chain = LLMChain(llm=llm, prompt=qa_system_prompt, output_parser=StrOutputParser())
