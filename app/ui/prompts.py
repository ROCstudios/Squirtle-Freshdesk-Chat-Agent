from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import MessagesPlaceholder
from app.consts import SYSTEM_TEMPLATE, HUMAN_TEMPLATE, REPHRASE_PROMPT

qa_system_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI assistant that answers user queries based on the context provided. "
            "Use previous messages as context to generate an accurate and concise response. "
            "If you don't have enough context, ask for clarification.",
        ),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

choose_retriever_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You have the ability to choose between two retrievers. One is a pandas retriever and the other is a docs retriever."
            "You will be given a question and you will need to decide which retriever to use.",
        ),
        ("human", "{question}"),
    ]
)

combine_docs_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_TEMPLATE),
        ("human", HUMAN_TEMPLATE),
    ]
)

document_prompt = PromptTemplate(
    input_variables=["page_content"], template="{page_content}"
)

question_prompt = PromptTemplate.from_template(REPHRASE_PROMPT)
