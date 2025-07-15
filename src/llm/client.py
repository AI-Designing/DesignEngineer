import os
# Use langchain_openai for OpenAI to avoid deprecation warnings
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    # Fallback to older imports if langchain_openai is not available
    try:
        from langchain_community.chat_models import ChatOpenAI
    except ImportError:
        from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Google Gemini import
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

class LLMClient:
    def __init__(self, api_key=None, model_name=None, provider="openai"):
        self.provider = provider
        if provider == "google":
            self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
            self.model_name = model_name or "gemini-1.5-flash"
            if ChatGoogleGenerativeAI is None:
                raise ImportError("Google Gemini provider not installed. Please install langchain-google-genai.")
            print("[LLMClient] Using Google Gemini for command generation.")
            self.llm = ChatGoogleGenerativeAI(google_api_key=self.api_key, model=self.model_name)
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.model_name = model_name or "gpt-3.5-turbo"
            print("[LLMClient] Using OpenAI for command generation.")
            self.llm = ChatOpenAI(openai_api_key=self.api_key, model=self.model_name)

    def generate_command(self, nl_command, state=None):
        """
        Use LLM to generate a FreeCAD Python command from a natural language command and (optionally) the current state.
        """
        print(f"[LLMClient] Provider: {self.provider}, Model: {self.model_name}")
        
        try:
            # Convert state to JSON string if it's a dictionary
            if state is not None:
                import json
                try:
                    state_str = json.dumps(state, indent=2)
                except (TypeError, ValueError) as json_error:
                    print(f"[LLMClient] JSON serialization error: {json_error}")
                    # Fallback to string representation
                    state_str = str(state)
            else:
                state_str = 'N/A'
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert FreeCAD Python scripter. Given a user request and the current FreeCAD state, generate a single valid FreeCAD Python command or script that fulfills the request. Only output the code, no explanations."),
                ("human", f"User request: {nl_command}\nCurrent state: {state_str}")
            ])
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            # Print the generated code for verification
            print("[LLMClient] Generated code:\n", response.content)
            return response.content.strip()
        except Exception as e:
            print(f"[LLMClient] Error generating command: {e}")
            raise