#!/usr/bin/env python3
"""
Real-Time FreeCAD Demo
Demonstrates continuous GUI updates with step-by-step visualization
"""

import sys
import os
import time

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))

from ai_designer.cli import FreeCADCLI

def demo_real_time_freecad():
    """
    Demonstrate the real-time FreeCAD system with persistent GUI
    """
    print("🚀 Real-Time FreeCAD Automation Demo")
    print("=" * 60)
    print("This demo shows:")
    print("✅ Persistent FreeCAD GUI that stays open")
    print("✅ Real-time updates as commands execute")
    print("✅ Step-by-step visualization")
    print("✅ WebSocket-based progress tracking")
    print()
    
    # Initialize CLI with all real-time features enabled
    cli = FreeCADCLI(
        use_headless=True,  # Use headless backend with persistent GUI
        llm_provider="google",
        llm_api_key="AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc",
        enable_websocket=True,
        enable_persistent_gui=True
    )
    
    if not cli.initialize():
        print("❌ Failed to initialize CLI")
        return
    
    print("✅ CLI initialized with persistent GUI")
    print("🖥️  FreeCAD GUI should now be open and ready")
    print()
    
    # Wait for user to confirm GUI is visible
    input("📺 Confirm that FreeCAD GUI is open, then press Enter to continue...")
    print()
    
    # Demo commands with real-time updates
    demo_commands = [
        "create box 20x20x20 --real",
        "create cylinder radius 10 height 15 --real", 
        "create sphere radius 8 --real",
        "create cone radius1 12 radius2 4 height 20 --real",
        "create gear with 24 teeth, 5mm module, 10mm thickness --real"
    ]
    
    print("🎬 Starting real-time demo sequence...")
    print(f"📊 {len(demo_commands)} commands will be executed")
    print("👀 Watch the FreeCAD GUI for live updates!")
    print()
    
    for i, command in enumerate(demo_commands, 1):
        print(f"🔄 [{i}/{len(demo_commands)}] Executing: {command}")
        print("-" * 50)
        
        # Execute command with real-time updates
        start_time = time.time()
        cli.execute_command(command)
        execution_time = time.time() - start_time
        
        print(f"⏱️  Execution time: {execution_time:.2f}s")
        print()
        
        # Pause between commands to observe changes
        if i < len(demo_commands):
            print("⏸️  Pausing for 3 seconds to observe changes...")
            time.sleep(3)
            print()
    
    print("🎉 Demo completed!")
    print("📊 Final status:")
    
    # Show final status
    if cli.enable_websocket and cli.websocket_manager:
        stats = cli.websocket_manager.get_stats()
        print(f"   📡 WebSocket: {stats['active_connections']} active connections")
        print(f"   📨 Messages sent: {stats['messages_sent']}")
    
    if cli.enable_persistent_gui and cli.persistent_gui:
        gui_status = cli.persistent_gui.get_status()
        print(f"   🖥️  GUI Status: {'🟢 Running' if gui_status['running'] else '🔴 Stopped'}")
        if gui_status['running']:
            print(f"   🔌 Communication port: {gui_status['communication_port']}")
    
    print()
    print("💡 The FreeCAD GUI will remain open for you to explore")
    print("🔗 WebSocket server is still running on ws://localhost:8765")
    print("🛑 The GUI will close when this script exits")
    
    # Keep script running
    try:
        input("\nPress Enter to exit and cleanup...")
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    # Cleanup
    print("🧹 Cleaning up...")
    cli.cleanup()
    print("✅ Cleanup completed")

if __name__ == "__main__":
    demo_real_time_freecad()
