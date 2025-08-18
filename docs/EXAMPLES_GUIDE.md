# Examples Directory

This directory contains demonstration scripts and usage examples for the FreeCAD LLM Automation system.

## Structure

```
examples/
├── README.md                        # This file  
├── demos/                          # Demo scripts
│   ├── demo_continuous_updates.py  # Continuous updates demonstration
│   ├── demo_persistent_fix.py      # Persistent GUI fixes demonstration
│   ├── demo_real_execution.py      # Real execution mode demonstration
│   ├── demo_realtime_freecad.py    # Real-time FreeCAD interaction
│   └── demo_realtime_gui.py        # Real-time GUI updates
├── demo_state_management.py        # State management example
├── state_cli_example.py           # CLI usage examples
└── websocket_client_example.py    # WebSocket client examples
```

## Demo Scripts (`demos/`)

### Continuous Updates Demo
**File:** `demos/demo_continuous_updates.py`  
Demonstrates how the system provides continuous updates during command execution.

### Persistent GUI Demo  
**File:** `demos/demo_persistent_fix.py`  
Shows how the persistent FreeCAD GUI maintains state across multiple commands.

### Real Execution Demo
**File:** `demos/demo_real_execution.py`  
Demonstrates the difference between simulation mode and real execution mode (`--real` flag).

### Real-time FreeCAD Demo
**File:** `demos/demo_realtime_freecad.py`  
Shows real-time interaction with FreeCAD API and immediate object creation.

### Real-time GUI Demo
**File:** `demos/demo_realtime_gui.py`  
Demonstrates real-time GUI updates as commands are executed.

## Usage Examples

### State Management
**File:** `demo_state_management.py`  
Comprehensive example of state management features including saving, loading, and caching design states.

### CLI Usage
**File:** `state_cli_example.py`  
Examples of using the command-line interface with various natural language commands.

### WebSocket Client
**File:** `websocket_client_example.py`  
Example of connecting to the WebSocket server for real-time monitoring and communication.

## Running Examples

### Basic Usage
```bash
# Run state management demo
python examples/demo_state_management.py

# Run CLI examples  
python examples/state_cli_example.py

# Run WebSocket client example
python examples/websocket_client_example.py
```

### Demo Scripts
```bash
# Run continuous updates demo
python examples/demos/demo_continuous_updates.py

# Run real execution demo
python examples/demos/demo_real_execution.py

# Run real-time GUI demo
python examples/demos/demo_realtime_gui.py
```

### With Main CLI System
```bash
# Start main CLI system
python -m ai_designer.cli --llm-provider google

# In another terminal, run examples
python examples/websocket_client_example.py
```

## Prerequisites

- FreeCAD installed and accessible via `freecad` command
- Python environment with required dependencies
- API key configured (Google Gemini or OpenAI)
- Redis server running (optional, for state caching)

## Configuration

Most examples use the same configuration as the main system:
- Environment variables or `.env` file for API keys
- Default WebSocket server on `localhost:8765`
- Default Redis connection on `localhost:6379`

## Integration

These examples are designed to work with:
- Main AI Designer CLI system
- Development tools in `tools/` directory
- Testing framework in `tests/` directory
- Monitoring tools for real-time feedback
