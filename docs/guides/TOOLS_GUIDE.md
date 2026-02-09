# FreeCAD LLM Automation - Tools

This directory contains various tools for development, testing, monitoring, and debugging the FreeCAD LLM automation system.

## Directory Structure

```
tools/
├── README.md                 # This file
├── monitoring/              # Real-time monitoring tools
│   └── websocket_monitor.py # WebSocket real-time monitor
├── gui/                     # GUI management tools
│   ├── simple_gui_launcher.py    # Persistent FreeCAD GUI launcher
│   └── direct_gui_commands.py    # Direct GUI command sender
├── debug/                   # Debug and troubleshooting tools
│   ├── debug_freecad_gui.py      # GUI debugging utilities
│   └── debug_gui_communication.py # Communication debugging
├── testing/                 # Testing and validation tools
│   ├── test_complex_workflow.py   # Complex workflow tests
│   ├── test_persistent_gui_fix.py # GUI persistence tests
│   ├── test_realtime_commands.py  # Real-time command tests
│   └── test_redis_demo.py         # Redis integration tests
└── utilities/               # General utilities
    ├── verify_real_objects.py     # Object verification utility
    ├── create_gear.py             # Gear creation utility
    └── quick_test_workflow.py     # Quick workflow testing
```

## Tool Categories

### 🔍 Monitoring Tools

#### WebSocket Monitor (`monitoring/websocket_monitor.py`)
Real-time monitoring of the WebSocket communication between CLI and GUI.

**Usage:**
```bash
python tools/monitoring/websocket_monitor.py
```

**Features:**
- Live progress tracking
- Command status monitoring
- Error notification display
- Connection status tracking

### 🖥️ GUI Tools

#### Simple GUI Launcher (`gui/simple_gui_launcher.py`)
Starts and manages a persistent FreeCAD GUI that stays open for real-time updates.

**Usage:**
```bash
python tools/gui/simple_gui_launcher.py
```

**Features:**
- Persistent FreeCAD GUI
- Socket communication setup
- Process management
- Auto-cleanup on exit

#### Direct GUI Commands (`gui/direct_gui_commands.py`)
Sends commands directly to a running FreeCAD GUI session via socket communication.

**Usage:**
```bash
python tools/gui/direct_gui_commands.py
```

**Features:**
- Direct socket communication
- Real-time object creation
- Colorful object visualization
- Immediate view updates

### 🐛 Debug Tools

#### Debug FreeCAD GUI (`debug/debug_freecad_gui.py`)
Debugging utilities for FreeCAD GUI issues.

#### Debug GUI Communication (`debug/debug_gui_communication.py`)
Tests and debugs socket communication between CLI and GUI.

**Usage:**
```bash
python tools/debug/debug_gui_communication.py
```

### 🧪 Testing Tools

#### Complex Workflow Tests (`testing/test_complex_workflow.py`)
Tests complex multi-step workflows with Phase 2 & 3 features.

#### Persistent GUI Tests (`testing/test_persistent_gui_fix.py`)
Tests the persistent GUI functionality and socket communication.

#### Real-time Commands Tests (`testing/test_realtime_commands.py`)
Tests real-time command execution and GUI updates.

#### Redis Demo Tests (`testing/test_redis_demo.py`)
Tests Redis integration for state caching and management.

### 🔧 Utilities

#### Object Verification (`utilities/verify_real_objects.py`)
Verifies that FreeCAD objects were actually created and saved correctly.

#### Gear Creation (`utilities/create_gear.py`)
Utility for creating complex gear objects with parameters.

#### Quick Workflow Test (`utilities/quick_test_workflow.py`)
Quick testing utility for basic workflow validation.

## Usage Examples

### Complete Real-time Workflow Test

1. **Start the persistent GUI:**
   ```bash
   python tools/gui/simple_gui_launcher.py
   ```

2. **Monitor WebSocket activity:**
   ```bash
   python tools/monitoring/websocket_monitor.py
   ```

3. **Send real-time commands:**
   ```bash
   python tools/gui/direct_gui_commands.py
   ```

4. **Verify objects were created:**
   ```bash
   python tools/utilities/verify_real_objects.py
   ```

### Debug Communication Issues

1. **Test GUI communication:**
   ```bash
   python tools/debug/debug_gui_communication.py
   ```

2. **Check debug logs:**
   ```bash
   python tools/debug/debug_freecad_gui.py
   ```

### Run Comprehensive Tests

```bash
# Test complex workflows
python tools/testing/test_complex_workflow.py

# Test GUI persistence
python tools/testing/test_persistent_gui_fix.py

# Test real-time commands
python tools/testing/test_realtime_commands.py
```

## Integration with Main System

These tools are designed to work with the main AI Designer CLI system:

```bash
# Start main CLI with real-time features
python -m ai_designer.cli --llm-provider google

# Use tools in parallel for monitoring and testing
python tools/monitoring/websocket_monitor.py &
python tools/gui/simple_gui_launcher.py
```

## Development Guidelines

- **Monitoring tools**: Should be non-intrusive and provide clear output
- **GUI tools**: Should handle graceful shutdown and cleanup
- **Debug tools**: Should provide detailed error information
- **Testing tools**: Should be automated and provide clear pass/fail results
- **Utilities**: Should be reusable and well-documented

## Configuration

Most tools use the same configuration as the main system:
- Google API key from environment or `.env` file
- WebSocket server on `localhost:8765`
- GUI communication ports auto-assigned
- Redis connection for state caching (optional)

## Troubleshooting

Common issues and solutions:

1. **GUI won't start**: Check FreeCAD installation and PATH
2. **WebSocket connection failed**: Ensure main CLI is running
3. **Socket communication errors**: Check port availability
4. **Object creation fails**: Verify API key and LLM access

For more detailed troubleshooting, use the debug tools in the `debug/` directory.
