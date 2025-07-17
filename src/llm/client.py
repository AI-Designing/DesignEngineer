import os
# Google Gemini import
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

class LLMClient:
    def __init__(self, api_key=None, model_name=None, provider="google"):
        self.provider = provider
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or "gemini-1.5-flash"
        if ChatGoogleGenerativeAI is None:
            raise ImportError("Google Gemini provider not installed. Please install langchain-google-genai.")
        print("[LLMClient] Using Google Gemini for command generation.")
        self.llm = ChatGoogleGenerativeAI(google_api_key=self.api_key, model=self.model_name)

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
            
            from langchain.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert FreeCAD Python scripter. Given a user request and the current FreeCAD state, generate a single valid FreeCAD Python command or script that fulfills the request. IMPORTANT: Only output the Python code, no markdown formatting, no explanations, no code blocks, no backticks. The code should be ready to execute directly. Always use the correct FreeCAD scripting pattern for each primitive. For example: For a box, use: box = doc.addObject('Part::Box', 'Box'); box.Length = 10; box.Width = 10; box.Height = 10; doc.recompute(). For a cylinder, use: cylinder = doc.addObject('Part::Cylinder', 'Cylinder'); cylinder.Radius = 5; cylinder.Height = 20; doc.recompute(). For a sphere, use: sphere = doc.addObject('Part::Sphere', 'Sphere'); sphere.Radius = 10; doc.recompute(). For a cone, use: cone = doc.addObject('Part::Cone', 'Cone'); cone.Radius1 = 5; cone.Radius2 = 10; cone.Height = 50; cone.Angle = 360; doc.recompute(). For a torus, use: torus = doc.addObject('Part::Torus', 'Torus'); torus.Radius1 = 10; torus.Radius2 = 2; doc.recompute(). If the user does not specify dimensions for a primitive, choose reasonable default values (e.g., for a box: Length=10, Width=10, Height=10; for a cylinder: Radius=5, Height=20; for a sphere: Radius=10; for a cone: Radius1=5, Radius2=10, Height=50, Angle=360; for a torus: Radius1=10, Radius2=2)."),
                ("human", f"User request: {nl_command}\nCurrent state: {state_str}")
            ])
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            
            # Clean the response content
            code = response.content.strip()
            
            # Remove markdown code blocks if present
            if code.startswith('```python'):
                code = code[9:]
            elif code.startswith('```'):
                code = code[3:]
            
            if code.endswith('```'):
                code = code[:-3]
            
            code = code.strip()
            
            # Print the generated code for verification
            print("[LLMClient] Generated code:\n", code)
            return code
        except Exception as e:
            print(f"[LLMClient] Error generating command: {e}")
            raise