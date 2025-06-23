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
        command = " ".join(sys.argv[1:])
        print(f"Executing command: {command}")
        
        cli = FreeCADCLI(use_headless=True)
        if cli.initialize():
            cli.execute_command(command)
    else:
        # Start interactive mode
        cli = FreeCADCLI(use_headless=True)
        cli.interactive_mode()

if __name__ == "__main__":
    main()