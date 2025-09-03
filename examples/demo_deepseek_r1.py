"""
DeepSeek R1 Complex Part Generation Demo
Demonstrates the integration of DeepSeek R1 for creating complex FreeCAD parts
"""

import logging
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_designer.llm.client import LLMClient
from ai_designer.llm.deepseek_client import (
    DeepSeekConfig,
    DeepSeekIntegrationManager,
    DeepSeekMode,
    DeepSeekR1Client,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DeepSeekDemo:
    """Demo class for DeepSeek R1 complex part generation"""

    def __init__(self):
        self.setup_clients()

    def setup_clients(self):
        """Initialize the necessary clients"""
        logger.info("🚀 Setting up DeepSeek R1 Demo...")

        try:
            # Configure DeepSeek R1
            deepseek_config = DeepSeekConfig(
                host="localhost",
                port=8000,  # Default port for local DeepSeek R1
                model_name="deepseek-r1",
                timeout=300,
                reasoning_enabled=True,
            )

            # Initialize DeepSeek client
            self.deepseek_client = DeepSeekR1Client(deepseek_config)

            # Initialize fallback LLM client (Gemini)
            try:
                self.fallback_client = LLMClient()
                logger.info("✅ Fallback LLM client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Fallback client failed: {e}")
                self.fallback_client = None

            # Initialize integration manager
            self.integration_manager = DeepSeekIntegrationManager(
                self.deepseek_client, self.fallback_client
            )

            logger.info("✅ DeepSeek R1 Demo setup complete!")

        except Exception as e:
            logger.error(f"❌ Demo setup failed: {e}")
            logger.info("💡 Make sure DeepSeek R1 is running locally on port 8000")
            raise

    def test_connection(self):
        """Test DeepSeek R1 connection"""
        logger.info("🔍 Testing DeepSeek R1 connection...")

        try:
            # Test basic connectivity
            response = self.deepseek_client.generate_complex_part(
                requirements="Create a simple test cube", mode=DeepSeekMode.FAST
            )

            if response.status == "success":
                logger.info("✅ DeepSeek R1 connection successful!")
                logger.info(f"   Confidence: {response.confidence_score:.2f}")
                logger.info(f"   Execution time: {response.execution_time:.2f}s")
                return True
            else:
                logger.error(f"❌ DeepSeek R1 test failed: {response.error_message}")
                return False

        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False

    def demo_simple_part(self):
        """Demo: Generate a simple mechanical part"""
        logger.info("🔧 Demo 1: Simple Mechanical Part")

        requirements = """
        Create a simple shaft with the following specifications:
        - Length: 100mm
        - Diameter: 20mm
        - Add a keyway that is 5mm wide and 2.5mm deep
        - Add a chamfer of 1mm on both ends
        """

        response = self.deepseek_client.generate_complex_part(
            requirements=requirements,
            mode=DeepSeekMode.TECHNICAL,
            constraints={
                "material": "steel",
                "tolerance": 0.05,
                "surface_finish": "machined",
            },
        )

        self._display_results("Simple Shaft", response)
        return response

    def demo_complex_assembly(self):
        """Demo: Generate a complex assembly"""
        logger.info("🏗️ Demo 2: Complex Mechanical Assembly")

        requirements = """
        Create a gear assembly with the following components:
        1. Main gear: 50mm diameter, 20 teeth, 10mm thick
        2. Pinion gear: 25mm diameter, 10 teeth, 8mm thick
        3. Mounting bracket to hold both gears
        4. Shafts for both gears with proper spacing
        5. Ensure proper gear mesh and clearances
        """

        response = self.deepseek_client.generate_complex_part(
            requirements=requirements,
            mode=DeepSeekMode.REASONING,
            context={
                "application": "speed reducer",
                "environment": "industrial",
                "load_requirements": "medium duty",
            },
            constraints={
                "gear_ratio": 2.0,
                "center_distance": 37.5,
                "pressure_angle": 20,
                "module": 2.0,
            },
        )

        self._display_results("Gear Assembly", response)
        return response

    def demo_creative_design(self):
        """Demo: Creative design generation"""
        logger.info("🎨 Demo 3: Creative Design Challenge")

        requirements = """
        Design an innovative phone stand that:
        - Adjusts to multiple viewing angles
        - Accommodates phones of different sizes
        - Has a modern, aesthetic appearance
        - Can be easily manufactured
        - Includes cable management features
        """

        response = self.deepseek_client.generate_complex_part(
            requirements=requirements,
            mode=DeepSeekMode.CREATIVE,
            context={
                "target_market": "premium consumers",
                "manufacturing_method": "3D printing",
                "material_preference": "sustainable",
            },
        )

        self._display_results("Creative Phone Stand", response)
        return response

    def demo_reasoning_chain(self):
        """Demo: Show detailed reasoning chain"""
        logger.info("🧠 Demo 4: Detailed Reasoning Analysis")

        requirements = """
        Design a complex mechanical linkage system that converts
        rotational motion to linear motion with the following requirements:
        - Input: rotational motion, 0-360 degrees
        - Output: linear motion, 50mm stroke
        - Smooth operation with minimal backlash
        - Compact design for integration
        """

        response = self.deepseek_client.generate_complex_part(
            requirements=requirements, mode=DeepSeekMode.REASONING
        )

        self._display_detailed_reasoning(response)
        return response

    def demo_integration_manager(self):
        """Demo: Integration manager with fallback"""
        logger.info("🔄 Demo 5: Integration Manager with Fallback")

        test_commands = [
            "Create a simple box 10x10x10mm",
            "Design a complex turbine blade",
            "Generate a precision bearing assembly",
            "Create an artistic lamp shade",
        ]

        results = []
        for command in test_commands:
            logger.info(f"🔍 Testing: {command}")

            try:
                code = self.integration_manager.generate_command(
                    nl_command=command, mode="auto"  # Let the system decide
                )

                results.append(
                    {
                        "command": command,
                        "success": True,
                        "code_length": len(code),
                        "has_freecad_imports": "import FreeCAD" in code
                        or "import App" in code,
                    }
                )

                logger.info(f"✅ Generated {len(code)} characters of code")

            except Exception as e:
                logger.error(f"❌ Failed: {e}")
                results.append({"command": command, "success": False, "error": str(e)})

        # Display integration statistics
        self._display_integration_stats(results)
        return results

    def _display_results(self, demo_name: str, response):
        """Display generation results"""
        logger.info(f"📊 Results for {demo_name}:")
        logger.info(f"   Status: {response.status}")
        logger.info(f"   Confidence: {response.confidence_score:.2f}")
        logger.info(f"   Execution time: {response.execution_time:.2f}s")
        logger.info(f"   Reasoning steps: {len(response.reasoning_chain)}")
        logger.info(f"   Code length: {len(response.generated_code)} characters")

        if response.complexity_analysis:
            complexity = response.complexity_analysis
            logger.info(
                f"   Complexity score: {complexity.get('complexity_score', 0):.1f}/10"
            )
            logger.info(
                f"   Skill level: {complexity.get('skill_level_required', 'unknown')}"
            )

        if response.optimization_suggestions:
            logger.info(
                f"   Optimization suggestions: {len(response.optimization_suggestions)}"
            )
            for i, suggestion in enumerate(response.optimization_suggestions[:3]):
                logger.info(f"     {i+1}. {suggestion}")

        # Show a snippet of the generated code
        code_snippet = (
            response.generated_code[:200] + "..."
            if len(response.generated_code) > 200
            else response.generated_code
        )
        logger.info(f"   Code snippet:\n{code_snippet}")
        logger.info("=" * 60)

    def _display_detailed_reasoning(self, response):
        """Display detailed reasoning chain"""
        logger.info("🧠 Detailed Reasoning Chain:")

        for i, step in enumerate(response.reasoning_chain):
            logger.info(f"   Step {i+1}: {step.description}")
            logger.info(f"           Reasoning: {step.reasoning}")
            logger.info(f"           Confidence: {step.confidence:.2f}")
            if step.code_snippet:
                snippet = (
                    step.code_snippet[:100] + "..."
                    if len(step.code_snippet) > 100
                    else step.code_snippet
                )
                logger.info(f"           Code: {snippet}")
            logger.info(f"           Status: {step.validation_status}")
            logger.info("   ---")

        logger.info("=" * 60)

    def _display_integration_stats(self, results):
        """Display integration manager statistics"""
        total_tests = len(results)
        successful_tests = len([r for r in results if r["success"]])

        logger.info("📈 Integration Manager Statistics:")
        logger.info(f"   Total tests: {total_tests}")
        logger.info(f"   Successful: {successful_tests}")
        logger.info(f"   Success rate: {successful_tests/total_tests*100:.1f}%")

        # Get integration metrics
        try:
            metrics = self.integration_manager.get_integration_metrics()
            logger.info(f"   DeepSeek usage: {metrics['deepseek_usage_rate']*100:.1f}%")
            logger.info(f"   Fallback usage: {metrics['fallback_usage_rate']*100:.1f}%")
            logger.info(f"   Hybrid usage: {metrics['hybrid_usage_rate']*100:.1f}%")
        except Exception as e:
            logger.warning(f"Could not get integration metrics: {e}")

        logger.info("=" * 60)

    def run_all_demos(self):
        """Run all demonstration scenarios"""
        logger.info("🎯 Starting DeepSeek R1 Complex Part Generation Demos")
        logger.info("=" * 60)

        # Test connection first
        if not self.test_connection():
            logger.error("❌ Connection test failed. Aborting demos.")
            return False

        demo_functions = [
            self.demo_simple_part,
            self.demo_complex_assembly,
            self.demo_creative_design,
            self.demo_reasoning_chain,
            self.demo_integration_manager,
        ]

        results = {}
        for demo_func in demo_functions:
            try:
                logger.info("\n")
                result = demo_func()
                results[demo_func.__name__] = result
                logger.info("✅ Demo completed successfully")
            except Exception as e:
                logger.error(f"❌ Demo failed: {e}")
                results[demo_func.__name__] = None

        # Final summary
        self._display_final_summary(results)
        return results

    def _display_final_summary(self, results):
        """Display final demo summary"""
        logger.info("\n" + "=" * 60)
        logger.info("🎉 DeepSeek R1 Demo Summary")
        logger.info("=" * 60)

        successful_demos = len([r for r in results.values() if r is not None])
        total_demos = len(results)

        logger.info(f"   Completed demos: {successful_demos}/{total_demos}")
        logger.info(f"   Success rate: {successful_demos/total_demos*100:.1f}%")

        try:
            # Get final integration metrics if available
            if hasattr(self, "integration_manager"):
                metrics = self.integration_manager.get_integration_metrics()
                logger.info(
                    f"   Overall DeepSeek usage: "
                    f"{metrics['deepseek_usage_rate']*100:.1f}%"
                )
        except Exception as e:
            logger.warning(f"Could not get final metrics: {e}")

        logger.info("=" * 60)
        logger.info(
            "🚀 Demo complete! DeepSeek R1 is ready for complex part generation."
        )


def main():
    """Main demo function"""
    print("🎯 DeepSeek R1 Complex Part Generation Demo")
    print("=" * 60)

    try:
        demo = DeepSeekDemo()
        demo.run_all_demos()

    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure DeepSeek R1 is running locally")
        print("2. Check that the port (8000) is correct")
        print("3. Verify network connectivity")
        print("4. Check the logs for detailed error information")


if __name__ == "__main__":
    main()
