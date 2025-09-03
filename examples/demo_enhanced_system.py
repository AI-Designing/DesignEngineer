#!/usr/bin/env python3
"""
Enhanced Complex Shape Generation Demo
Demonstrates the advanced capabilities of the enhanced FreeCAD automation system
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from ai_designer.core.enhanced_complex_generator import (
        ComplexityLevel,
        EnhancedComplexShapeGenerator,
        GenerationMode,
        QualityMetrics,
    )
    from ai_designer.freecad.command_executor import CommandExecutor
    from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
    from ai_designer.llm.client import LLMClient
    from ai_designer.realtime.websocket_manager import WebSocketManager
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    print("💡 This demo requires the enhanced system components")
    sys.exit(1)


class EnhancedDemo:
    """Demonstration of enhanced complex shape generation"""

    def __init__(self):
        self.setup_complete = False
        self.enhanced_generator = None
        self.websocket_manager = None

    def setup_system(self):
        """Setup the enhanced system components"""
        print("🔧 Setting up Enhanced FreeCAD Automation System...")

        try:
            # Initialize core components
            print("  📡 Initializing LLM client...")
            llm_client = LLMClient(
                api_key=os.getenv("GOOGLE_API_KEY", "demo-key"), provider="google"
            )

            print("  🔍 Initializing state analyzer...")
            state_analyzer = FreeCADStateAnalyzer()

            print("  ⚡ Initializing command executor...")
            command_executor = CommandExecutor()

            print("  🌐 Initializing WebSocket manager...")
            self.websocket_manager = WebSocketManager(port=8765)

            print("  🧠 Initializing enhanced generator...")
            self.enhanced_generator = EnhancedComplexShapeGenerator(
                llm_client=llm_client,
                state_analyzer=state_analyzer,
                command_executor=command_executor,
                websocket_manager=self.websocket_manager,
            )

            self.setup_complete = True
            print("✅ Enhanced system setup complete!")

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False

        return True

    def demonstrate_basic_generation(self):
        """Demonstrate basic enhanced generation"""
        print("\n🎯 Demo 1: Basic Enhanced Generation")
        print("=" * 50)

        test_requirements = [
            "Create a simple tower with a cone on top",
            "Build a complex mechanical assembly with gears",
            "Design a parametric house with windows and doors",
            "Create an intricate architectural structure",
        ]

        for i, requirement in enumerate(test_requirements, 1):
            print(f"\n📋 Test {i}: {requirement}")
            session_id = f"demo_session_{i}"

            # Run generation
            result = self.enhanced_generator.generate_enhanced_complex_shape(
                user_requirements=requirement,
                session_id=session_id,
                generation_mode=GenerationMode.ADAPTIVE,
            )

            # Display results
            self._display_result(result)

    def demonstrate_mode_comparison(self):
        """Demonstrate different generation modes"""
        print("\n🔄 Demo 2: Generation Mode Comparison")
        print("=" * 50)

        requirement = (
            "Create a complex tower with multiple levels and architectural details"
        )
        modes = [
            GenerationMode.ADAPTIVE,
            GenerationMode.INCREMENTAL,
            GenerationMode.PARALLEL,
            GenerationMode.TEMPLATE_BASED,
        ]

        results = {}

        for mode in modes:
            print(f"\n🚀 Testing {mode.value.upper()} mode...")
            session_id = f"mode_test_{mode.value}"

            start_time = time.time()
            result = self.enhanced_generator.generate_enhanced_complex_shape(
                user_requirements=requirement,
                session_id=session_id,
                generation_mode=mode,
            )

            results[mode.value] = {
                "execution_time": time.time() - start_time,
                "quality_score": result.quality_metrics.overall_score,
                "success_rate": (
                    result.successful_steps / result.total_steps
                    if result.total_steps > 0
                    else 0
                ),
                "status": result.status,
            }

            print(f"  ⏱️ Time: {results[mode.value]['execution_time']:.2f}s")
            print(f"  📊 Quality: {results[mode.value]['quality_score']:.2f}")
            print(f"  ✅ Success Rate: {results[mode.value]['success_rate']:.2%}")

        # Compare results
        print(f"\n📈 Mode Comparison Summary:")
        print("-" * 30)
        for mode, data in results.items():
            print(
                f"{mode:15} | Time: {data['execution_time']:6.2f}s | Quality: {data['quality_score']:4.2f} | Success: {data['success_rate']:6.1%}"
            )

    def demonstrate_quality_prediction(self):
        """Demonstrate quality prediction capabilities"""
        print("\n🔮 Demo 3: Quality Prediction")
        print("=" * 50)

        requirements = [
            ("Simple box creation", {"geometric_accuracy": 0.95}),
            (
                "Complex architectural design",
                {"overall_score": 0.85, "aesthetic_quality": 0.8},
            ),
            (
                "Precision mechanical part",
                {"geometric_accuracy": 0.98, "manufacturability": 0.9},
            ),
        ]

        for requirement, quality_targets in requirements:
            print(f"\n🎯 Target: {requirement}")
            print(f"📊 Quality Targets: {quality_targets}")

            session_id = f"quality_demo_{hash(requirement) % 1000}"

            result = self.enhanced_generator.generate_enhanced_complex_shape(
                user_requirements=requirement,
                session_id=session_id,
                quality_targets=quality_targets,
            )

            # Check if targets were met
            achieved_quality = result.quality_metrics
            targets_met = self._check_quality_targets(achieved_quality, quality_targets)

            print(f"✅ Targets Met: {targets_met}")
            print(f"📈 Achieved Quality: {achieved_quality.overall_score:.2f}")

    def demonstrate_pattern_learning(self):
        """Demonstrate pattern learning capabilities"""
        print("\n🧠 Demo 4: Pattern Learning")
        print("=" * 50)

        # Generate several similar shapes to build patterns
        similar_requirements = [
            "Create a tower with cone roof",
            "Build a tower with pointed top",
            "Design a tower structure with cone",
            "Make a cylindrical tower with cone top",
        ]

        print("🔄 Building pattern database...")
        for i, requirement in enumerate(similar_requirements):
            print(f"  📝 Learning from: {requirement}")
            session_id = f"pattern_learning_{i}"

            result = self.enhanced_generator.generate_enhanced_complex_shape(
                user_requirements=requirement, session_id=session_id
            )

        # Test pattern recognition
        print("\n🔍 Testing pattern recognition...")
        test_requirement = "Create a tower with a cone on top"

        # Find similar patterns
        similar_patterns = (
            self.enhanced_generator.pattern_learning.find_similar_patterns(
                test_requirement
            )
        )

        print(f"📊 Found {len(similar_patterns)} similar patterns")
        for pattern in similar_patterns[:3]:
            print(
                f"  • Similarity: {pattern.get('similarity_score', 0):.2f}, Success Rate: {pattern.get('success_rate', 0):.2%}"
            )

    def demonstrate_real_time_monitoring(self):
        """Demonstrate real-time monitoring capabilities"""
        print("\n📊 Demo 5: Real-time Monitoring")
        print("=" * 50)

        if not self.websocket_manager:
            print("❌ WebSocket manager not available")
            return

        print("🌐 Starting WebSocket server for real-time monitoring...")

        async def run_monitoring_demo():
            # Start WebSocket server
            await self.websocket_manager.start_server()

            print("✅ WebSocket server started on ws://localhost:8765")
            print("💡 Connect with: python tools/monitoring/websocket_monitor.py")
            print("⏳ Waiting 5 seconds for connections...")

            await asyncio.sleep(5)

            # Run a complex generation with monitoring
            print("🚀 Running monitored generation...")

            result = self.enhanced_generator.generate_enhanced_complex_shape(
                user_requirements="Create a complex building with multiple floors and details",
                session_id="monitoring_demo",
                generation_mode=GenerationMode.INCREMENTAL,
            )

            print("✅ Monitored generation complete")

            # Keep server running for a bit
            await asyncio.sleep(10)

            # Stop server
            await self.websocket_manager.stop_server()

        try:
            asyncio.run(run_monitoring_demo())
        except Exception as e:
            print(f"❌ Monitoring demo failed: {e}")

    def show_performance_metrics(self):
        """Display comprehensive performance metrics"""
        print("\n📈 Performance Metrics")
        print("=" * 50)

        if not self.enhanced_generator:
            print("❌ Enhanced generator not initialized")
            return

        metrics = self.enhanced_generator.get_performance_metrics()

        print(f"🎯 Total Generations: {metrics.get('total_generations', 0)}")
        print(f"✅ Successful Generations: {metrics.get('successful_generations', 0)}")
        print(f"📊 Average Quality Score: {metrics.get('average_quality_score', 0):.2f}")
        print(
            f"⏱️ Average Execution Time: {metrics.get('average_execution_time', 0):.2f}s"
        )
        print(f"🧠 Pattern Database Size: {metrics.get('pattern_database_size', 0)}")
        print(f"✅ Success Patterns: {metrics.get('success_patterns', 0)}")
        print(f"❌ Failure Patterns: {metrics.get('failure_patterns', 0)}")
        print(f"🔄 Active Sessions: {metrics.get('active_sessions', 0)}")

    def _display_result(self, result):
        """Display generation result"""
        print(f"  📊 Status: {result.status}")
        print(f"  ⏱️ Time: {result.execution_time:.2f}s")
        print(f"  📈 Quality Score: {result.quality_metrics.overall_score:.2f}")
        print(f"  ✅ Success Rate: {result.successful_steps}/{result.total_steps}")

        if result.recommendations:
            print(f"  💡 Recommendations: {len(result.recommendations)}")
            for rec in result.recommendations[:2]:
                print(f"    • {rec}")

    def _check_quality_targets(
        self, achieved: QualityMetrics, targets: Dict[str, float]
    ) -> bool:
        """Check if quality targets were met"""
        for metric, target in targets.items():
            achieved_value = getattr(achieved, metric, 0)
            if achieved_value < target:
                return False
        return True

    def run_interactive_demo(self):
        """Run interactive demonstration"""
        print("🎮 Interactive Enhanced Generation Demo")
        print("=" * 50)

        while True:
            print("\nChoose a demo:")
            print("1. Basic Enhanced Generation")
            print("2. Generation Mode Comparison")
            print("3. Quality Prediction")
            print("4. Pattern Learning")
            print("5. Real-time Monitoring")
            print("6. Performance Metrics")
            print("7. Custom Generation")
            print("0. Exit")

            try:
                choice = input("\nEnter choice (0-7): ").strip()

                if choice == "0":
                    break
                elif choice == "1":
                    self.demonstrate_basic_generation()
                elif choice == "2":
                    self.demonstrate_mode_comparison()
                elif choice == "3":
                    self.demonstrate_quality_prediction()
                elif choice == "4":
                    self.demonstrate_pattern_learning()
                elif choice == "5":
                    self.demonstrate_real_time_monitoring()
                elif choice == "6":
                    self.show_performance_metrics()
                elif choice == "7":
                    self.custom_generation()
                else:
                    print("❌ Invalid choice")

            except KeyboardInterrupt:
                print("\n👋 Demo interrupted by user")
                break
            except Exception as e:
                print(f"❌ Demo error: {e}")

    def custom_generation(self):
        """Allow user to test custom requirements"""
        print("\n🛠️ Custom Generation Test")
        print("-" * 30)

        try:
            requirement = input("Enter your design requirement: ").strip()
            if not requirement:
                print("❌ Empty requirement")
                return

            # Select mode
            print("\nGeneration Modes:")
            modes = list(GenerationMode)
            for i, mode in enumerate(modes):
                print(f"  {i+1}. {mode.value.title()}")

            mode_choice = input("Select mode (1-4, or Enter for adaptive): ").strip()
            if mode_choice and mode_choice.isdigit():
                mode_idx = int(mode_choice) - 1
                if 0 <= mode_idx < len(modes):
                    selected_mode = modes[mode_idx]
                else:
                    selected_mode = GenerationMode.ADAPTIVE
            else:
                selected_mode = GenerationMode.ADAPTIVE

            print(f"\n🚀 Generating with {selected_mode.value} mode...")

            # Run generation
            result = self.enhanced_generator.generate_enhanced_complex_shape(
                user_requirements=requirement,
                session_id="custom_demo",
                generation_mode=selected_mode,
            )

            # Display detailed results
            print(f"\n📊 Generation Results:")
            self._display_result(result)

            if result.learned_patterns:
                print(f"🧠 Learned Patterns: {len(result.learned_patterns)}")

        except Exception as e:
            print(f"❌ Custom generation failed: {e}")


def main():
    """Main demonstration function"""
    print("🚀 Enhanced FreeCAD LLM Automation Demo")
    print("=" * 60)
    print("This demo showcases the advanced capabilities of the enhanced system")
    print("including AI-powered generation, quality prediction, and pattern learning.")
    print()

    demo = EnhancedDemo()

    # Setup system
    if not demo.setup_system():
        print("❌ Failed to setup system. Exiting.")
        return 1

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--auto":
            # Run all demos automatically
            print("\n🤖 Running automated demo sequence...")
            demo.demonstrate_basic_generation()
            demo.demonstrate_mode_comparison()
            demo.demonstrate_quality_prediction()
            demo.demonstrate_pattern_learning()
            demo.show_performance_metrics()
        elif sys.argv[1] == "--monitor":
            # Just run monitoring demo
            demo.demonstrate_real_time_monitoring()
        else:
            print(f"❌ Unknown argument: {sys.argv[1]}")
            return 1
    else:
        # Interactive mode
        demo.run_interactive_demo()

    print("\n✅ Demo completed successfully!")
    print("📚 For more information, see docs/ENHANCED_SYSTEM_IMPROVEMENTS.md")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
