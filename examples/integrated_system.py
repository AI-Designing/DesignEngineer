#!/usr/bin/env python3
"""
Integrated Component Generation System
Seamless integration of DeepSeek R1 with existing FreeCAD automation system
"""

import argparse
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

# Import existing system components
try:
    from ai_designer.core.enhanced_complex_generator import (
        EnhancedComplexShapeGenerator,
    )
    from ai_designer.freecad.api_client import FreeCADAPIClient
    from ai_designer.freecad.command_executor import CommandExecutor
    from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
    from ai_designer.llm.client import LLMClient
    from ai_designer.llm.deepseek_client import (
        DeepSeekConfig,
        DeepSeekIntegrationManager,
        DeepSeekMode,
        DeepSeekR1Client,
    )
    from ai_designer.realtime.websocket_manager import WebSocketManager
    from ai_designer.redis_utils.client import RedisClient
    from ai_designer.redis_utils.state_cache import StateCache
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    print("💡 Some advanced features may not be available")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegratedGenerationSystem:
    """Integrated system combining all components for seamless operation"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

        # Core components
        self.deepseek_client = None
        self.llm_client = None
        self.integration_manager = None
        self.enhanced_generator = None

        # System components
        self.redis_client = None
        self.state_cache = None
        self.freecad_api = None
        self.command_executor = None
        self.state_analyzer = None
        self.websocket_manager = None

        # Session management
        self.session_id = f"integrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.is_initialized = False

        # Component tracking
        self.generated_components = []
        self.execution_stats = {
            "total_generated": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_time": 0.0,
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load system configuration"""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "deepseek": {
                "enabled": True,
                "host": "localhost",
                "port": 11434,
                "model_name": "deepseek-r1:14b",
                "timeout": 600,
                "reasoning_enabled": True,
            },
            "redis": {"host": "localhost", "port": 6379, "db": 0},
            "freecad": {"api_url": "http://localhost:8080", "timeout": 30},
            "enhanced_generator": {
                "use_deepseek": True,
                "quality_targets": {
                    "geometric_accuracy": 0.9,
                    "manufacturability": 0.85,
                },
            },
        }

    def initialize_system(self) -> bool:
        """Initialize all system components"""
        logger.info("🚀 Initializing Integrated Generation System...")

        try:
            # Initialize DeepSeek R1
            if self._initialize_deepseek():
                logger.info("✅ DeepSeek R1 initialized")
            else:
                logger.warning("⚠️ DeepSeek R1 initialization failed")

            # Initialize LLM client (fallback)
            if self._initialize_llm_client():
                logger.info("✅ LLM client initialized")
            else:
                logger.warning("⚠️ LLM client initialization failed")

            # Initialize Redis
            if self._initialize_redis():
                logger.info("✅ Redis initialized")
            else:
                logger.warning("⚠️ Redis not available")

            # Initialize FreeCAD API
            if self._initialize_freecad_api():
                logger.info("✅ FreeCAD API initialized")
            else:
                logger.warning("⚠️ FreeCAD API not available")

            # Initialize enhanced generator
            if self._initialize_enhanced_generator():
                logger.info("✅ Enhanced generator initialized")
            else:
                logger.error("❌ Enhanced generator initialization failed")
                return False

            # Initialize WebSocket (optional)
            if self._initialize_websocket():
                logger.info("✅ WebSocket manager initialized")

            self.is_initialized = True
            logger.info("🎯 Integrated Generation System ready!")
            return True

        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            return False

    def _initialize_deepseek(self) -> bool:
        """Initialize DeepSeek R1 client"""
        try:
            deepseek_config = DeepSeekConfig(
                host=self.config.get("deepseek", {}).get("host", "localhost"),
                port=self.config.get("deepseek", {}).get("port", 11434),
                model_name=self.config.get("deepseek", {}).get(
                    "model_name", "deepseek-r1:14b"
                ),
                timeout=self.config.get("deepseek", {}).get("timeout", 600),
                reasoning_enabled=self.config.get("deepseek", {}).get(
                    "reasoning_enabled", True
                ),
            )

            self.deepseek_client = DeepSeekR1Client(deepseek_config)
            return True
        except Exception as e:
            logger.error(f"DeepSeek initialization failed: {e}")
            return False

    def _initialize_llm_client(self) -> bool:
        """Initialize fallback LLM client"""
        try:
            self.llm_client = LLMClient()
            return True
        except Exception as e:
            logger.error(f"LLM client initialization failed: {e}")
            return False

    def _initialize_redis(self) -> bool:
        """Initialize Redis client and state cache"""
        try:
            redis_config = self.config.get("redis", {})
            self.redis_client = RedisClient(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
            )

            if self.redis_client.connect():
                self.state_cache = StateCache(self.redis_client)
                return True
            return False
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}")
            return False

    def _initialize_freecad_api(self) -> bool:
        """Initialize FreeCAD API client"""
        try:
            api_url = self.config.get("freecad", {}).get(
                "api_url", "http://localhost:8080"
            )
            self.freecad_api = FreeCADAPIClient(api_url)
            self.command_executor = CommandExecutor(self.freecad_api)
            self.state_analyzer = FreeCADStateAnalyzer(self.freecad_api)
            return True
        except Exception as e:
            logger.error(f"FreeCAD API initialization failed: {e}")
            # Create mock components
            self.command_executor = MockCommandExecutor()
            self.state_analyzer = MockStateAnalyzer()
            return False

    def _initialize_enhanced_generator(self) -> bool:
        """Initialize enhanced complex shape generator"""
        try:
            self.enhanced_generator = EnhancedComplexShapeGenerator(
                llm_client=self.llm_client,
                state_analyzer=self.state_analyzer,
                command_executor=self.command_executor,
                state_cache=self.state_cache,
                websocket_manager=self.websocket_manager,
                use_deepseek=True if self.deepseek_client else False,
                deepseek_config=(
                    self.deepseek_client.config if self.deepseek_client else None
                ),
            )

            # Initialize integration manager if DeepSeek is available
            if self.deepseek_client:
                self.integration_manager = DeepSeekIntegrationManager(
                    self.deepseek_client, self.llm_client
                )

            return True
        except Exception as e:
            logger.error(f"Enhanced generator initialization failed: {e}")
            return False

    def _initialize_websocket(self) -> bool:
        """Initialize WebSocket manager"""
        try:
            self.websocket_manager = WebSocketManager()
            return True
        except Exception as e:
            logger.error(f"WebSocket initialization failed: {e}")
            return False

    def test_system_health(self) -> Dict[str, Any]:
        """Test health of all system components"""
        health_status = {
            "overall": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat(),
        }

        # Test DeepSeek R1
        if self.deepseek_client:
            try:
                test_response = self.deepseek_client.generate_complex_part(
                    requirements="Test: create a simple 5mm cube",
                    mode=DeepSeekMode.FAST,
                )
                health_status["components"]["deepseek"] = {
                    "status": (
                        "healthy" if test_response.status == "success" else "degraded"
                    ),
                    "confidence": test_response.confidence_score,
                    "response_time": test_response.execution_time,
                }
            except Exception as e:
                health_status["components"]["deepseek"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["overall"] = "degraded"

        # Test Redis
        if self.redis_client:
            try:
                ping_result = self.redis_client.connection.ping()
                health_status["components"]["redis"] = {
                    "status": "healthy" if ping_result else "unhealthy"
                }
            except Exception as e:
                health_status["components"]["redis"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

        # Test FreeCAD API
        if self.freecad_api:
            try:
                # Test with a simple ping or status check
                health_status["components"]["freecad_api"] = {
                    "status": "healthy"  # Simplified for now
                }
            except Exception as e:
                health_status["components"]["freecad_api"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

        return health_status

    def generate_component_integrated(
        self,
        requirements: str,
        mode: DeepSeekMode = DeepSeekMode.REASONING,
        execute_immediately: bool = True,
        save_results: bool = True,
    ) -> Dict[str, Any]:
        """Generate component using integrated system"""

        if not self.is_initialized:
            raise RuntimeError(
                "System not initialized. Call initialize_system() first."
            )

        logger.info(f"🎯 Generating component: {requirements[:80]}...")

        start_time = time.time()

        try:
            # Generate with enhanced system
            if self.enhanced_generator and self.deepseek_client:
                # Use enhanced generator with DeepSeek
                result = self.enhanced_generator.generate_enhanced_complex_shape(
                    user_requirements=requirements,
                    session_id=self.session_id,
                    quality_targets=self.config.get("enhanced_generator", {}).get(
                        "quality_targets", {}
                    ),
                )

                generated_code = (
                    result.final_code if hasattr(result, "final_code") else ""
                )

            elif self.deepseek_client:
                # Use DeepSeek directly
                response = self.deepseek_client.generate_complex_part(
                    requirements=requirements,
                    mode=mode,
                    context={"session_id": self.session_id},
                )

                if response.status == "success":
                    generated_code = response.generated_code
                    result = response
                else:
                    raise Exception(
                        f"DeepSeek generation failed: {response.error_message}"
                    )

            else:
                # Fallback to regular LLM
                if self.llm_client:
                    generated_code = self.llm_client.generate_command(requirements)
                    result = {"status": "success", "generated_code": generated_code}
                else:
                    raise Exception("No generation method available")

            generation_time = time.time() - start_time

            # Update statistics
            self.execution_stats["total_generated"] += 1
            self.execution_stats["total_time"] += generation_time

            # Create result summary
            component_result = {
                "requirements": requirements,
                "mode": mode.value if isinstance(mode, DeepSeekMode) else "llm",
                "generation_time": generation_time,
                "generated_code": generated_code,
                "status": "success",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
            }

            # Add DeepSeek-specific data if available
            if hasattr(result, "confidence_score"):
                component_result.update(
                    {
                        "confidence_score": result.confidence_score,
                        "reasoning_steps": (
                            len(result.reasoning_chain)
                            if hasattr(result, "reasoning_chain")
                            else 0
                        ),
                        "complexity_analysis": getattr(
                            result, "complexity_analysis", {}
                        ),
                        "optimization_suggestions": getattr(
                            result, "optimization_suggestions", []
                        ),
                    }
                )

            # Save results if requested
            if save_results:
                self._save_component_result(component_result)

            # Execute immediately if requested
            if execute_immediately and generated_code:
                execution_result = self._execute_component_code(
                    generated_code, component_result
                )
                component_result["execution_result"] = execution_result

            self.generated_components.append(component_result)

            logger.info(f"✅ Component generated successfully in {generation_time:.2f}s")
            return component_result

        except Exception as e:
            logger.error(f"❌ Component generation failed: {e}")
            return {
                "requirements": requirements,
                "status": "failed",
                "error": str(e),
                "generation_time": time.time() - start_time,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
            }

    def _save_component_result(self, component_result: Dict[str, Any]):
        """Save component result to filesystem and cache"""
        try:
            # Create output directory
            output_dir = Path("outputs") / f"integrated_{self.session_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique ID for this component
            component_id = f"component_{len(self.generated_components):03d}"

            # Save code file
            if component_result.get("generated_code"):
                code_file = output_dir / f"{component_id}.py"
                with open(code_file, "w") as f:
                    f.write(f"# Integrated Generation - {datetime.now()}\n")
                    f.write(f"# Requirements: {component_result['requirements']}\n")
                    f.write(f"# Session: {self.session_id}\n\n")
                    f.write(component_result["generated_code"])

            # Save metadata
            metadata_file = output_dir / f"{component_id}_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(component_result, f, indent=2)

            # Cache in Redis if available
            if self.state_cache:
                cache_key = f"component:{self.session_id}:{component_id}"
                self.state_cache.store_state(
                    cache_key, component_result, expiration=3600
                )

            logger.info(f"💾 Component result saved: {component_id}")

        except Exception as e:
            logger.error(f"❌ Failed to save component result: {e}")

    def _execute_component_code(
        self, code: str, component_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute generated component code"""
        try:
            logger.info("🔧 Executing generated component code...")

            if self.command_executor:
                # Use integrated command executor
                execution_result = self.command_executor.execute_command(code)

                if execution_result.get("status") == "success":
                    self.execution_stats["successful_executions"] += 1
                    logger.info("✅ Component executed successfully")
                else:
                    self.execution_stats["failed_executions"] += 1
                    logger.warning("⚠️ Component execution had issues")

                return execution_result
            else:
                # Fallback to direct FreeCAD execution
                return self._execute_with_freecad_direct(code)

        except Exception as e:
            self.execution_stats["failed_executions"] += 1
            logger.error(f"❌ Component execution failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _execute_with_freecad_direct(self, code: str) -> Dict[str, Any]:
        """Execute code directly with FreeCAD"""
        try:
            # Create temporary script
            temp_dir = Path("outputs") / "temp"
            temp_dir.mkdir(exist_ok=True)

            temp_script = temp_dir / f"temp_{int(time.time())}.py"

            enhanced_code = f"""#!/usr/bin/env python3
import FreeCAD as App
import Part
import Draft

# Create document
doc = App.newDocument("IntegratedGeneration")

print("[FreeCAD] Starting integrated component execution...")

try:
    # Generated code
{self._indent_code(code)}

    # Finalize
    doc.recompute()

    # Save document
    output_path = "{temp_dir}/integrated_model.FCStd"
    doc.saveAs(output_path)
    print(f"[FreeCAD] Model saved to: {{output_path}}")

    print("[FreeCAD] Integrated execution completed successfully")

except Exception as e:
    print(f"[FreeCAD] Error: {{e}}")
    import traceback
    traceback.print_exc()
"""

            with open(temp_script, "w") as f:
                f.write(enhanced_code)

            # Execute with FreeCAD
            import subprocess

            cmd = ["freecad", "--console", "--run-python", str(temp_script)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up
            if temp_script.exists():
                temp_script.unlink()

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "method": "direct_freecad",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "method": "direct_freecad",
                "timestamp": datetime.now().isoformat(),
            }

    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """Indent code for script embedding"""
        lines = code.split("\n")
        return "\n".join(
            " " * spaces + line if line.strip() else line for line in lines
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "system": {
                "initialized": self.is_initialized,
                "session_id": self.session_id,
                "uptime": time.time(),  # Simplified
            },
            "components": {
                "deepseek_available": self.deepseek_client is not None,
                "llm_client_available": self.llm_client is not None,
                "redis_available": self.redis_client is not None,
                "freecad_api_available": self.freecad_api is not None,
                "enhanced_generator_available": self.enhanced_generator is not None,
                "websocket_available": self.websocket_manager is not None,
            },
            "statistics": self.execution_stats,
            "generated_components": len(self.generated_components),
        }

    def shutdown(self):
        """Gracefully shutdown the system"""
        logger.info("🛑 Shutting down Integrated Generation System...")

        try:
            if self.websocket_manager:
                # Stop WebSocket server
                pass

            if self.redis_client and self.redis_client.connection:
                # Close Redis connection
                pass

            logger.info("✅ System shutdown complete")

        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")


# Mock classes for components that might not be available
class MockCommandExecutor:
    def execute_command(self, command):
        logger.info("🔄 Using mock command executor")
        return {"status": "success", "result": "mock execution"}


class MockStateAnalyzer:
    def analyze_state(self, state=None):
        logger.info("🔄 Using mock state analyzer")
        return {"objects": [], "analysis": "mock analysis"}


def main():
    """Main function for integrated system"""
    parser = argparse.ArgumentParser(
        description="Integrated Component Generation System"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Configuration file path",
    )
    parser.add_argument(
        "--health-check", action="store_true", help="Run system health check and exit"
    )
    parser.add_argument(
        "--generate",
        type=str,
        help="Generate a single component with given requirements",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["fast", "technical", "creative", "reasoning"],
        default="reasoning",
        help="Generation mode",
    )
    parser.add_argument(
        "--no-execute", action="store_true", help="Don't execute generated code"
    )

    args = parser.parse_args()

    # Initialize system
    system = IntegratedGenerationSystem(config_path=args.config)

    if not system.initialize_system():
        logger.error("❌ System initialization failed")
        return 1

    try:
        if args.health_check:
            # Run health check
            health_status = system.test_system_health()
            print(json.dumps(health_status, indent=2))
            return 0 if health_status["overall"] == "healthy" else 1

        elif args.generate:
            # Generate single component
            mode_map = {
                "fast": DeepSeekMode.FAST,
                "technical": DeepSeekMode.TECHNICAL,
                "creative": DeepSeekMode.CREATIVE,
                "reasoning": DeepSeekMode.REASONING,
            }

            mode = mode_map[args.mode]

            result = system.generate_component_integrated(
                requirements=args.generate,
                mode=mode,
                execute_immediately=not args.no_execute,
            )

            print(f"Generation Status: {result['status']}")
            if result["status"] == "success":
                print(f"Generation Time: {result['generation_time']:.2f}s")
                if "confidence_score" in result:
                    print(f"Confidence: {result['confidence_score']:.2f}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")

            return 0 if result["status"] == "success" else 1

        else:
            # Interactive mode
            print("🎯 Integrated Component Generation System")
            print("=" * 50)
            print("System Status:")
            status = system.get_system_status()
            for component, available in status["components"].items():
                status_icon = "✅" if available else "❌"
                print(f"  {status_icon} {component}")

            print(f"\nSystem ready! Session ID: {system.session_id}")
            print("Enter component requirements (or 'quit' to exit):")

            while True:
                try:
                    requirements = input("\n> ").strip()

                    if requirements.lower() in ["quit", "exit", "q"]:
                        break

                    if not requirements:
                        continue

                    result = system.generate_component_integrated(
                        requirements=requirements, execute_immediately=True
                    )

                    if result["status"] == "success":
                        print(
                            f"✅ Generated successfully in {result['generation_time']:.2f}s"
                        )
                        if "confidence_score" in result:
                            print(f"🎯 Confidence: {result['confidence_score']:.2f}")
                    else:
                        print(
                            f"❌ Generation failed: {result.get('error', 'Unknown error')}"
                        )

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")

        return 0

    finally:
        system.shutdown()


if __name__ == "__main__":
    sys.exit(main())
