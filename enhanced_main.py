"""
Enhanced Main Entry Point
Demonstrates the complete state-aware, LLM-integrated FreeCAD automation system
"""

import asyncio
import json
import time
from typing import Dict, Any
from src.core.orchestrator import SystemOrchestrator

async def run_enhanced_system():
    """
    Run the enhanced system with full state management and real-time features
    """
    
    # System configuration
    config = {
        'redis_host': 'localhost',
        'redis_port': 6379,
        'llm_provider': 'google',  # or 'openai'
        'llm_api_key': None,  # Set your API key
        'headless': True,
        'max_concurrent': 3,
        'enable_realtime': True,
        'websocket_host': 'localhost',
        'websocket_port': 8765,
        'state_checkpoint_interval': 30  # seconds
    }
    
    print("🚀 Starting Enhanced FreeCAD LLM Automation System")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = SystemOrchestrator(config)
    
    try:
        # Start the system
        print("📊 Starting system components...")
        orchestrator.start_system()
        
        print("\n✅ System started successfully!")
        print("🌐 WebSocket server running on ws://localhost:8765")
        print("📡 Real-time updates enabled")
        print("🧠 State-LLM integration active")
        print("=" * 60)
        
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

if __name__ == "__main__":
    main()
