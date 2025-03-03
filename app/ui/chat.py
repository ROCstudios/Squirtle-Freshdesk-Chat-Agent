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

rephrase_prompt = hub.pull("langchain-ai/chat-langchain-rephrase")


class QueryClassifier(BaseModel):
    """Determine whether the query is quantitative or qualitative."""

    query: str = Field(
        ...,
        description="Query to look up",
    )

    query_type: str = Field(
        ..., description="The type of query. Should be 'quantitative' or 'qualitative'."
    )


sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

dotenv.load_dotenv()

updater = GlobalFlagUpdater()

st.set_page_config(page_title="Alpine Reports", page_icon="🗻")
if st.button("Clear message history", key="clear_button"):
    st.session_state.clear_messages = True
st.title("Alpine Reports")

st.sidebar.title("Sidebar Title")
if st.sidebar.button("Click Me"):
    st.sidebar.write("Button clicked!")

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

question_generator = LLMChain(llm=llm, prompt=rephrase_prompt)

########################################################

prompter = ChatPromptTemplate.from_messages(
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
    | prompter
    | structured_llm
)

retrievers = {
    "quantitative": st.session_state.pandas_retriever,
    "qualitative": st.session_state.docs_retriever,
}


@chain
def custom_chain(question: str):
    response = query_analyzer.invoke(question)
    print("🚀 ~ response:", response)
    retriever = retrievers[response.query_type]
    return retriever


chosen_retriever = custom_chain

########################################################

# qa_chain = ConversationalRetrievalChain(
#     retriever=None,
#     combine_docs_chain=combine_docs_chain,
#     question_generator=question_generator,
#     memory=memory,
#     return_source_documents=True,
#     verbose=True,
# )

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

        response = custom_chain.invoke(user_query)
        print("🚀 ~ response:1", response)

        chat_retriever_chain = create_history_aware_retriever(
            llm, chosen_retriever, rephrase_prompt
        )

        # response = chat_retriever_chain.invoke(
        #     {"input": user_query, "chat_history": msgs.messages}
        # )
        response = chat_retriever_chain(
            {"input": user_query, "chat_history": msgs.messages},
            callbacks=[retrieval_handler, stream_handler],
        )
        print("🚀 ~ final response:", response)
        msgs.add_ai_message(response["answer"])
