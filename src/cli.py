#!/usr/bin/env python3
import sys
import os
import argparse
from freecad.api_client import FreeCADAPIClient
from freecad.command_executor import CommandExecutor
from redis.client import RedisClient
from redis.state_cache import StateCache

class FreeCADCLI:
    def __init__(self, use_headless=True):
        self.api_client = FreeCADAPIClient(use_headless=use_headless)
        self.command_executor = None
        self.state_cache = None
        
        # Try to initialize Redis for state management
        try:
            redis_client = RedisClient()
            if redis_client.connect():
                self.state_cache = StateCache(redis_client)
                print("✓ Redis connection established for state caching")
        except Exception as e:
            print(f"Warning: Redis not available: {e}")

    def initialize(self):
        """Initialize FreeCAD connection and command executor"""
        print("Initializing FreeCAD CLI...")
        
        if self.api_client.connect():
            print("✓ FreeCAD connection established")
            self.command_executor = CommandExecutor(self.api_client, self.state_cache)
            return True
        else:
            print("✗ Failed to connect to FreeCAD")
            return False

    def interactive_mode(self):
        """Start interactive command mode"""
        if not self.initialize():
            return
        
        print("\nFreeCAD Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("FreeCAD> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    self.show_help()
                
                elif user_input.lower() == 'state':
                    self.show_state()
                
                elif user_input.lower() == 'history':
                    self.show_history()
                
                elif user_input.startswith('script '):
                    script_path = user_input[7:].strip()
                    self.execute_script(script_path)
                
                else:
                    self.execute_command(user_input)
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break

    def execute_command(self, command):
        """Execute a single command"""
        try:
            if command.startswith('!'):
                # Direct FreeCAD Python command
                freecad_command = command[1:]
                result = self.command_executor.execute(freecad_command)
            else:
                # Natural language command
                result = self.command_executor.execute_natural_language(command)
            
            if result["status"] == "success":
                print(f"✓ {result['message']}")
            else:
                print(f"✗ Error: {result['message']}")
                
        except Exception as e:
            print(f"✗ Exception: {e}")

    def execute_script(self, script_path):
        """Execute a FreeCAD script file"""
        if not os.path.exists(script_path):
            print(f"✗ Script file not found: {script_path}")
            return
        
        try:
            result = self.api_client.execute_script_file(script_path)
            if result["status"] == "success":
                print(f"✓ Script executed: {script_path}")
                print(result["message"])
            else:
                print(f"✗ Script failed: {result['message']}")
        except Exception as e:
            print(f"✗ Exception executing script: {e}")

    def show_state(self):
        """Show current FreeCAD document state"""
        state = self.command_executor.get_state()
        print("\nCurrent FreeCAD State:")
        print(f"Document: {state.get('active_document', 'None')}")
        print(f"Objects: {state.get('object_count', 0)}")
        
        for obj in state.get('objects', []):
            print(f"  - {obj['name']} ({obj['type']})")

    def show_history(self):
        """Show command history"""
        history = self.command_executor.get_command_history()
        print(f"\nCommand History ({len(history)} commands):")
        for i, cmd in enumerate(history[-10:], 1):  # Show last 10 commands
            print(f"{i:2d}. {cmd[:50]}{'...' if len(cmd) > 50 else ''}")

    def show_help(self):
        """Show help information"""
        help_text = """
Available Commands:
  Natural Language:
    - create box 10x20x30        Create a box with dimensions
    - create cylinder radius 5   Create a cylinder
    - create sphere radius 10    Create a sphere
    - save document as myfile    Save document
    - export stl as output       Export to STL
  
  Direct FreeCAD Commands (prefix with !):
    - !box = doc.addObject("Part::Box", "MyBox")
    - !box.Length = 10
    
  CLI Commands:
    - state                      Show document state
    - history                    Show command history
    - script <path>             Execute script file
    - help                      Show this help
    - quit                      Exit
"""
        print(help_text)

def main():
    parser = argparse.ArgumentParser(description="FreeCAD Command Line Interface")
    parser.add_argument('--gui', action='store_true', help='Use FreeCAD GUI instead of headless mode')
    parser.add_argument('--script', help='Execute a specific script file')
    parser.add_argument('--command', help='Execute a single command and exit')
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = FreeCADCLI(use_headless=not args.gui)
    
    if args.script:
        # Execute script mode
        if cli.initialize():
            cli.execute_script(args.script)
    elif args.command:
        # Single command mode
        if cli.initialize():
            cli.execute_command(args.command)
    else:
        # Interactive mode
        cli.interactive_mode()

if __name__ == "__main__":
    main()