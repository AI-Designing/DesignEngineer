#!/usr/bin/env python3
"""
AI Designer Package Main Entry Point
This file allows running the package with: python -m ai_designer
"""

import sys
import os
import argparse
from typing import Optional

# Ensure the package is importable
if __name__ == "__main__":
    # Add the parent directory to the path to allow imports
    package_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(package_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from ai_designer.cli import FreeCADCLI

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AI Designer - FreeCAD LLM Automation System")
    
    # LLM configuration
    parser.add_argument('--llm-provider', choices=['openai', 'google'], default='openai',
                       help='LLM provider to use (default: openai)')
    parser.add_argument('--llm-api-key', type=str,
                       help='API key for the LLM provider')
    
    # Mode selection
    parser.add_argument('--interactive', action='store_true',
                       help='Start in interactive mode')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run in headless mode (default: True)')
    parser.add_argument('--auto-gui', action='store_true', default=True,
                       help='Automatically open objects in FreeCAD GUI after creation (default: True)')
    parser.add_argument('--no-auto-gui', action='store_true',
                       help='Disable automatic GUI opening')
    
    # Enhanced system options
    parser.add_argument('--enhanced', action='store_true',
                       help='Use enhanced system with state management and real-time features')
    parser.add_argument('--redis-host', default='localhost',
                       help='Redis host for enhanced mode (default: localhost)')
    parser.add_argument('--redis-port', type=int, default=6379,
                       help='Redis port for enhanced mode (default: 6379)')
    parser.add_argument('--websocket-port', type=int, default=8765,
                       help='WebSocket port for enhanced mode (default: 8765)')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent operations for enhanced mode (default: 3)')
    parser.add_argument('--disable-realtime', action='store_true',
                       help='Disable real-time WebSocket features in enhanced mode')
    
    # Analysis mode
    parser.add_argument('--analyze', type=str, metavar='FILE',
                       help='Analyze a FreeCAD file')
    
    # Command execution
    parser.add_argument('command', nargs='*',
                       help='Command to execute')
    
    return parser.parse_args()

def main():
    """
    Main entry point for AI Designer
    """
    print("AI Designer - FreeCAD LLM Automation System")
    print("=" * 50)
    
    args = parse_arguments()
    
    if args.enhanced:
        # Use enhanced system with async orchestrator
        import asyncio
        from ai_designer.core.orchestrator import SystemOrchestrator
        
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
            'state_checkpoint_interval': 30
        }
        
        print("🚀 Starting Enhanced AI Designer System")
        print(f"🧠 LLM Provider: {config['llm_provider']}")
        print(f"🌐 Real-time features: {'Enabled' if config['enable_realtime'] else 'Disabled'}")
        
        async def run_enhanced():
            orchestrator = SystemOrchestrator(config)
            
            try:
                orchestrator.start_system()
                print("✅ Enhanced system started successfully!")
                
                if args.command:
                    # Execute single command
                    command = " ".join(args.command)
                    session_id = "cli_session"
                    print(f"📝 Executing: {command}")
                    result = orchestrator.process_user_input_enhanced(command, session_id)
                    
                    status = result.get('status', 'unknown')
                    if status == 'success':
                        print("✅ Command executed successfully")
                    else:
                        print(f"❌ Command failed: {result.get('error', 'Unknown error')}")
                else:
                    # Interactive mode
                    print("💬 Starting interactive mode...")
                    print("Type 'exit' to quit")
                    
                    session_id = "interactive_session"
                    while True:
                        try:
                            command = input("AI Designer> ").strip()
                            if command.lower() in ['exit', 'quit']:
                                break
                            if not command:
                                continue
                            
                            result = orchestrator.process_user_input_enhanced(command, session_id)
                            status = result.get('status', 'unknown')
                            
                            if status == 'success':
                                print("✅ Command executed successfully")
                            else:
                                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                        
                        except (KeyboardInterrupt, EOFError):
                            break
            
            finally:
                orchestrator.stop_system()
        
        asyncio.run(run_enhanced())
    
    else:
        # Use standard CLI system
        auto_gui = args.auto_gui and not args.no_auto_gui
        
        cli = FreeCADCLI(
            use_headless=args.headless,
            llm_provider=args.llm_provider,
            llm_api_key=args.llm_api_key,
            auto_open_gui=auto_gui
        )
        
        if args.analyze:
            print(f"Analyzing file: {args.analyze}")
            if cli.initialize():
                cli.analyze_state(args.analyze)
        elif args.command:
            # Execute command
            command = " ".join(args.command)
            print(f"Executing command: {command}")
            if cli.initialize():
                cli.execute_command(command)
        else:
            # Start interactive mode
            print("Starting interactive mode...")
            print("Type 'help' for available commands")
            print("💾 Auto-save is ENABLED - files will be saved automatically")
            if auto_gui:
                print("🖥️  Auto-GUI is ENABLED - objects will open in FreeCAD GUI")
            else:
                print("🖥️  Auto-GUI is DISABLED - use 'gui' command to view objects")
            cli.interactive_mode()

if __name__ == "__main__":
    main()
