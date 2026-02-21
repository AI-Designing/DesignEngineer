#!/usr/bin/env python3
"""
Continuous FreeCAD Component Generator using Online LLM (Gemini 2.0 Flash)
Automatically generates complex mechanical components using AI reasoning
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_designer.core.enhanced_complex_generator import EnhancedComplexShapeGenerator
from ai_designer.llm.client import LLMClient
from ai_designer.llm.providers.online_codegen import OnlineCodeGenClient, OnlineCodeGenConfig
from ai_designer.llm.providers.deepseek import DeepSeekMode

# Legacy aliases for any internal usage
DeepSeekConfig = OnlineCodeGenConfig
DeepSeekR1Client = OnlineCodeGenClient

# DeepSeekIntegrationManager shim (keeps the attribute name alive)
class DeepSeekIntegrationManager:
    """Lightweight shim that delegates to OnlineCodeGenClient."""
    def __init__(self, client, fallback_client=None):
        self._client = client
    def generate_command(self, nl_command: str, state=None, mode: str = "auto") -> str:
        resp = self._client.generate_complex_part(requirements=nl_command)
        if resp.status == "success":
            return resp.generated_code
        raise RuntimeError(resp.error_message or "Generation failed")
    def get_integration_metrics(self):
        return self._client.get_performance_metrics()


# Mock classes for missing components
class MockStateAnalyzer:
    """Mock state analyzer for testing"""

    def analyze_state(self, state=None):
        return {"objects": [], "analysis": "mock analysis"}


class MockCommandExecutor:
    """Mock command executor for testing"""

    def execute_command(self, command):
        return {"status": "success", "result": "mock execution"}


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ContinuousComponentGenerator:
    """Continuous generator for complex FreeCAD components using DeepSeek R1"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.deepseek_client = None
        self.integration_manager = None
        self.enhanced_generator = None
        self.session_id = f"continuous_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.generation_count = 0

        # Component categories to generate
        self.component_categories = [
            "mechanical_parts",
            "assemblies",
            "gears",
            "bearings",
            "shafts",
            "housings",
            "brackets",
            "connectors",
            "mechanisms",
        ]

        # Complexity levels
        self.complexity_levels = ["simple", "moderate", "complex", "advanced"]

        self.setup_clients()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            # Fallback configuration
            return {
                "deepseek": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 11434,
                    "model_name": "deepseek-r1:14b",
                    "timeout": 600,
                    "reasoning_enabled": True,
                }
            }

    def setup_clients(self):
        """Initialize the online code-generation client."""
        logger.info("\U0001f680 Setting up Continuous Component Generator...")

        try:
            # Read optional model override from config
            codegen_cfg = self.config.get("online_codegen", {})
            config = OnlineCodeGenConfig(
                model=codegen_cfg.get("model", "google/gemini-2.0-flash"),
                fallback_model=codegen_cfg.get("fallback_model", "openai/gpt-4o"),
                temperature=codegen_cfg.get("temperature", 0.1),
                max_tokens=codegen_cfg.get("max_tokens", 8192),
                timeout=codegen_cfg.get("timeout", 120),
            )

            self.deepseek_client = OnlineCodeGenClient(config)
            logger.info(
                f"\u2705 Online code-gen client initialised (model: {self.deepseek_client.config.model})"
            )

            # Lightweight integration manager (for legacy code paths)
            self.integration_manager = DeepSeekIntegrationManager(self.deepseek_client)

            # Enhanced generator (uses the same online client internally)
            self.enhanced_generator = EnhancedComplexShapeGenerator(
                llm_client=None,
                state_analyzer=MockStateAnalyzer(),
                command_executor=MockCommandExecutor(),
                use_deepseek=True,
                deepseek_config=deepseek_config,
            )

            logger.info("🎯 Continuous Component Generator setup complete!")

        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise

    def test_connection(self) -> bool:
        """Test connection to DeepSeek R1"""
        try:
            logger.info("🔍 Testing DeepSeek R1 connection...")

            # Test with a simple generation
            response = self.deepseek_client.generate_complex_part(
                requirements="Test connection: create a simple 10mm cube",
                mode=DeepSeekMode.FAST,
            )

            if response.status == "success":
                logger.info(
                    f"✅ DeepSeek R1 connection successful - Confidence: {response.confidence_score:.2f}"
                )
                return True
            else:
                logger.error(f"❌ DeepSeek R1 test failed: {response.error_message}")
                return False

        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False

    def generate_component_requirements(self, category: str, complexity: str) -> str:
        """Generate realistic component requirements"""

        requirements_templates = {
            "mechanical_parts": {
                "simple": [
                    "Create a simple shaft with diameter 20mm and length 100mm",
                    "Design a basic flange with 6 bolt holes, diameter 100mm",
                    "Generate a simple bracket with mounting holes",
                ],
                "moderate": [
                    "Create a shaft with keyway, diameter 25mm, length 150mm, key 8x7mm",
                    "Design a bearing housing for 6205 bearing with oil seals",
                    "Generate a mounting bracket with reinforcement ribs",
                ],
                "complex": [
                    "Create a multi-step shaft with different diameters and precision keyways",
                    "Design a complex bearing housing with multiple seals and lubrication ports",
                    "Generate an adjustable mounting bracket with slot mechanisms",
                ],
                "advanced": [
                    "Create a precision shaft assembly with multiple keyways, splines, and threaded sections",
                    "Design a complete bearing assembly with housing, seals, and lubrication system",
                    "Generate a parametric mounting system with adjustable geometry",
                ],
            },
            "gears": {
                "simple": [
                    "Create a spur gear with 20 teeth, module 2mm",
                    "Design a simple pinion gear with 12 teeth",
                    "Generate a basic gear wheel with hub",
                ],
                "moderate": [
                    "Create a helical gear with 25 teeth, helix angle 20 degrees",
                    "Design a bevel gear pair for 90-degree drive",
                    "Generate a gear with keyway and mounting hub",
                ],
                "complex": [
                    "Create a planetary gear system with ring, sun, and planet gears",
                    "Design a worm gear set with proper geometry",
                    "Generate a gear train with multiple reduction stages",
                ],
                "advanced": [
                    "Create a complete differential gear assembly",
                    "Design a harmonic drive gear system",
                    "Generate a compound planetary gear system with multiple stages",
                ],
            },
            "assemblies": {
                "simple": [
                    "Create a simple bolt and nut assembly",
                    "Design a basic shaft and bearing assembly",
                    "Generate a simple coupling connection",
                ],
                "moderate": [
                    "Create a gear box assembly with housing and gears",
                    "Design a linear actuator with shaft and housing",
                    "Generate a rotary joint assembly with bearings",
                ],
                "complex": [
                    "Create a complete transmission assembly with multiple gears",
                    "Design a robot joint with motors and encoders",
                    "Generate a precision linear stage with guides",
                ],
                "advanced": [
                    "Create a complete robotic arm joint assembly",
                    "Design a CNC spindle assembly with bearings and cooling",
                    "Generate a precision measurement instrument assembly",
                ],
            },
        }

        import secrets

        if (
            category in requirements_templates
            and complexity in requirements_templates[category]
        ):
            options = requirements_templates[category][complexity]
            return options[secrets.randbelow(len(options))]
        else:
            return f"Create a {complexity} {category.replace('_', ' ')} component with appropriate features"

    def save_generation_result(self, requirements: str, response, generation_id: int):
        """Save generation results to file"""
        try:
            # Create outputs directory if it doesn't exist
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)

            # Create session directory
            session_dir = outputs_dir / self.session_id
            session_dir.mkdir(exist_ok=True)

            # Save detailed result
            result_data = {
                "generation_id": generation_id,
                "timestamp": datetime.now().isoformat(),
                "requirements": requirements,
                "status": response.status,
                "generated_code": response.generated_code,
                "confidence_score": response.confidence_score,
                "execution_time": response.execution_time,
                "reasoning_steps": len(response.reasoning_chain),
                "complexity_analysis": response.complexity_analysis,
                "optimization_suggestions": response.optimization_suggestions,
            }

            result_file = session_dir / f"generation_{generation_id:03d}.json"
            with open(result_file, "w") as f:
                json.dump(result_data, f, indent=2)

            # Save FreeCAD code separately
            if response.generated_code:
                code_file = session_dir / f"generation_{generation_id:03d}.py"
                with open(code_file, "w") as f:
                    f.write(f"# Generated by DeepSeek R1 - {datetime.now()}\n")
                    f.write(f"# Requirements: {requirements}\n")
                    f.write(f"# Confidence: {response.confidence_score:.2f}\n\n")
                    f.write(response.generated_code)

            logger.info(f"💾 Results saved to {result_file}")

        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

    def execute_freecad_code(self, code: str, generation_id: int) -> bool:
        """Execute generated FreeCAD code"""
        try:
            logger.info(f"🔧 Executing FreeCAD code for generation {generation_id}")

            # Create a temporary Python file
            temp_file = f"temp_generation_{generation_id}.py"
            with open(temp_file, "w") as f:
                f.write(code)

            # Execute with FreeCAD (you can modify this based on your FreeCAD setup)
            import subprocess

            cmd = ["freecad", "--console", "--run-python", temp_file]
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up temp file
            os.remove(temp_file)

            if result.returncode == 0:
                logger.info(
                    f"✅ FreeCAD execution successful for generation {generation_id}"
                )
                return True
            else:
                logger.error(
                    f"❌ FreeCAD execution failed for generation {generation_id}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ FreeCAD execution error: {e}")
            return False

    def run_continuous_generation(
        self,
        max_generations: int = 100,
        delay_seconds: int = 30,
        execute_code: bool = True,
    ):
        """Run continuous component generation"""

        logger.info(f"🚀 Starting continuous generation session: {self.session_id}")
        logger.info(
            f"📊 Parameters: {max_generations} generations, {delay_seconds}s delay"
        )

        # Test connection first
        if not self.test_connection():
            logger.error(
                "❌ DeepSeek R1 connection failed. Aborting continuous generation."
            )
            return

        successful_generations = 0
        failed_generations = 0

        try:
            for i in range(1, max_generations + 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"🎯 Generation {i}/{max_generations}")
                logger.info(f"{'='*60}")

                # Select random category and complexity
                import secrets

                category = self.component_categories[
                    secrets.randbelow(len(self.component_categories))
                ]
                complexity = self.complexity_levels[
                    secrets.randbelow(len(self.complexity_levels))
                ]

                # Generate requirements
                requirements = self.generate_component_requirements(
                    category, complexity
                )
                logger.info(f"📋 Category: {category}")
                logger.info(f"📊 Complexity: {complexity}")
                logger.info(f"📝 Requirements: {requirements}")

                try:
                    # Select appropriate mode based on complexity
                    mode_mapping = {
                        "simple": DeepSeekMode.FAST,
                        "moderate": DeepSeekMode.TECHNICAL,
                        "complex": DeepSeekMode.REASONING,
                        "advanced": DeepSeekMode.REASONING,
                    }
                    mode = mode_mapping.get(complexity, DeepSeekMode.REASONING)

                    # Generate with DeepSeek R1
                    start_time = time.time()
                    response = self.deepseek_client.generate_complex_part(
                        requirements=requirements,
                        mode=mode,
                        context={"session_id": self.session_id, "generation_id": i},
                        constraints={"category": category, "complexity": complexity},
                    )

                    generation_time = time.time() - start_time

                    if response.status == "success":
                        logger.info(f"✅ Generation successful!")
                        logger.info(f"⏱️  Time: {generation_time:.2f}s")
                        logger.info(f"🎯 Confidence: {response.confidence_score:.2f}")
                        logger.info(
                            f"🧠 Reasoning steps: {len(response.reasoning_chain)}"
                        )

                        # Save results
                        self.save_generation_result(requirements, response, i)

                        # Execute FreeCAD code if requested
                        if execute_code and response.generated_code:
                            execution_success = self.execute_freecad_code(
                                response.generated_code, i
                            )
                            if execution_success:
                                logger.info("🎨 FreeCAD execution completed")
                            else:
                                logger.warning("⚠️ FreeCAD execution had issues")

                        successful_generations += 1

                    else:
                        logger.error(f"❌ Generation failed: {response.error_message}")
                        failed_generations += 1

                except Exception as e:
                    logger.error(f"❌ Generation error: {e}")
                    failed_generations += 1

                # Update statistics
                total = successful_generations + failed_generations
                success_rate = (
                    (successful_generations / total) * 100 if total > 0 else 0
                )

                logger.info(f"\n📊 Session Statistics:")
                logger.info(f"   ✅ Successful: {successful_generations}")
                logger.info(f"   ❌ Failed: {failed_generations}")
                logger.info(f"   📈 Success Rate: {success_rate:.1f}%")

                # Wait before next generation
                if i < max_generations:
                    logger.info(f"⏳ Waiting {delay_seconds}s before next generation...")
                    time.sleep(delay_seconds)

        except KeyboardInterrupt:
            logger.info("\n🛑 Continuous generation interrupted by user")

        except Exception as e:
            logger.error(f"❌ Continuous generation error: {e}")

        finally:
            logger.info(f"\n🏁 Continuous generation session completed")
            logger.info(f"📊 Final Statistics:")
            logger.info(f"   ✅ Successful generations: {successful_generations}")
            logger.info(f"   ❌ Failed generations: {failed_generations}")
            logger.info(f"   📈 Overall success rate: {success_rate:.1f}%")
            logger.info(f"   📁 Results saved in: outputs/{self.session_id}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Continuous FreeCAD Component Generator"
    )
    parser.add_argument(
        "--max-generations",
        type=int,
        default=50,
        help="Maximum number of generations (default: 50)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=30,
        help="Delay between generations in seconds (default: 30)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Configuration file path (default: config/config.yaml)",
    )
    parser.add_argument(
        "--no-execute", action="store_true", help="Don't execute generated FreeCAD code"
    )
    parser.add_argument(
        "--test-only", action="store_true", help="Only test connection and exit"
    )

    args = parser.parse_args()

    try:
        # Initialize generator
        generator = ContinuousComponentGenerator(config_path=args.config)

        if args.test_only:
            # Test connection only
            success = generator.test_connection()
            if success:
                logger.info("🎉 DeepSeek R1 connection test successful!")
                return 0
            else:
                logger.error("❌ DeepSeek R1 connection test failed!")
                return 1
        else:
            # Run continuous generation
            generator.run_continuous_generation(
                max_generations=args.max_generations,
                delay_seconds=args.delay,
                execute_code=not args.no_execute,
            )
            return 0

    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
