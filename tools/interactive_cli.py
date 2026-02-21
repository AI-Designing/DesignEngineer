#!/usr/bin/env python3
"""
Interactive Component Generator CLI
Generate complex mechanical components interactively using an online LLM (Gemini 2.0 Flash)
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_designer.llm.providers.online_codegen import OnlineCodeGenClient, OnlineCodeGenConfig
from ai_designer.llm.providers.deepseek import DeepSeekMode

# Legacy aliases
DeepSeekConfig = OnlineCodeGenConfig
DeepSeekR1Client = OnlineCodeGenClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class InteractiveGenerator:
    """Interactive component generator"""

    def __init__(self):
        self.client = None
        self.setup_client()

    def setup_client(self):
        """Set up the online code-generation client."""
        try:
            self.client = OnlineCodeGenClient()
            logger.info(
                f"\u2705 Online code-gen client ready (model: {self.client.config.model})"
            )
        except Exception as e:
            logger.error(f"\u274c Failed to setup online code-gen client: {e}")
            sys.exit(1)

    def get_mode_from_user(self) -> DeepSeekMode:
        """Get generation mode from user"""
        modes = {
            "1": ("fast", DeepSeekMode.FAST, "Quick generation for simple parts"),
            "2": ("technical", DeepSeekMode.TECHNICAL, "Precision engineering parts"),
            "3": ("creative", DeepSeekMode.CREATIVE, "Innovative and artistic designs"),
            "4": (
                "reasoning",
                DeepSeekMode.REASONING,
                "Complex assemblies with full reasoning",
            ),
        }

        print("\\n🎨 Select Generation Mode:")
        for key, (name, mode, desc) in modes.items():
            print(f"  {key}. {name.upper()} - {desc}")

        while True:
            choice = input("\\nEnter choice (1-4): ").strip()
            if choice in modes:
                return modes[choice][1]
            print("❌ Invalid choice. Please enter 1-4.")

    def generate_component(self, requirements: str, mode: DeepSeekMode):
        """Generate a component"""

        print(f"\\n🚀 Generating component...")
        print(f"📋 Requirements: {requirements}")
        print(f"⚙️ Mode: {mode.value}")

        start_time = time.time()

        try:
            response = self.client.generate_complex_part(
                requirements=requirements,
                mode=mode,
                context={"interactive": True, "timestamp": datetime.now().isoformat()},
                constraints={"output_format": "freecad_python"},
            )

            generation_time = time.time() - start_time

            if response.status == "success":
                print(f"\\n✅ Generation successful!")
                print(f"⏱️ Time: {generation_time:.2f}s")
                print(f"🎯 Confidence: {response.confidence_score:.2f}")
                print(f"🧠 Reasoning steps: {len(response.reasoning_chain)}")

                # Show reasoning preview
                if response.reasoning_chain and len(response.reasoning_chain) > 0:
                    print(f"\\n🔍 First reasoning step:")
                    print(f"   {response.reasoning_chain[0].description}")

                # Save results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = Path("outputs") / f"interactive_generation_{timestamp}"
                output_dir.mkdir(parents=True, exist_ok=True)

                # Save code
                code_file = output_dir / "generated_component.py"
                with open(code_file, "w") as f:
                    f.write(f"# Interactive Generation - {datetime.now()}\\n")
                    f.write(f"# Requirements: {requirements}\\n")
                    f.write(f"# Mode: {mode.value}\\n")
                    f.write(f"# Confidence: {response.confidence_score:.2f}\\n\\n")
                    f.write(response.generated_code)

                # Save metadata
                metadata = {
                    "requirements": requirements,
                    "mode": mode.value,
                    "generation_time": generation_time,
                    "confidence_score": response.confidence_score,
                    "status": response.status,
                    "reasoning_steps": len(response.reasoning_chain),
                    "complexity_analysis": response.complexity_analysis,
                    "optimization_suggestions": response.optimization_suggestions,
                }

                with open(output_dir / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)

                print(f"💾 Results saved to: {output_dir}")

                # Show code preview
                if response.generated_code:
                    lines = response.generated_code.split("\\n")
                    preview_lines = [line for line in lines[:15] if line.strip()]
                    print(f"\\n📝 Code Preview (first 15 non-empty lines):")
                    print("-" * 50)
                    for line in preview_lines:
                        print(line)
                    if len(lines) > 15:
                        print("...")
                    print("-" * 50)

                # Ask about execution
                execute = input("\\n🚀 Execute with FreeCAD? (y/n): ").strip().lower()
                if execute == "y":
                    self.execute_freecad(code_file)

                return True

            else:
                print(f"❌ Generation failed: {response.error_message}")
                return False

        except Exception as e:
            print(f"❌ Error during generation: {e}")
            return False

    def execute_freecad(self, code_file: Path):
        """Execute generated code with FreeCAD"""

        print(f"🔧 Executing with FreeCAD...")

        # Create enhanced script
        with open(code_file, "r") as f:
            original_code = f.read()

        enhanced_script = f"""#!/usr/bin/env python3
import FreeCAD as App
import Part
import Draft

# Create new document
doc = App.newDocument("InteractiveGeneration")

print("[FreeCAD] Starting component creation...")

try:
    # Generated code
{self._indent_code(original_code)}

    # Finalize
    doc.recompute()

    # Save document
    output_path = "{code_file.parent}/interactive_model.FCStd"
    doc.saveAs(output_path)
    print(f"[FreeCAD] Model saved to: {{output_path}}")

    # Export to STEP
    step_path = "{code_file.parent}/interactive_model.step"
    import Import
    objects = [obj for obj in doc.Objects if hasattr(obj, 'Shape')]
    if objects:
        Import.export(objects, step_path)
        print(f"[FreeCAD] STEP exported to: {{step_path}}")

    print("[FreeCAD] Component creation completed successfully")

except Exception as e:
    print(f"[FreeCAD] Error: {{e}}")
    import traceback
    traceback.print_exc()
"""

        enhanced_file = code_file.parent / "enhanced_freecad_script.py"
        with open(enhanced_file, "w") as f:
            f.write(enhanced_script)

        # Execute
        cmd = ["freecad", "--console", "--run-python", str(enhanced_file)]
        print(f"🚀 Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ FreeCAD execution successful")
        else:
            print(f"❌ FreeCAD execution failed (exit code: {result.returncode})")

    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """Indent code for script embedding"""
        lines = code.split("\\n")
        return "\\n".join(
            " " * spaces + line if line.strip() else line for line in lines
        )

    def show_examples(self):
        """Show example components"""
        examples = [
            "Create a precision shaft with diameter 30mm, length 200mm, with keyway",
            "Design a spur gear with 20 teeth, module 3mm, with central bore",
            "Create a bearing housing for 6207 bearing with mounting flanges",
            "Design an adjustable bracket with multiple mounting holes",
            "Create a linear actuator housing with guide rails",
            "Design a gear coupling for connecting two shafts",
            "Create a cam follower mechanism with spring return",
            "Design a universal joint assembly",
            "Create a planetary gear reducer housing",
            "Design a robotic gripper finger with articulation",
        ]

        print("\\n💡 Example Components:")
        for i, example in enumerate(examples, 1):
            print(f"  {i:2d}. {example}")

    def run_interactive(self):
        """Run interactive session"""

        print("🎯 Interactive Component Generator")
        print("=" * 50)
        print("Generate complex mechanical components using DeepSeek R1")
        print("Type 'help' for examples, 'quit' to exit")
        print()

        while True:
            try:
                # Get requirements from user
                requirements = input(
                    "\\n📝 Describe the component you want to create: "
                ).strip()

                if not requirements:
                    continue

                if requirements.lower() in ["quit", "exit", "q"]:
                    print("👋 Goodbye!")
                    break

                if requirements.lower() in ["help", "examples", "h"]:
                    self.show_examples()
                    continue

                # Get mode
                mode = self.get_mode_from_user()

                # Generate component
                success = self.generate_component(requirements, mode)

                if success:
                    print("\\n🎉 Component generated successfully!")
                else:
                    print("\\n😞 Generation failed. Please try again.")

                # Ask to continue
                continue_gen = (
                    input("\\n🔄 Generate another component? (y/n): ").strip().lower()
                )
                if continue_gen != "y":
                    print("👋 Thanks for using the Interactive Component Generator!")
                    break

            except KeyboardInterrupt:
                print("\\n\\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\\n❌ Error: {e}")


def main():
    """Main function"""
    generator = InteractiveGenerator()
    generator.run_interactive()


if __name__ == "__main__":
    main()
