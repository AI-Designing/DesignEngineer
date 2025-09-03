import logging
import os
from typing import Any, Dict, Optional

# Import secure configuration
from ..config import ConfigurationError, get_api_key

# Google Gemini import
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: str = "google",
    ):
        """
        Initialize LLM client with secure API key handling.

        Args:
            api_key: Optional API key (if not provided, loaded from secure config)
            model_name: Model name to use (defaults to gemini-1.5-flash)
            provider: LLM provider (currently only 'google' supported)
        """
        self.provider = provider
        self.model_name = model_name or "gemini-1.5-flash"

        # Securely get API key
        try:
            self.api_key = api_key or get_api_key()
        except ConfigurationError as e:
            logger.error(f"Failed to get API key: {e}")
            raise

        if ChatGoogleGenerativeAI is None:
            raise ImportError(
                "Google Gemini provider not installed. Please install langchain-google-genai."
            )

        logger.info("[LLMClient] Using Google Gemini for command generation.")
        logger.info(f"[LLMClient] Model: {self.model_name}")

        # Initialize LLM with secure API key
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=self.api_key, model=self.model_name
        )

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
                state_str = "N/A"

            from langchain.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are an expert FreeCAD Python scripter. Given a user request and the current FreeCAD state, generate a single valid FreeCAD Python command or script that fulfills the request. IMPORTANT: Only output the Python code, no markdown formatting, no explanations, no code blocks, no backticks. The code should be ready to execute directly.

BASIC PRIMITIVES:
- Box: box = doc.addObject('Part::Box', 'Box'); box.Length = 10; box.Width = 10; box.Height = 10; doc.recompute()
- Cylinder: cylinder = doc.addObject('Part::Cylinder', 'Cylinder'); cylinder.Radius = 5; cylinder.Height = 20; doc.recompute()
- Sphere: sphere = doc.addObject('Part::Sphere', 'Sphere'); sphere.Radius = 10; doc.recompute()
- Cone: cone = doc.addObject('Part::Cone', 'Cone'); cone.Radius1 = 5; cone.Radius2 = 10; cone.Height = 50; cone.Angle = 360; doc.recompute()
- Torus: torus = doc.addObject('Part::Torus', 'Torus'); torus.Radius1 = 10; torus.Radius2 = 2; doc.recompute()

GEAR CREATION:
For gears, create a simplified representation using cylinders and cuts. Example gear:
```
import FreeCAD as App
import Part
doc = App.ActiveDocument

# Create gear body (main cylinder)
gear_body = doc.addObject('Part::Cylinder', 'GearBody')
gear_body.Radius = 25
gear_body.Height = 10
gear_body.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

# Create central bore
bore = doc.addObject('Part::Cylinder', 'Bore')
bore.Radius = 5
bore.Height = 12
bore.Placement = App.Placement(App.Vector(0, 0, -1), App.Rotation())

# Create gear with bore
gear_with_bore = doc.addObject('Part::Cut', 'Gear')
gear_with_bore.Base = gear_body
gear_with_bore.Tool = bore

doc.recompute()
```

POSITIONING AND BOOLEAN OPERATIONS:
- Positioning: obj.Placement = App.Placement(App.Vector(x,y,z), App.Rotation())
- Fusion: fusion = doc.addObject('Part::MultiFuse', 'Fusion'); fusion.Shapes = [obj1, obj2]; doc.recompute()
- Cut: cut = doc.addObject('Part::Cut', 'Cut'); cut.Base = base_obj; cut.Tool = tool_obj; doc.recompute()

DEFAULT DIMENSIONS:
Box: Length=10, Width=10, Height=10
Cylinder: Radius=5, Height=20
Sphere: Radius=10
Cone: Radius1=5, Radius2=10, Height=50, Angle=360
Torus: Radius1=10, Radius2=2
Gear: Radius=25, Height=10, Bore=5""",
                    ),
                    (
                        "human",
                        f"User request: {nl_command}\nCurrent state: {state_str}",
                    ),
                ]
            )
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)

            # Clean the response content - handle different response types
            if hasattr(response, "content"):
                code = response.content.strip()
            elif hasattr(response, "text") and callable(getattr(response, "text")):
                code = response.text().strip()
            elif hasattr(response, "text"):
                code = response.text.strip()
            else:
                code = str(response).strip()

            # Remove markdown code blocks if present
            if code.startswith("```python"):
                code = code[9:]
            elif code.startswith("```"):
                code = code[3:]

            if code.endswith("```"):
                code = code[:-3]

            code = code.strip()

            # Print the generated code for verification
            print("[LLMClient] Generated code:\n", code)
            return code
        except Exception as e:
            print(f"[LLMClient] Error generating command: {e}")
            raise
