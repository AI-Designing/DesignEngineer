import sys
import os
import argparse

# Add src directory to path if not already there
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

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
    parser.add_argument('--auto-gui', action='store_true', default=True,
                       help='Automatically open objects in FreeCAD GUI after creation (default: True)')
    parser.add_argument('--no-auto-gui', action='store_true',
                       help='Disable automatic GUI opening')
    
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
    
    # Determine auto-gui setting
    auto_gui = args.auto_gui and not args.no_auto_gui
    
    # Create CLI instance with proper configuration
    cli = FreeCADCLI(
        use_headless=args.headless,
        llm_provider=args.llm_provider,
        llm_api_key=args.llm_api_key,
        auto_open_gui=auto_gui
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
        if auto_gui:
            print("🖥️  Auto-GUI is ENABLED - objects will open in FreeCAD GUI after creation")
        else:
            print("🖥️  Auto-GUI is DISABLED - use 'gui' command to view objects manually")
        cli.interactive_mode()

if __name__ == "__main__":
    main()