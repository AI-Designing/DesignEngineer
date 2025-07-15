#!/usr/bin/env python3
import sys
import os
import argparse
from freecad.api_client import FreeCADAPIClient
from freecad.command_executor import CommandExecutor
from freecad.state_manager import FreeCADStateAnalyzer
from redis_utils.client import RedisClient
from redis_utils.state_cache import StateCache

class FreeCADCLI:
    def __init__(self, use_headless=True, llm_provider="openai", llm_api_key=None):
        self.api_client = FreeCADAPIClient(use_headless=use_headless)
        self.command_executor = None
        self.state_cache = None
        self.state_analyzer = None
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
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
            self.command_executor = CommandExecutor(self.api_client, self.state_cache, llm_provider=self.llm_provider, llm_api_key=self.llm_api_key)
            self.state_analyzer = FreeCADStateAnalyzer(self.api_client)
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
                
                elif user_input.lower() == 'analyze':
                    self.analyze_state()
                
                elif user_input.startswith('analyze '):
                    doc_path = user_input[8:].strip()
                    self.analyze_state(doc_path)
                
                elif user_input.lower() == 'history':
                    self.show_history()
                
                elif user_input.startswith('script '):
                    script_path = user_input[7:].strip()
                    self.execute_script(script_path)
                
                elif user_input.lower() in ['fileinfo', 'files', 'location']:
                    self.show_file_info()
                
                elif user_input.lower() in ['saveinfo', 'saves', 'autosave']:
                    self.show_save_info()
                
                elif user_input.startswith('save '):
                    # Manual save command
                    filename = user_input[5:].strip()
                    if filename:
                        self.command_executor.manual_save(filename)
                    else:
                        self.command_executor.manual_save()
                
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

    def analyze_state(self, doc_path=None):
        """Perform comprehensive state analysis"""
        if not self.state_analyzer:
            print("✗ State analyzer not available")
            return
        
        print("🔄 Analyzing FreeCAD document state...")
        
        try:
            analysis = self.state_analyzer.analyze_document_state(doc_path)
            self.state_analyzer.print_analysis_results(analysis)
            
            # Cache the analysis results if Redis is available
            if self.state_cache and "analysis" in analysis:
                self.state_cache.cache_state(analysis, "last_analysis")
                print("\n💾 Analysis results cached")
                
        except Exception as e:
            print(f"✗ Analysis failed: {e}")

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
    - state                      Show basic document state
    - analyze                    Perform comprehensive state analysis
    - analyze <file.FCStd>       Analyze specific FreeCAD file
    - history                    Show command history
    - script <path>             Execute script file
    - fileinfo                  Show file locations and paths
    - saveinfo                  Show auto-save information and file locations
    - save [filename]           Manually save document (auto-save also enabled)
    - help                      Show this help
    - quit                      Exit

  State Analysis Features:
    ✅ Pad Created              Check if document has Pad objects
    ✅ Face Available           Check if faces are available for operations
    ✅ Active Body              Check if there's an active PartDesign body
    ✅ Sketch Plane Ready       Check if sketches are mapped to planes
    ✅ Constrained Base Sketch  Check if sketches are fully constrained
    ✅ Safe References          Check external reference integrity
    ✅ No Errors                Check for document errors
"""
        print(help_text)

    def show_file_info(self):
        """Show current file and directory information"""
        print("\nFile Location Information:")
        print("=" * 30)
        try:
            result = self.api_client.get_file_info()
            if result["status"] == "success":
                for line in result["message"].split('\n'):
                    if line.startswith("CURRENT_DIR: "):
                        print(f"Working Directory: {line.replace('CURRENT_DIR: ', '')}")
                    elif line.startswith("HOME_DIR: "):
                        print(f"Home Directory: {line.replace('HOME_DIR: ', '')}")
                    elif line.startswith("DOCUMENT_NAME: "):
                        print(f"Document Name: {line.replace('DOCUMENT_NAME: ', '')}")
                    elif line.startswith("DOCUMENT_PATH: "):
                        path = line.replace('DOCUMENT_PATH: ', '')
                        if path == "Not saved yet":
                            print(f"Document Status: {path}")
                            print("Default save location: Current working directory")
                        else:
                            print(f"Document Path: {path}")
            else:
                print(f"Error getting file info: {result['message']}")
        except Exception as e:
            print(f"Error: {e}")

    def show_save_info(self):
        """Show information about saved files"""
        if not self.command_executor:
            print("❌ Command executor not initialized")
            return
            
        save_info = self.command_executor.get_save_info()
        print("\n💾 File Save Information:")
        print("=" * 40)
        print(f"Auto-save enabled: {'✅ Yes' if save_info['auto_save_enabled'] else '❌ No'}")
        print(f"Save counter: {save_info['save_counter']}")
        
        if save_info['last_saved_path']:
            print(f"Last saved to: {save_info['last_saved_path']}")
            # Check if file exists
            if os.path.exists(save_info['last_saved_path']):
                file_size = os.path.getsize(save_info['last_saved_path'])
                print(f"File size: {file_size} bytes")
                mod_time = os.path.getmtime(save_info['last_saved_path'])
                import datetime
                mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                print(f"Last modified: {mod_time_str}")
            else:
                print("⚠️  File no longer exists at saved location")
        else:
            print("No files saved yet")

def main():
    parser = argparse.ArgumentParser(description="FreeCAD Command Line Interface")
    parser.add_argument('--gui', action='store_true', help='Use FreeCAD GUI instead of headless mode')
    parser.add_argument('--script', help='Execute a specific script file')
    parser.add_argument('--command', help='Execute a single command and exit')
    parser.add_argument('--analyze', help='Analyze a specific FreeCAD file and exit')
    parser.add_argument('--auto-analyze', action='store_true', help='Automatically analyze state after each command')
    parser.add_argument('--llm-provider', choices=['openai', 'google'], default='openai', help='LLM provider to use (openai or google)')
    parser.add_argument('--llm-api-key', help='API key for the selected LLM provider')
    args = parser.parse_args()
    
    # Initialize CLI
    cli = FreeCADCLI(use_headless=not args.gui, llm_provider=args.llm_provider, llm_api_key=args.llm_api_key)
    
    if args.analyze:
        # Analysis mode
        if cli.initialize():
            cli.analyze_state(args.analyze)
    elif args.script:
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