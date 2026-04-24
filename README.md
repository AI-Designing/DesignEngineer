# AI Designer - FreeCAD LLM Automation System

## 🎯 Overview

AI Designer is a comprehensive FreeCAD automation system that allows users to interact with FreeCAD using natural language commands. By leveraging Large Language Models (LLM), the application translates user input into executable commands for FreeCAD, maintaining intelligent state management and providing real-time feedback.

**Key Features:**
- **🧠 Intelligent State Management**: Saves and retrieves current design state with all required data
- **⚡ Low-Latency Processing**: Optimized for quick decision-making and execution
- **🔄 Real-time Updates**: Live progress tracking via WebSocket connections
- **🎯 LLM-Powered Decisions**: Uses AI to make intelligent next-step decisions
- **📊 Complete Component Building**: Capable of building entire design components

## 🏗️ Project Structure

```
ai-designing-designengineer/
├── src/
│   └── ai_designer/           # Main package
│       ├── __init__.py        # Package initialization
│       ├── __main__.py        # CLI entry point (python -m ai_designer)
│       ├── cli.py             # Command-line interface
│       ├── core/              # Core system components
│       │   ├── orchestrator.py      # System orchestration
│       │   ├── queue_manager.py     # Command queue management
│       │   ├── intent_processor.py  # Natural language processing
│       │   └── state_llm_integration.py # State-aware LLM integration
│       ├── freecad/           # FreeCAD API integration
│       │   ├── api_client.py         # FreeCAD API communication
│       │   ├── command_executor.py  # Command execution
│       │   ├── state_manager.py     # FreeCAD state management
│       │   └── state_aware_processor.py # State-aware processing
│       ├── llm/               # LLM integration
│       │   ├── client.py             # LLM client interfaces
│       │   └── prompt_templates.py  # LLM prompt templates
│       ├── realtime/          # Real-time features
│       │   └── websocket_manager.py # WebSocket connections
│       ├── parsers/           # Command parsing
│       │   └── command_parser.py    # Natural language parsing
│       ├── redis_utils/       # Redis state caching
│       ├── services/          # Additional services
│       └── utils/             # Utility functions
│           ├── analysis.py          # Design analysis tools
│           └── validation.py        # Input validation
├── examples/                  # Usage examples
│   ├── demos/                       # Demo scripts
│   │   ├── demo_continuous_updates.py   # Continuous updates demo
│   │   ├── demo_persistent_fix.py       # Persistent GUI demo
│   │   ├── demo_real_execution.py       # Real execution demo
│   │   ├── demo_realtime_freecad.py     # Real-time FreeCAD demo
│   │   └── demo_realtime_gui.py         # Real-time GUI demo
├── tools/                     # Development and utility tools
│   ├── monitoring/                   # Monitoring tools
│   │   └── websocket_monitor.py     # WebSocket connection monitor
│   ├── gui/                         # GUI management tools
│   │   ├── simple_gui_launcher.py   # Persistent GUI launcher
│   │   └── direct_gui_commands.py   # Direct GUI command sender
│   ├── debug/                       # Debugging utilities
│   ├── testing/                     # Testing tools
│   └── utilities/                   # General utilities
│   ├── demo_state_management.py     # State management demo
│   ├── state_cli_example.py         # CLI usage example
│   └── websocket_client_example.py  # WebSocket client example
├── tools/                     # Development and testing tools
│   ├── monitoring/                   # Real-time monitoring tools
│   │   └── websocket_monitor.py     # WebSocket real-time monitor
│   ├── gui/                         # GUI management tools
│   │   ├── simple_gui_launcher.py   # Persistent FreeCAD GUI launcher
│   │   └── direct_gui_commands.py   # Direct GUI command sender
│   ├── debug/                       # Debug and troubleshooting tools
│   │   ├── debug_freecad_gui.py     # GUI debugging utilities
│   │   └── debug_gui_communication.py # Communication debugging
│   ├── testing/                     # Testing and validation tools
│   │   ├── test_complex_workflow.py # Complex workflow tests
│   │   ├── test_persistent_gui_fix.py # GUI persistence tests
│   │   ├── test_realtime_commands.py # Real-time command tests
│   │   └── test_redis_demo.py       # Redis integration tests
│   └── utilities/                   # General utilities
│       ├── verify_real_objects.py   # Object verification utility
│       ├── create_gear.py           # Gear creation utility
│       └── quick_test_workflow.py   # Quick workflow testing
├── scripts/                   # Utility scripts
│   ├── run_complex_demo.sh          # Complex shapes demo
│   └── run_tests.sh                 # Test runner
├── tests/                     # Test suite
│   ├── test_freecad.py              # FreeCAD tests
│   ├── test_llm.py                  # LLM tests
│   └── test_state_analysis.py      # State analysis tests
├── docs/                      # Documentation
│   ├── architecture.md              # System architecture
│   ├── STATE_MANAGEMENT.md         # State management guide
│   ├── STATE_ANALYSIS.md           # State analysis guide
│   └── advanced/                    # Advanced documentation
│       └── COMPLEX_SHAPES.md       # Complex shapes guide
├── config/                    # Configuration files
│   ├── config.yaml                 # Main configuration
│   └── redis.conf                  # Redis configuration
├── outputs/                   # Generated files
├── pyproject.toml            # Project configuration and dependencies
├── LICENSE                   # MIT License
├── CONTRIBUTING.md          # Contribution guidelines
└── README.md                # This file
```

## 📦 Installation

### Prerequisites
```bash
# Install FreeCAD (required)
sudo apt install freecad  # Ubuntu/Debian
# or
brew install freecad      # macOS

# Install Redis (optional, for enhanced features)
sudo apt install redis-server  # Ubuntu/Debian
# or
brew install redis            # macOS
```

### Install AI Designer

#### From Source (Development)
```bash
# Clone the repository
git clone https://github.com/your-username/ai-designing-designengineer.git
cd ai-designing-designengineer

# Install in development mode
pip install -e .[dev]
```

#### From PyPI (Coming Soon)
```bash
pip install ai-designer
```

### Configuration
1. Set your LLM API key:
   ```bash
   export GOOGLE_API_KEY="your-api-key"  # pragma: allowlist secret
   # or
   export OPENAI_API_KEY="your-api-key"  # pragma: allowlist secret
   ```

2. Start Redis (optional but recommended for enhanced features):
   ```bash
   redis-server
   ```

## 🚀 Usage

### Command Line Interface

#### Basic Usage
```bash
# Run AI Designer with standard features
ai-designer --interactive

# Execute a single command
ai-designer "Create a cube with dimensions 10x10x10"

# Analyze an existing FreeCAD file
ai-designer --analyze path/to/file.FCStd
```

#### Enhanced Mode (Full Features)
```bash
# Run with enhanced state management and real-time features
ai-designer --enhanced --interactive --llm-provider google --llm-api-key your-key  # pragma: allowlist secret

# Run enhanced mode with custom configuration
ai-designer --enhanced --redis-host localhost --websocket-port 8765 --max-concurrent 5
```

### Python API

#### Basic Usage
```python
from ai_designer import FreeCADCLI

# Initialize the CLI
cli = FreeCADCLI(
    use_headless=True,
    llm_provider='google',
    llm_api_key='your-api-key'  # pragma: allowlist secret
)

# Execute commands
if cli.initialize():
    cli.execute_command("Create a cube and add a cylinder next to it")
```

#### Enhanced Usage with Full State Management
```python
from ai_designer.core.orchestrator import SystemOrchestrator

# Initialize with full configuration
config = {
    'redis_host': 'localhost',
    'redis_port': 6379,
    'llm_provider': 'google',
    'llm_api_key': 'your-api-key',  # pragma: allowlist secret
    'enable_realtime': True,
    'websocket_port': 8765
}

orchestrator = SystemOrchestrator(config)
orchestrator.start_system()

# Process commands with full state awareness
result = orchestrator.process_user_input_enhanced(
    "Create a complex building structure with multiple floors",
    session_id="my_design_session"
)

print(f"Status: {result['status']}")
print(f"Objects created: {result['execution']['objects_created']}")
```

### Real-time Features

#### WebSocket Client
```python
import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Register for session updates
        await websocket.send(json.dumps({
            "type": "register_session",
            "session_id": "my_session"
        }))

        # Listen for real-time updates
        async for message in websocket:
            data = json.loads(message)
            print(f"Update: {data}")

# Run the WebSocket client
asyncio.run(websocket_client())
```

## 🧪 Examples

### Basic Shape Creation
```bash
ai-designer "Create a cube with dimensions 20x20x20"
ai-designer "Add a cylinder with radius 5 and height 15 next to the cube"
ai-designer "Change the cube color to red and the cylinder color to blue"
```

### Complex Design Tasks
```bash
ai-designer --enhanced "Design a simple house with walls, roof, and windows"
ai-designer --enhanced "Create a mechanical part with holes and fillets"
ai-designer --enhanced "Build a tower structure with multiple levels"
```

### Analysis and Export
```bash
ai-designer "Analyze the current design and provide dimensions"
ai-designer "Export the design as STL file"
ai-designer "What objects are currently in the document?"
```

## 🔧 System Architecture

The system implements a comprehensive architecture with the following layers:

### User Layer
- **Natural Language Interface**: Accept user commands in plain English
- **Error Handling**: Comprehensive error recovery and user feedback
- **Live Updates**: Real-time progress tracking and notifications

### AI Enhancement Layer
- **Intent Processing**: Understands and categorizes user requirements
- **Command Generation**: Creates appropriate FreeCAD commands
- **Context Analysis**: Analyzes current design state for informed decisions
- **Pattern Recognition**: Learns from previous commands and interactions

### Processing Layer
- **Queue Management**: Handles command prioritization and execution order
- **Load Balancing**: Distributes processing load across available resources
- **Safe Execution**: Sandboxed command execution with timeout protection

### Storage Layer
- **Design State Management**: Maintains current design context and history
- **Session Tracking**: Persistent user sessions across interactions
- **Performance Metrics**: System performance and usage analytics

### Real-time Layer
- **WebSocket Connections**: Live client connections for real-time updates
- **Progress Broadcasting**: Real-time command execution progress
- **State Notifications**: Immediate design state change notifications

## 📊 Performance & Monitoring

### Key Features
- **State Caching**: Redis-based state storage for low-latency access
- **Async Processing**: Non-blocking operations for better responsiveness
- **Performance Metrics**: Real-time system performance monitoring
- **Smart Caching**: LLM decision caching to reduce API calls

### Metrics Available
```python
metrics = orchestrator.get_performance_metrics()
# Includes: processing time, success rate, cache hit rate, connection count
```

## 🛠️ Development

### Setup Development Environment
```bash
git clone https://github.com/your-username/ai-designing-designengineer.git
cd ai-designing-designengineer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install in development mode
pip install -e .[dev]
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_freecad.py
pytest tests/test_llm.py

# Run with coverage
pytest --cov=ai_designer
```

### Real FreeCAD benchmarks (optional)

The `tests/benchmarks/` suite runs **real** `freecadcmd` subprocesses and asserts on structured document state (not only exit status). If no suitable console FreeCAD binary is available, these tests **skip** so default CI stays fast and green.

```bash
make test-freecad
```

Requires `freecadcmd` (or `FreeCADCmd`) on your `PATH`, or `FREECAD_PATH` pointing at a console-capable FreeCAD executable. Snap-only `freecad` is not used for this tier because it often does not support the same `-c script.py` workflow as `freecadcmd`.

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Start for Contributors
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with tests
4. Run quality checks: `black src/ && flake8 src/ && pytest`
5. Submit a pull request

## � Development Tools

AI Designer includes comprehensive development and testing tools located in the `tools/` directory:

### 🔍 Monitoring Tools
- **WebSocket Monitor** (`tools/monitoring/websocket_monitor.py`): Real-time monitoring of WebSocket communication
- Live progress tracking and error notifications

### 🖥️ GUI Tools
- **GUI Launcher** (`tools/gui/simple_gui_launcher.py`): Persistent FreeCAD GUI management
- **Direct Commands** (`tools/gui/direct_gui_commands.py`): Send commands directly to GUI via socket

### 🐛 Debug Tools
- **GUI Debug** (`tools/debug/debug_freecad_gui.py`): FreeCAD GUI debugging utilities
- **Communication Debug** (`tools/debug/debug_gui_communication.py`): Socket communication testing

### 🧪 Testing Tools
- **Workflow Tests** (`tools/testing/test_complex_workflow.py`): Complex workflow validation
- **GUI Tests** (`tools/testing/test_persistent_gui_fix.py`): GUI persistence testing
- **Real-time Tests** (`tools/testing/test_realtime_commands.py`): Real-time command execution tests

### 🔧 Utilities
- **Object Verification** (`tools/utilities/verify_real_objects.py`): Verify created FreeCAD objects
- **Gear Creation** (`tools/utilities/create_gear.py`): Complex gear generation utility

For detailed tool usage, see [`tools/README.md`](tools/README.md).

## �📚 Documentation

- [Architecture Guide](docs/architecture.md) - System architecture overview
- [State Management](docs/STATE_MANAGEMENT.md) - State management details
- [Complex Shapes](docs/advanced/COMPLEX_SHAPES.md) - Advanced shape creation
- [API Reference](docs/) - Complete API documentation

## 🔒 Security & Safety

- **Command Sanitization**: Prevents dangerous operations
- **Execution Sandboxing**: Isolated command execution environment
- **State Validation**: Ensures design state consistency
- **Timeout Protection**: Prevents infinite loops and hangs
- **Resource Monitoring**: Memory and CPU usage limits

## � Documentation

For detailed information about specific components:

- **[Tools Guide](docs/TOOLS_GUIDE.md)** - Complete guide to development and utility tools
- **[Examples Guide](docs/EXAMPLES_GUIDE.md)** - Usage examples and demo scripts
- **[Real-time System Guide](REALTIME_SYSTEM_GUIDE.md)** - WebSocket and real-time features
- **[Security Guide](docs/SECURITY_GUIDE.md)** - Security features and best practices
- **[Project Summary](PROJECT_SUMMARY.md)** - High-level project overview

## �📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FreeCAD](https://www.freecadweb.org/) community for the excellent CAD platform
- [OpenAI](https://openai.com/) and [Google](https://ai.google/) for LLM capabilities
- [Redis](https://redis.io/) for high-performance caching
- WebSocket protocol for real-time communication

---

## 🚀 Quick Demo

Experience AI Designer in action:

```bash
# Start the enhanced system
ai-designer --enhanced --interactive

# In another terminal, connect to real-time updates
python examples/websocket_client_example.py

# Try these commands:
"Create a parametric model of a chair"
"Add a table with adjustable height"
"Design a simple house layout"
"Export the entire scene as OBJ file"
```

The system will demonstrate:
- ✅ Intelligent intent understanding and processing
- ✅ State-aware LLM decision making
- ✅ Real-time progress tracking and updates
- ✅ Automatic state management and checkpointing
- ✅ Comprehensive error handling and recovery
- ✅ Performance monitoring and optimization

**Experience the future of AI-powered CAD automation!** 🎉
