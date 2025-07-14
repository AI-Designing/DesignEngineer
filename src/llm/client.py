import os
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class LLMClient:
    def __init__(self, api_key=None, model_name="gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.llm = ChatOpenAI(openai_api_key=self.api_key, model_name=self.model_name)

    def generate_command(self, nl_command, state=None):
        """
        Use LLM to generate a FreeCAD Python command from a natural language command and (optionally) the current state.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert FreeCAD Python scripter. Given a user request and the current FreeCAD state, generate a single valid FreeCAD Python command or script that fulfills the request. Only output the code, no explanations."),
            ("human", f"User request: {nl_command}\nCurrent state: {state if state else 'N/A'}")
        ])
        response = self.llm(prompt.to_messages())
        return response.content.strip()