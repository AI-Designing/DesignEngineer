#!/usr/bin/env python3
import sys
import os
import argparse

# Fix imports to use absolute paths
try:
    from ai_designer.freecad.api_client import FreeCADAPIClient
    from ai_designer.freecad.command_executor import CommandExecutor
    from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
    from ai_designer.redis_utils.client import RedisClient
    from ai_designer.redis_utils.state_cache import StateCache
except ImportError:
    # Fallback for when running as script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from ai_designer.freecad.api_client import FreeCADAPIClient
    from ai_designer.freecad.command_executor import CommandExecutor
    from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
    from ai_designer.redis_utils.client import RedisClient
    from ai_designer.redis_utils.state_cache import StateCache

class FreeCADCLI:
    def __init__(self, use_headless=True, llm_provider="openai", llm_api_key=None, auto_open_gui=True):
        self.api_client = FreeCADAPIClient(use_headless=use_headless)
        self.command_executor = None
        self.state_cache = None
        self.state_analyzer = None
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.auto_open_gui = auto_open_gui
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
            self.command_executor = CommandExecutor(
                self.api_client, 
                self.state_cache, 
                llm_provider=self.llm_provider, 
                llm_api_key=self.llm_api_key,
                auto_open_gui=self.auto_open_gui
            )
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
                
                elif user_input.lower() in ['gui', 'open', 'view']:
                    # Open current document in GUI
                    result = self.command_executor.open_current_in_gui()
                    if result.get("status") == "success":
                        print("✅ Document opened in FreeCAD GUI")
                    else:
                        print(f"❌ Failed to open in GUI: {result.get('message', 'Unknown error')}")
                
                elif user_input.lower() in ['gui-on', 'auto-gui-on']:
                    # Enable auto GUI opening
                    self.command_executor.set_auto_open_gui(True)
                
                elif user_input.lower() in ['gui-off', 'auto-gui-off']:
                    # Disable auto GUI opening
                    self.command_executor.set_auto_open_gui(False)
                
                elif user_input.lower() in ['complex', 'examples']:
                    # Show complex shape examples
                    self.show_complex_examples()
                
                else:
                    self.execute_command(user_input)
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break

    def execute_command(self, command):
        """Execute a single command using Phase 2 & 3 advanced workflows"""
        try:
            print(f"🧠 Processing with Phase 2 & 3 workflows: {command}")
            
            # Use StateAwareCommandProcessor for all commands
            if hasattr(self.command_executor, 'state_aware_processor') and self.command_executor.state_aware_processor:
                print("🎯 Using advanced State-Aware Processing (Phase 2 & 3)")
                
                # Let the state-aware processor handle workflow detection and execution
                result = self.command_executor.state_aware_processor.process_complex_command(command)
                
                # Display detailed workflow results
                self._display_workflow_results(result, command)
                
            else:
                print("⚠️ Falling back to basic processing")
                # Fallback to basic processing
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
            import traceback
            traceback.print_exc()
    
    def _display_workflow_results(self, result, original_command):
        """Display detailed results from Phase 2 & 3 workflow processing"""
        print(f"\n📊 Workflow Execution Results:")
        print("=" * 50)
        
        status = result.get('status', 'unknown')
        workflow_type = result.get('workflow', 'unknown')
        
        # Status with emoji
        status_emoji = "✅" if status == 'success' else "❌" if status == 'error' else "⚠️"
        print(f"Status: {status_emoji} {status.upper()}")
        print(f"Workflow: {workflow_type}")
        print(f"Command: {original_command}")
        
        # Phase 2: Face Selection Results
        if workflow_type == 'face_selection':
            print(f"\n🎯 Phase 2 - Face Selection Workflow:")
            selected_face = result.get('selected_face')
            if selected_face:
                print(f"  • Selected Face: {selected_face.get('object_name', 'Unknown')}")
                print(f"  • Face Type: {selected_face.get('face_type', 'Unknown')}")
                print(f"  • Suitability Score: {selected_face.get('suitability_score', 0):.2f}")
            
            operation_type = result.get('operation_type', 'Unknown')
            print(f"  • Operation: {operation_type}")
        
        # Phase 3: Complex Workflow Results
        elif workflow_type == 'complex_workflow':
            print(f"\n🏗️ Phase 3 - Complex Multi-Step Workflow:")
            total_steps = result.get('total_steps', 0)
            completed_steps = result.get('completed_steps', 0)
            failed_steps = result.get('failed_steps', 0)
            execution_time = result.get('execution_time', 0)
            complexity_score = result.get('complexity_score', 0)
            
            print(f"  • Total Steps: {total_steps}")
            print(f"  • Completed: {completed_steps}")
            print(f"  • Failed: {failed_steps}")
            print(f"  • Execution Time: {execution_time:.2f}s")
            print(f"  • Complexity Score: {complexity_score:.2f}")
            
            # Show step details
            step_results = result.get('step_results', [])
            if step_results:
                print(f"\n  🔧 Step Details:")
                for i, step in enumerate(step_results, 1):
                    if hasattr(step, 'status'):
                        step_status = "✅" if step.status == 'success' else "❌"
                        step_name = getattr(step, 'step_name', f'Step {i}')
                    else:
                        step_status = "✅" if step.get('status') == 'success' else "❌"
                        step_name = step.get('step_name', f'Step {i}')
                    print(f"    {step_status} {step_name}")
        
        # Phase 1: Sketch-Then-Operate Results
        elif workflow_type == 'sketch_then_operate':
            print(f"\n✏️ Phase 1 - Sketch-Then-Operate Workflow:")
            objects_created = result.get('objects_created', 0)
            print(f"  • Objects Created: {objects_created}")
            
            validation = result.get('validation', {})
            if validation:
                quality_score = validation.get('quality_score', 0)
                print(f"  • Quality Score: {quality_score:.2f}")
                
                issues = validation.get('issues', [])
                if issues:
                    print(f"  • Issues: {', '.join(issues)}")
        
        # Multi-step workflow results
        elif workflow_type == 'multi_step':
            print(f"\n🔄 Multi-Step Workflow:")
            steps_executed = result.get('steps_executed', 0)
            print(f"  • Steps Executed: {steps_executed}")
        
        # Show execution results
        execution_results = result.get('execution_results', [])
        if execution_results:
            print(f"\n📋 Execution Steps:")
            for i, exec_result in enumerate(execution_results, 1):
                step_status = "✅" if exec_result.get('status') == 'success' else "❌"
                operation = exec_result.get('operation', f'Step {i}')
                print(f"  {step_status} {operation}")
        
        # Final state summary
        final_state = result.get('final_state', {})
        if final_state:
            object_count = final_state.get('object_count', 0)
            print(f"\n📈 Final State: {object_count} objects in document")
        
        # Success message
        if status == 'success':
            print(f"\n🎉 SUCCESS: Advanced workflow completed!")
            if workflow_type == 'complex_workflow':
                print(f"✅ Phase 3 complex multi-step workflow executed")
            elif workflow_type == 'face_selection':
                print(f"✅ Phase 2 intelligent face selection performed")
            elif workflow_type == 'sketch_then_operate':
                print(f"✅ Phase 1 sketch-then-operate workflow completed")
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
            suggestion = result.get('suggestion', '')
            if suggestion:
                print(f"💡 Suggestion: {suggestion}")

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
🚀 Phase 2 & 3 Enhanced FreeCAD CLI - Advanced Workflow System

Available Commands:
  🎯 Smart Natural Language Processing:
    - create box 10x20x30                    Create a box with dimensions
    - create cylinder radius 5               Create a cylinder  
    - create sphere radius 10                Create a sphere
    - add hole on top face                   Phase 2: Intelligent face selection
    - create bracket with mounting holes     Phase 3: Complex multi-step workflow
    - design gear with hub and fillets       Phase 3: Advanced feature generation
    - build assembly with multiple parts     Phase 3: Complex assembly workflow
  
  🏗️ Phase 3 - Complex Multi-Step Workflows:
    - create a bracket with 4 mounting holes and fillets
    - design a gear housing with cover and mounting features  
    - build a complex mechanical assembly with patterns
    - create architectural structure with multiple levels
    - make a planetary gear system with sun, planet, and ring gears
    - design a tower with base, pillars, and roof
    - create a rocket with body, nose cone, and fins
  
  🎯 Phase 2 - Intelligent Face Selection & Operations:
    - add 10mm hole on the top face          Smart face detection
    - create pocket in the center            Optimal face selection
    - drill 4 holes in square pattern        Pattern on selected face
    - add mounting holes on flat surface     Surface analysis
    - create slots on the side face          Face type recognition
  
  ✏️ Phase 1 - Sketch-Then-Operate (Enhanced):
    - create 50mm diameter cylinder 100mm tall    Parametric sketch creation
    - make rectangular base 100x50x10mm           Constraint-based modeling
    - design L-shaped bracket with dimensions     Complex sketch geometry
  
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
    - gui / open / view         Open current document in FreeCAD GUI
    - gui-on / auto-gui-on      Enable automatic GUI opening after commands
    - gui-off / auto-gui-off    Disable automatic GUI opening
    - complex / examples        Show complex shape examples
    - help                      Show this help
    - quit                      Exit

🚀 Advanced Workflow Features (Phase 2 & 3):

  🎯 Phase 2 - Face Selection Engine:
    ✅ Intelligent Face Detection    Automatically finds suitable faces
    ✅ Face Type Recognition         Distinguishes flat, curved, complex faces
    ✅ Suitability Scoring          Ranks faces by operation compatibility
    ✅ Surface Area Analysis         Considers face size for operations
    ✅ Normal Vector Calculation     Determines face orientation
    ✅ Smart Hole Placement          Optimal positioning for holes/pockets

  🏗️ Phase 3 - Complex Workflow Orchestrator:
    ✅ Multi-Step Decomposition     Breaks complex commands into steps
    ✅ Dependency Management        Ensures proper step execution order
    ✅ Pattern Generation           Creates linear, circular, matrix patterns
    ✅ Feature Operations           Adds fillets, chamfers, shells automatically
    ✅ Assembly Operations          Coordinates multiple part creation
    ✅ Complexity Analysis          Scores and routes commands intelligently
    ✅ Workflow Validation          Ensures each step completes successfully

  📊 Intelligent Strategy Selection:
    🔍 Simple Command              → Direct execution
    ✏️ Sketch Required            → Phase 1: Sketch-then-operate workflow
    🎯 Face Operation             → Phase 2: Face selection workflow  
    🔄 Multi-step Process         → Traditional multi-step workflow
    🏗️ Complex Assembly          → Phase 3: Complex workflow orchestrator

  🎛️ Real-time Workflow Analysis:
    📈 Complexity Scoring         Analyzes command complexity (0-1 scale)
    📊 Step Estimation            Predicts number of execution steps
    🔍 Strategy Detection         Automatically selects optimal workflow
    ⚡ Performance Optimization   Routes commands to best processor
    📋 Progress Tracking          Shows step-by-step execution status

  Examples by Workflow Type:

  Phase 1 (Sketch-Then-Operate):
    "create 50mm diameter cylinder 100mm tall"
    "make rectangular pocket 20x10x5mm deep"
    "design circular pad with 25mm radius"

  Phase 2 (Face Selection):  
    "add 8mm hole on the top face"
    "create rectangular pocket on flat surface"
    "drill 4 mounting holes in corners"

  Phase 3 (Complex Workflows):
    "create bracket with 4 mounting holes and fillets"
    "design gear housing with cover and ventilation"
    "build mechanical assembly with multiple components"
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

    def execute_complex_shape(self, description):
        """Execute complex shape creation with multiple operations"""
        print(f"🔄 Creating complex shape: {description}")
        
        # Enhanced prompts for complex shape creation
        complex_prompts = {
            "cone and cylinder": [
                "create a cylinder with radius 5 and height 10",
                "create a cone with radius 3 and height 8 positioned on top of the cylinder",
                "fuse the cylinder and cone together"
            ],
            "tower": [
                "create a cylinder base with radius 8 and height 5",
                "create a smaller cylinder with radius 6 and height 10 on top",
                "create a cone roof with radius 6 and height 6 on top",
                "fuse all parts together"
            ],
            "rocket": [
                "create a cylinder body with radius 4 and height 20",
                "create a cone nose with radius 4 and height 8 on top",
                "create 4 small cylinders as fins with radius 1 and height 6",
                "position fins around the base",
                "fuse body and nose together"
            ],
            "complex structure": [
                "create a box base 20x20x5",
                "create a cylinder pillar radius 3 height 15 at each corner",
                "create a cone roof radius 8 height 5 in the center",
                "fuse all components together"
            ]
        }
        
        # Try to match the description to known complex shapes
        description_lower = description.lower()
        
        if "cone" in description_lower and "cylinder" in description_lower:
            commands = complex_prompts["cone and cylinder"]
        elif "tower" in description_lower:
            commands = complex_prompts["tower"]
        elif "rocket" in description_lower:
            commands = complex_prompts["rocket"]
        elif "complex" in description_lower or "structure" in description_lower:
            commands = complex_prompts["complex structure"]
        else:
            # Fallback to LLM for complex interpretation
            commands = [f"create a complex shape: {description}"]
        
        results = []
        for i, command in enumerate(commands, 1):
            print(f"  Step {i}/{len(commands)}: {command}")
            try:
                if command.startswith('!'):
                    # Direct FreeCAD Python command
                    freecad_command = command[1:]
                    result = self.command_executor.execute(freecad_command)
                else:
                    # Natural language command
                    result = self.command_executor.execute_natural_language(command)
                
                if result["status"] == "success":
                    print(f"    ✓ {result['message']}")
                    results.append(result)
                else:
                    print(f"    ✗ Error: {result['message']}")
                    # Continue with next step even if one fails
                    
            except Exception as e:
                print(f"    ✗ Exception: {e}")
        
        print(f"✅ Complex shape creation completed with {len(results)} successful operations")
        return results

    def show_complex_examples(self):
        """Show examples of Phase 2 & 3 enhanced commands"""
        examples = """
🚀 Phase 2 & 3 Enhanced Command Examples:

🎯 Phase 2 - Intelligent Face Selection & Operations:

  Basic Face Operations:
    add 10mm hole on the top face
    create 5mm deep pocket on flat surface  
    drill 6mm hole in the center
    make rectangular slot on side face
    add chamfer to sharp edges
  
  Advanced Face Operations:
    create 4 mounting holes in square pattern
    add threaded holes with M6 specification
    make keyway slot on cylindrical surface
    create counterbore holes for cap screws
    drill angled holes at 45 degrees
  
  Multi-Face Operations:
    add holes on all flat faces
    create pockets on top and bottom
    drill holes on cylindrical surfaces
    make slots on parallel faces

🏗️ Phase 3 - Complex Multi-Step Workflows:

  Mechanical Components:
    create a bracket with 4 mounting holes and fillets
    design a gear with 20 teeth and central hub
    build a bearing housing with mounting features
    make a shaft collar with set screws
    create a pulley with keyway and hub
  
  Assembly Workflows:
    design a gear box housing with cover and mounting
    build a motor mount with vibration damping
    create a valve body with inlet and outlet ports
    make a pump housing with impeller chamber
    design a bearing block with lubrication fittings
  
  Architectural Elements:
    create a column with base and capital
    build a staircase with railings and supports
    design a truss structure with multiple joints
    make a roof frame with rafters and beams
    create a foundation with anchor bolts
  
  Pattern & Feature Operations:
    create linear pattern of holes along edge
    make circular pattern of mounting features
    add matrix pattern of ventilation holes
    create helical pattern around cylinder
    make variable spacing pattern with fillets

✏️ Phase 1 Enhanced - Sketch-Then-Operate:

  Parametric Sketching:
    create 50mm diameter cylinder 100mm tall
    make rectangular base 100x50x10mm with fillets
    design L-shaped bracket with specific dimensions
    create hexagonal prism with 25mm sides
    make tapered cylinder with 20mm to 10mm diameter

🔄 Workflow Strategy Examples:

  Command: "create box"
  → Strategy: Simple (direct execution)
  
  Command: "create 50mm cylinder with 10mm hole"  
  → Strategy: Sketch-then-operate (Phase 1)
  
  Command: "add hole on top face"
  → Strategy: Face selection (Phase 2)
  
  Command: "create bracket with mounting holes and fillets"
  → Strategy: Complex workflow (Phase 3)

💡 Pro Tips for Advanced Workflows:

  🎯 For Face Operations:
    - Mention face location: "top", "side", "flat", "cylindrical"
    - Specify operation: "hole", "pocket", "slot", "chamfer"
    - Include dimensions: "10mm diameter", "5mm deep"
  
  🏗️ For Complex Workflows:
    - Use descriptive terms: "bracket", "housing", "assembly"
    - Mention multiple features: "holes and fillets"
    - Specify patterns: "4 holes in square pattern"
    - Include mounting: "mounting features", "bolt holes"
  
  ⚡ System Intelligence:
    - Commands are automatically analyzed for complexity
    - Optimal workflow strategy is selected automatically
    - Multi-step operations are decomposed intelligently
    - Face selection happens automatically when needed
    - Pattern operations are recognized and executed
    - Feature operations (fillets, chamfers) are applied automatically

🔧 Example Workflow Progressions:

  Simple → Complex:
    1. "create cylinder" (Phase 1)
    2. "add hole on top" (Phase 2) 
    3. "add 4 mounting holes in pattern" (Phase 2 + Pattern)
    4. "create bracket with multiple holes and fillets" (Phase 3)

  The system learns your intent and applies the most sophisticated
  workflow automatically for optimal results!
"""
        print(examples)

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