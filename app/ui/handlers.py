import os
from langchain_core.callbacks import BaseCallbackHandler
import streamlit as st
from langchain.schema import AgentAction, AgentFinish


class PrintPandasAgentHandler(BaseCallbackHandler):
    def __init__(self, container):
        self.status = container.status("**Loading**")

    def on_agent_action(self, action: AgentAction, **kwargs):
        self.status.write(f"{action.log}\n\n")

    def on_agent_finish(self, finish: AgentFinish, **kwargs):
        self.status.update(state="complete")


class StreamPandasAgentHandler(BaseCallbackHandler):
    def __init__(
        self, container: st.delta_generator.DeltaGenerator, initial_text: str = ""
    ):
        self.container = container
        self.text = initial_text
        self.run_id_ignore_token = None

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if self.run_id_ignore_token == kwargs.get("run_id", False):
            return
        self.text += token

    def on_llm_end(self, output, **kwargs):
        final_answer = self.text.split("Final Answer: ", 1)[1].strip()
        self.container.markdown(final_answer)


class PrintRetrievalHandler(BaseCallbackHandler):
    def __init__(self, container):
        self.status = container.status("**Loading**")

    def on_retriever_start(self, serialized: dict, query: str, **kwargs):
        self.status.write(f"**Question:** {query}")
        self.status.update(state="complete")

    def on_retriever_end(self, documents, **kwargs):
        for idx, doc in enumerate(documents):
            source = os.path.basename(doc.metadata["source"])
            self.status.write(f"**Document {idx} from {source}**")
            self.status.markdown(doc.page_content)


class StreamHandler(BaseCallbackHandler):
    def __init__(
        self, container: st.delta_generator.DeltaGenerator, initial_text: str = ""
    ):
        self.container = container
        self.text = initial_text
        self.run_id_ignore_token = None

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs):
        # Workaround to prevent showing the rephrased question as output
        if prompts[0].startswith("Human"):
            self.run_id_ignore_token = kwargs.get("run_id")

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if self.run_id_ignore_token == kwargs.get("run_id", False):
            return
        self.text += token
        self.container.markdown(self.text)


# Create a simple class to mimic UploadedFile interface
class StaticFile:
    def __init__(self, path):
        self.name = os.path.basename(path)
        self._path = path

    def getvalue(self):
        with open(self._path, "rb") as f:
            return f.read()
