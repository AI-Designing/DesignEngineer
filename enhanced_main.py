"""
Enhanced Main Entry Point
Demonstrates the complete state-aware, LLM-integrated FreeCAD automation system
"""

import asyncio
import json
import time
import sys
import argparse
from typing import Dict, Any
from src.core.orchestrator import SystemOrchestrator

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Enhanced FreeCAD LLM Automation System")
    
    # LLM configuration
    parser.add_argument('--llm-provider', choices=['openai', 'google'], default='google',
                       help='LLM provider to use (default: google)')
    parser.add_argument('--llm-api-key', type=str, required=True,
                       help='API key for the LLM provider')
    
    # System configuration
    parser.add_argument('--redis-host', default='localhost',
                       help='Redis host (default: localhost)')
    parser.add_argument('--redis-port', type=int, default=6379,
                       help='Redis port (default: 6379)')
    parser.add_argument('--websocket-port', type=int, default=8765,
                       help='WebSocket port (default: 8765)')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent operations (default: 3)')
    
    # Mode options
    parser.add_argument('--disable-realtime', action='store_true',
                       help='Disable real-time WebSocket features')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run in headless mode (default: True)')
    parser.add_argument('--demo-mode', action='store_true', default=True,
                       help='Run predefined demo commands (default: True)')
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive mode instead of demo')
    
    # Test options
    parser.add_argument('--test-complex-shapes', action='store_true',
                       help='Test complex shape generation')
    parser.add_argument('--single-command', type=str,
                       help='Execute a single command and exit')
    
    return parser.parse_args()

async def run_enhanced_system():
    """
    Run the enhanced system with full state management and real-time features
    """
    
    # Parse command line arguments
    args = parse_arguments()
    
    # System configuration
    config = {
        'redis_host': args.redis_host,
        'redis_port': args.redis_port,
        'llm_provider': args.llm_provider,
        'llm_api_key': args.llm_api_key,
        'headless': args.headless,
        'max_concurrent': args.max_concurrent,
        'enable_realtime': not args.disable_realtime,
        'websocket_host': 'localhost',
        'websocket_port': args.websocket_port,
        'state_checkpoint_interval': 30  # seconds
    }
    
    print("🚀 Starting Enhanced FreeCAD LLM Automation System")
    print("=" * 60)
    print(f"🧠 LLM Provider: {config['llm_provider']}")
    print(f"🌐 Real-time features: {'Enabled' if config['enable_realtime'] else 'Disabled'}")
    print(f"📡 WebSocket port: {config['websocket_port']}")
    print(f"⚡ Max concurrent: {config['max_concurrent']}")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = SystemOrchestrator(config)
    
    try:
        # Start the system
        print("📊 Starting system components...")
        orchestrator.start_system()
        
        print("\n✅ System started successfully!")
        if config['enable_realtime']:
            print(f"🌐 WebSocket server running on ws://localhost:{config['websocket_port']}")
            print("📡 Real-time updates enabled")
        print("🧠 State-LLM integration active")
        print("=" * 60)
        
        # Handle different modes
        if args.single_command:
            await run_single_command(orchestrator, args.single_command)
        elif args.test_complex_shapes:
            await run_complex_shape_tests(orchestrator)
        elif args.interactive:
            await run_interactive_mode(orchestrator)
        else:
            await run_demo_mode(orchestrator)
        
        # Demo session
        session_id = "demo_session"
        print(f"\n🎯 Starting demo session: {session_id}")
        
        # Test commands that demonstrate state management and LLM decision-making
        test_commands = [
            "Create a cube with dimensions 10x10x10",
            "Add a cylinder next to the cube",
            "Change the cube color to red", 
            "Analyze the current design",
            "Export the design as STL file",
            "What objects are currently in the document?"
        ]
        
        print(f"\n🧪 Running {len(test_commands)} test commands...")
        print("-" * 40)
        
        results = []
        
        for i, command in enumerate(test_commands, 1):
            print(f"\n[{i}/{len(test_commands)}] 📝 Processing: '{command}'")
            
            # Use enhanced processing with state-LLM integration
            start_time = time.time()
            result = orchestrator.process_user_input_enhanced(command, session_id)
            processing_time = time.time() - start_time
            
            # Display result
            status = result.get('status', 'unknown')
            status_icon = '✅' if status == 'success' else ('❌' if status == 'error' else '⚠️')
            
            print(f"   {status_icon} Status: {status}")
            print(f"   ⏱️ Processing time: {processing_time:.2f}s")
            
            if status == 'success':
                intent = result.get('intent', {})
                print(f"   🧠 Intent: {intent.get('intent_type', 'unknown')}")
                
                decision = result.get('decision', {})
                print(f"   🎯 Confidence: {decision.get('confidence', 0):.2f}")
                
                execution = result.get('execution', {})
                print(f"   ⚡ Execution: {execution.get('status', 'unknown')}")
            
            elif status == 'error':
                print(f"   💥 Error: {result.get('error', 'Unknown error')}")
            
            results.append({
                'command': command,
                'result': result,
                'processing_time': processing_time
            })
            
            # Show current state after each command
            state_info = orchestrator.get_session_state(session_id)
            cached_state = state_info.get('cached_state', {})
            if cached_state and 'object_count' in cached_state:
                print(f"   📊 Current objects: {cached_state['object_count']}")
            
            # Small delay between commands
            await asyncio.sleep(1)
        
        print("\n" + "=" * 60)
        print("📈 DEMO RESULTS SUMMARY")
        print("=" * 60)
        
        # Calculate metrics
        successful_commands = sum(1 for r in results if r['result'].get('status') == 'success')
        total_time = sum(r['processing_time'] for r in results)
        avg_time = total_time / len(results) if results else 0
        
        print(f"✅ Successful commands: {successful_commands}/{len(results)}")
        print(f"📊 Success rate: {(successful_commands/len(results)*100):.1f}%")
        print(f"⏱️ Total processing time: {total_time:.2f}s")
        print(f"📈 Average time per command: {avg_time:.2f}s")
        
        # Show performance metrics
        print(f"\n📊 System Performance Metrics:")
        metrics = orchestrator.get_performance_metrics()
        
        if 'state_llm' in metrics:
            llm_metrics = metrics['state_llm']
            print(f"   🧠 LLM avg decision time: {llm_metrics.get('llm_decision_time', {}).get('avg', 0):.2f}s")
            print(f"   📊 State retrieval avg time: {llm_metrics.get('state_retrieval_time', {}).get('avg', 0):.2f}s")
        
        if 'websocket' in metrics:
            ws_metrics = metrics['websocket']
            print(f"   🌐 WebSocket connections: {ws_metrics.get('active_connections', 0)}")
            print(f"   📡 Messages sent: {ws_metrics.get('messages_sent', 0)}")
        
        if 'queue' in metrics:
            queue_metrics = metrics['queue']
            print(f"   📤 Commands processed: {queue_metrics.get('pending_count', 0)}")
            print(f"   ⚡ Active workers: {queue_metrics.get('worker_count', 0)}")
        
        # Show final state
        print(f"\n📋 Final Session State:")
        final_state = orchestrator.get_session_state(session_id)
        cached_state = final_state.get('cached_state', {})
        
        if cached_state:
            print(f"   📄 Document: {cached_state.get('document_name', 'Unnamed')}")
            print(f"   🔢 Total objects: {cached_state.get('object_count', 0)}")
            
            objects = cached_state.get('objects', [])
            if objects:
                print(f"   🎯 Object types:")
                obj_types = {}
                for obj in objects:
                    obj_type = obj.get('type', 'Unknown')
                    obj_types[obj_type] = obj_types.get(obj_type, 0) + 1
                
                for obj_type, count in obj_types.items():
                    print(f"      • {obj_type}: {count}")
        
        print("\n🎉 Demo completed successfully!")
        print("💡 The system demonstrated:")
        print("   • Intelligent intent processing")
        print("   • State-aware LLM decision making")
        print("   • Real-time progress tracking")
        print("   • Automatic state checkpointing")
        print("   • Comprehensive error handling")
        print("   • Performance monitoring")
        
        # Keep system running for WebSocket connections
        print(f"\n🌐 System will continue running for WebSocket connections...")
        print("💡 Connect to ws://localhost:8765 to see real-time updates")
        print("🛑 Press Ctrl+C to stop the system")
        
        # Wait for manual interruption
        try:
            while True:
                await asyncio.sleep(10)
                
                # Show periodic status
                print(f"💓 System heartbeat - Active sessions: {len(orchestrator.active_sessions)}")
        
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested...")
    
    except Exception as e:
        print(f"\n❌ System error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("🧹 Stopping system components...")
        orchestrator.stop_system()
        
        if orchestrator.websocket_manager:
            await orchestrator.websocket_manager.stop_server()
        
        print("✅ System stopped cleanly")

async def run_single_command(orchestrator, command):
    """Run a single command and exit"""
    session_id = "single_command_session"
    print(f"\n📝 Executing single command: '{command}'")
    
    start_time = time.time()
    result = orchestrator.process_user_input_enhanced(command, session_id)
    processing_time = time.time() - start_time
    
    # Display result
    status = result.get('status', 'unknown')
    status_icon = '✅' if status == 'success' else ('❌' if status == 'error' else '⚠️')
    
    print(f"\n{status_icon} Command Result:")
    print(f"   Status: {status}")
    print(f"   Processing time: {processing_time:.2f}s")
    
    if status == 'success':
        intent = result.get('intent', {})
        print(f"   Intent: {intent.get('intent_type', 'unknown')}")
        
        decision = result.get('decision', {})
        print(f"   Confidence: {decision.get('confidence', 0):.2f}")
        
        execution = result.get('execution', {})
        print(f"   Execution: {execution.get('status', 'unknown')}")
    
    elif status == 'error':
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    # Show final state
    state_info = orchestrator.get_session_state(session_id)
    cached_state = state_info.get('cached_state', {})
    if cached_state and 'object_count' in cached_state:
        print(f"   Objects created: {cached_state['object_count']}")

async def run_complex_shape_tests(orchestrator):
    """Run complex shape generation tests"""
    session_id = "complex_shape_test"
    print(f"\n🏗️ Running Complex Shape Tests")
    print("-" * 40)
    
    complex_commands = [
        "create a cone and cylinder together",
        "build a tower with cone roof",
        "make a rocket with fins",
        "create a complex building structure"
    ]
    
    for i, command in enumerate(complex_commands, 1):
        print(f"\n[{i}/{len(complex_commands)}] Testing: '{command}'")
        
        start_time = time.time()
        result = orchestrator.process_user_input_enhanced(command, session_id)
        processing_time = time.time() - start_time
        
        status = result.get('status', 'unknown')
        status_icon = '✅' if status == 'success' else ('❌' if status == 'error' else '⚠️')
        
        print(f"   {status_icon} Status: {status} ({processing_time:.2f}s)")
        
        if status == 'success':
            execution = result.get('execution', {})
            print(f"   ⚡ Execution: {execution.get('status', 'unknown')}")
        
        # Show state after each test
        state_info = orchestrator.get_session_state(session_id)
        cached_state = state_info.get('cached_state', {})
        if cached_state and 'object_count' in cached_state:
            print(f"   📊 Total objects: {cached_state['object_count']}")
        
        await asyncio.sleep(1)
    
    print("\n✅ Complex shape tests completed!")

async def run_interactive_mode(orchestrator):
    """Run interactive mode"""
    session_id = "interactive_session"
    print(f"\n💬 Interactive Mode - Session: {session_id}")
    print("Type 'exit' or 'quit' to stop")
    print("-" * 40)
    
    while True:
        try:
            command = input("\nEnhanced> ").strip()
            
            if not command:
                continue
            
            if command.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            if command.lower() == 'help':
                print("""
Available commands:
  - Any natural language command (e.g., 'create a cube')
  - Complex shapes (e.g., 'create a cone and cylinder together')
  - State commands: 'state', 'analyze'
  - 'help' - Show this help
  - 'exit' - Exit interactive mode
                """)
                continue
            
            if command.lower() == 'state':
                state_info = orchestrator.get_session_state(session_id)
                cached_state = state_info.get('cached_state', {})
                if cached_state:
                    print(f"📊 Current state: {cached_state.get('object_count', 0)} objects")
                else:
                    print("📊 No state information available")
                continue
            
            # Process command
            start_time = time.time()
            result = orchestrator.process_user_input_enhanced(command, session_id)
            processing_time = time.time() - start_time
            
            status = result.get('status', 'unknown')
            status_icon = '✅' if status == 'success' else ('❌' if status == 'error' else '⚠️')
            
            print(f"{status_icon} {status} ({processing_time:.2f}s)")
            
            if status == 'error':
                print(f"Error: {result.get('error', 'Unknown error')}")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break

async def run_demo_mode(orchestrator):
    """Run the original demo mode"""
    session_id = "demo_mode_session"
    print(f"\n🎬 Running Demo Mode - Session: {session_id}")
    
    demo_commands = [
        "Create a parametric model of a chair",
        "Add a table with adjustable height",
        "Design a simple house layout",
        "Generate a 3D model of a car",
        "Create a scene with multiple objects",
        "Export the entire scene as OBJ file"
    ]
    
    for i, command in enumerate(demo_commands, 1):
        print(f"\n[{i}/{len(demo_commands)}] ▶️ Executing: '{command}'")
        
        start_time = time.time()
        result = orchestrator.process_user_input_enhanced(command, session_id)
        processing_time = time.time() - start_time
        
        status = result.get('status', 'unknown')
        status_icon = '✅' if status == 'success' else ('❌' if status == 'error' else '⚠️')
        
        print(f"   {status_icon} Status: {status} ({processing_time:.2f}s)")
        
        if status == 'success':
            intent = result.get('intent', {})
            print(f"   🧠 Intent: {intent.get('intent_type', 'unknown')}")
            
            decision = result.get('decision', {})
            print(f"   🎯 Confidence: {decision.get('confidence', 0):.2f}")
            
            execution = result.get('execution', {})
            print(f"   ⚡ Execution: {execution.get('status', 'unknown')}")
        
        elif status == 'error':
            print(f"   💥 Error: {result.get('error', 'Unknown error')}")
        
        # Show state after each command
        state_info = orchestrator.get_session_state(session_id)
        cached_state = state_info.get('cached_state', {})
        if cached_state and 'object_count' in cached_state:
            print(f"   📊 Current objects: {cached_state['object_count']}")
        
        # Small delay between commands
        await asyncio.sleep(1)
    
    print("\n✅ Demo mode completed!")
    print("💡 The demo showcased the system's capabilities to:")
    print("   • Interpret complex design commands")
    print("   • Manage multiple objects and parameters")
    print("   • Provide real-time feedback and updates")
    print("   • Handle errors and exceptions gracefully")
    print("   • Integrate with LLM for intelligent decision making")
    print("   • Export designs in standard 3D formats")
    
    # Final state summary
    final_state = orchestrator.get_session_state(session_id)
    cached_state = final_state.get('cached_state', {})
    
    if cached_state:
        print(f"\n📋 Final Demo Session State:")
        print(f"   📄 Document: {cached_state.get('document_name', 'Unnamed')}")
        print(f"   🔢 Total objects: {cached_state.get('object_count', 0)}")
        
        objects = cached_state.get('objects', [])
        if objects:
            print(f"   🎯 Object types:")
            obj_types = {}
            for obj in objects:
                obj_type = obj.get('type', 'Unknown')
                obj_types[obj_type] = obj_types.get(obj_type, 0) + 1
            
            for obj_type, count in obj_types.items():
                print(f"      • {obj_type}: {count}")
    
    print("🎉 Demo session ended. System ready for next steps.")
    
    # Keep system running for WebSocket connections
    print(f"\n🌐 System will continue running for WebSocket connections...")
    print("💡 Connect to ws://localhost:8765 to see real-time updates")
    print("🛑 Press Ctrl+C to stop the system")
    
    # Wait for manual interruption
    try:
        while True:
            await asyncio.sleep(10)
            
            # Show periodic status
            print(f"💓 System heartbeat - Active sessions: {len(orchestrator.active_sessions)}")
    
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")

def main():
    """Main entry point"""
    print("🔧 FreeCAD LLM Automation - Enhanced System")
    print("🎯 Intelligent state management with real-time updates")
    print()
    
    try:
        # Run the async system
        asyncio.run(run_enhanced_system())
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    except SystemExit:
        # Handle argparse exits gracefully
        pass

if __name__ == "__main__":
    main()
