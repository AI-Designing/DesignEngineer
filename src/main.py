import sys
import os
import argparse
from cli import FreeCADCLI

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="FreeCAD LLM Automation System")
    
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
    
    # Analysis mode
    parser.add_argument('--analyze', type=str, metavar='FILE',
                       help='Analyze a FreeCAD file')
    
    # Command execution
    parser.add_argument('command', nargs='*',
                       help='Command to execute')
    
    return parser.parse_args()

def main():
    """
    Main entry point for FreeCAD LLM Automation
    """
    print("FreeCAD LLM Automation System")
    print("=" * 40)
    
    args = parse_arguments()
    
    # Create CLI instance with proper configuration
    cli = FreeCADCLI(
        use_headless=args.headless,
        llm_provider=args.llm_provider,
        llm_api_key=args.llm_api_key
    )
    
    # Handle different modes
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
        print("💾 Auto-save is ENABLED - files will be saved automatically after each command")
        cli.interactive_mode()

if __name__ == "__main__":
    main()