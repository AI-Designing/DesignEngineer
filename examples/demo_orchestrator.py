"""
Demo: Complete multi-agent orchestration workflow.

This example demonstrates how to use the OrchestratorAgent to coordinate
the complete multi-agent design pipeline:
1. Planner: Decomposes prompt into task graph
2. Generator: Creates FreeCAD scripts
3. Executor: Runs scripts (optional)
4. Validator: Assesses quality
5. Refiner: Iterates until valid or max iterations

Usage:
    python examples/demo_orchestrator.py

Requirements:
    - Valid API keys in .env (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY)
    - FreeCAD installed (optional, for execution)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_designer.agents import OrchestratorAgent
from ai_designer.agents.executor import FreeCADExecutor
from ai_designer.core.llm_provider import UnifiedLLMProvider
from ai_designer.schemas.design_state import DesignRequest


async def demo_basic_workflow():
    """Demonstrate basic orchestration without FreeCAD execution."""
    print("=" * 70)
    print("DEMO 1: Basic Workflow (No Execution)")
    print("=" * 70)
    print()

    # Initialize LLM provider
    llm_provider = UnifiedLLMProvider()

    # Initialize orchestrator
    orchestrator = OrchestratorAgent(
        llm_provider=llm_provider, max_iterations=3, enable_refinement=True
    )

    # Create design request
    request = DesignRequest(user_prompt="Create a simple 10x10x10mm cube")

    print(f"📝 Prompt: {request.user_prompt}")
    print(f"🔄 Max iterations: {orchestrator.max_iterations}")
    print(
        f"♻️  Refinement: {'enabled' if orchestrator.enable_refinement else 'disabled'}"
    )
    print()

    # Execute workflow (without execution callback)
    print("🚀 Starting workflow...\n")
    result = await orchestrator.execute(request=request)

    # Display results
    print(f"\n{'='*70}")
    print("📊 Workflow Results")
    print("=" * 70)
    print(f"Status: {result.status.value}")
    print(f"Valid: {result.is_valid}")
    print(f"Iterations: {result.current_iteration}")
    print(f"Total agent calls: {len(result.iterations)}")

    if result.freecad_script:
        print(f"\n📜 Generated script: {len(result.freecad_script)} characters")
        print("\nFirst 200 characters:")
        print("-" * 70)
        print(result.freecad_script[:200])
        print("...")

    if result.validation_results:
        val = result.validation_results
        print(f"\n✅ Validation scores:")
        print(f"  Overall: {val.get('overall_score', 0):.2f}")
        print(f"  Geometric: {val.get('geometric_score', 0):.2f}")
        print(f"  Semantic: {val.get('semantic_score', 0):.2f}")

    if result.error_message:
        print(f"\n❌ Error: {result.error_message}")

    # Show iteration breakdown
    print(f"\n📋 Iteration breakdown:")
    for i, iteration in enumerate(result.iterations, 1):
        print(f"  {i}. {iteration.agent.value}: ", end="")
        if iteration.errors:
            print(f"❌ Failed - {iteration.errors[0][:50]}...")
        else:
            print("✅ Success")

    return result


async def demo_with_execution():
    """Demonstrate full workflow with FreeCAD execution."""
    print("\n\n")
    print("=" * 70)
    print("DEMO 2: Full Workflow (With FreeCAD Execution)")
    print("=" * 70)
    print()

    # Initialize components
    llm_provider = UnifiedLLMProvider()

    orchestrator = OrchestratorAgent(
        llm_provider=llm_provider, max_iterations=2, enable_refinement=True
    )

    # Initialize FreeCAD executor
    executor = FreeCADExecutor(
        timeout=60, save_outputs=True, outputs_dir="outputs/orchestrator_demo"
    )

    # Create design request
    request = DesignRequest(
        user_prompt="Create a mechanical bracket with two mounting holes"
    )

    print(f"📝 Prompt: {request.user_prompt}")
    print(f"🔄 Max iterations: {orchestrator.max_iterations}")
    print(f"⚙️  Executor timeout: {executor.timeout}s")
    print(f"💾 Save outputs: {executor.save_outputs}")
    print()

    # Execute workflow with execution callback
    print("🚀 Starting workflow with execution...\n")
    result = await orchestrator.execute(
        request=request, execution_callback=executor.execute
    )

    # Display results
    print(f"\n{'='*70}")
    print("📊 Workflow Results")
    print("=" * 70)
    print(f"Status: {result.status.value}")
    print(f"Valid: {result.is_valid}")
    print(f"Iterations: {result.current_iteration}")

    if result.artifacts and "execution_result" in result.artifacts:
        exec_result = result.artifacts["execution_result"]
        print(f"\n🔧 Execution results:")
        print(f"  Success: {exec_result.get('success', False)}")
        print(f"  Objects created: {len(exec_result.get('created_objects', []))}")
        if exec_result.get("created_objects"):
            print(f"  Objects: {', '.join(exec_result['created_objects'][:5])}")
        if exec_result.get("document_path"):
            print(f"  Document: {exec_result['document_path']}")
        if exec_result.get("execution_time"):
            print(f"  Execution time: {exec_result['execution_time']:.2f}s")

    if result.validation_results:
        val = result.validation_results
        print(f"\n✅ Validation:")
        print(f"  Overall score: {val.get('overall_score', 0):.2f}")

    if result.error_message:
        print(f"\n❌ Error: {result.error_message}")

    return result


async def demo_complex_design():
    """Demonstrate workflow with more complex design."""
    print("\n\n")
    print("=" * 70)
    print("DEMO 3: Complex Design with Refinement")
    print("=" * 70)
    print()

    llm_provider = UnifiedLLMProvider()

    orchestrator = OrchestratorAgent(
        llm_provider=llm_provider, max_iterations=5, enable_refinement=True
    )

    request = DesignRequest(
        user_prompt="""Create a gear wheel with the following specifications:
        - Outer diameter: 50mm
        - Inner diameter (bore): 10mm
        - Number of teeth: 20
        - Thickness: 5mm
        """
    )

    print(f"📝 Prompt: {request.user_prompt[:100]}...")
    print(f"🔄 Max iterations: {orchestrator.max_iterations}")
    print()

    print("🚀 Starting workflow...\n")
    result = await orchestrator.execute(request=request)

    # Display results
    print(f"\n{'='*70}")
    print("📊 Workflow Results")
    print("=" * 70)
    print(f"Status: {result.status.value}")
    print(f"Iterations used: {result.current_iteration}/{orchestrator.max_iterations}")
    print(f"Total agent calls: {len(result.iterations)}")

    if result.validation_results:
        val = result.validation_results
        print(f"\nValidation: {val.get('overall_score', 0):.2f}")
        if val.get("refinement_suggestions"):
            print(f"Refinement suggestions: {len(val['refinement_suggestions'])}")

    # Show how refinement worked
    print(f"\n🔄 Refinement cycles:")
    for i in range(1, result.current_iteration + 1):
        print(f"\n  Iteration {i}:")
        # Find validation result for this iteration
        iteration_agents = [
            it.agent.value for it in result.iterations if it.iteration_number <= i * 3
        ]
        print(f"    Agents: {' → '.join(iteration_agents[-3:])}")

    return result


async def main():
    """Run all demos."""
    try:
        # Demo 1: Basic workflow without execution
        result1 = await demo_basic_workflow()

        # Demo 2: Full workflow with execution (optional - needs FreeCAD)
        try:
            result2 = await demo_with_execution()
        except Exception as e:
            print(f"\n⚠️  Demo 2 skipped (FreeCAD execution): {e}")
            print("   This is expected if FreeCAD is not installed.")

        # Demo 3: Complex design with refinement
        result3 = await demo_complex_design()

        print("\n\n" + "=" * 70)
        print("✅ All demos completed!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
