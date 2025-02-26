import spacy
import streamlit as st
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.chains import ConversationalRetrievalChain
from consts import SYSTEM_TEMPLATE, HUMAN_TEMPLATE, REPHRASE_PROMPT
from app.agents.handlers import PrintRetrievalHandler, StreamHandler
from app.agents.retriever_routing import configure_retriever, get_static_files
from langchain.chains import LLMChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
import os
import dotenv

dotenv.load_dotenv()

nlp = spacy.load("en_core_web_sm")

st.set_page_config(page_title="Alpine Reports", page_icon="🏆")
if st.button("Clear message history", key="clear_button"):
    st.session_state.clear_messages = True
st.title("Alpine Reports")

# Setup memory for contextual conversation
msgs = StreamlitChatMessageHistory()
memory = ConversationBufferMemory(
    memory_key="chat_history",
    chat_memory=msgs,
    return_messages=True,
    output_key="answer",
)

if "retriever" not in st.session_state:
    st.session_state.retriever = configure_retriever(st.session_state.static_files)

retriever = st.session_state.retriever

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

rephrase_prompt = PromptTemplate.from_template(REPHRASE_PROMPT)

question_generator = LLMChain(llm=llm, prompt=rephrase_prompt)

qa_chain = ConversationalRetrievalChain(
    retriever=st.session_state.retriever,
    combine_docs_chain=combine_docs_chain,
    question_generator=question_generator,
    memory=memory,
    return_source_documents=True,
    verbose=True,
)

if len(msgs.messages) == 0 or st.session_state.get("clear_messages", False):
    msgs.clear()
    msgs.add_ai_message("""What can I get started for you today?""")
    st.session_state.clear_messages = False

avatars = {"human": "user", "ai": "assistant"}
for msg in msgs.messages:
    st.chat_message(avatars[msg.type]).write(msg.content)

if user_query := st.chat_input(placeholder="Ask me anything!"):
    st.chat_message("user").write(user_query)

    # Process query to remove person names
    doc = nlp(user_query)
    processed_query = " ".join(
        [token.text for token in doc if token.ent_type_ != "PERSON"]
    )

    with st.chat_message("assistant"):
        retrieval_handler = PrintRetrievalHandler(st.container())
        stream_handler = StreamHandler(st.empty())

        response = qa_chain(
            {"question": processed_query}, callbacks=[retrieval_handler, stream_handler]
        )

        msgs.add_ai_message(response["answer"])
