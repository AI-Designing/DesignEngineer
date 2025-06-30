import sys
import os
from cli import FreeCADCLI

def main():
    """
    Main entry point for FreeCAD LLM Automation
    """
    print("FreeCAD LLM Automation System")
    print("=" * 40)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        
        # Check for analysis command
        if first_arg == "analyze" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            print(f"Analyzing file: {file_path}")
            
            cli = FreeCADCLI(use_headless=True)
            if cli.initialize():
                cli.analyze_state(file_path)
        else:
            # Regular command execution
            command = " ".join(sys.argv[1:])
            print(f"Executing command: {command}")
            
            cli = FreeCADCLI(use_headless=True)
            if cli.initialize():
                cli.execute_command(command)
    else:
        # Start interactive mode
        print("Starting interactive mode...")
        print("Type 'help' for available commands")
        print("💾 Auto-save is ENABLED - files will be saved automatically after each command")
        cli = FreeCADCLI(use_headless=True)
        cli.interactive_mode()

if __name__ == "__main__":
    main()