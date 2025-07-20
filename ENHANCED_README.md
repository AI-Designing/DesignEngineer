# Enhanced FreeCAD LLM Automation System

## 🎯 Overview

This is a comprehensive FreeCAD automation system that implements the complete architecture shown in `architecture.md`. The system provides:

- **🧠 Intelligent State Management**: Saves and retrieves current design state with all required data
- **⚡ Low-Latency Processing**: Optimized for quick decision-making and execution
- **🔄 Real-time Updates**: Live progress tracking via WebSocket connections
- **🎯 LLM-Powered Decisions**: Uses AI to make intelligent next-step decisions
- **📊 Complete Component Building**: Capable of building entire design components

## 🏗️ Architecture Implementation

The system follows the exact architecture diagram with these components:

### User Layer
- **User Input**: Natural language interface
- **Error Handler**: Comprehensive error recovery
- **Live Updates**: Real-time progress and status
- **Preview Gallery**: Design visualization

### AI Enhancement Layer  
- **Intent Processing**: Understands user requirements
- **Command Generator**: Creates appropriate FreeCAD commands
- **Context Analyzer**: Analyzes current design state
- **Pattern Recognition**: Learns from previous commands
- **Suggestions**: Provides intelligent next steps

### Processing Layer
- **Queue Manager**: Handles command prioritization
- **Command Queue**: Manages execution pipeline
- **Load Balancer**: Distributes processing load
- **FreeCAD Executor**: Executes commands safely
- **Script Execution**: Runs generated Python scripts

### Storage Layer
- **Design State**: Maintains current design context
- **User Sessions**: Tracks user interactions
- **Command History**: Stores execution history

### Real-time Layer
- **WebSocket Manager**: Handles live connections
- **Progress Tracker**: Monitors command execution
- **Live Updates**: Sends real-time notifications

## 🚀 Key Features

### State-Aware Decision Making
```python
# The system maintains complete context for every decision
decision_context = {
    'current_state': current_freecad_state,
    'command_history': previous_commands,
    'available_objects': existing_objects,
    'user_intent': processed_intent,
    'constraints': system_limits
}

# LLM uses this context to make informed decisions
llm_decision = llm_client.decide_next_action(decision_context)
```

### Low-Latency Processing
- **Intelligent Caching**: Frequently accessed states are cached
- **Async Processing**: Non-blocking command execution
- **State Checkpoints**: Periodic state snapshots for quick recovery
- **Performance Monitoring**: Real-time metrics tracking

### Real-time Updates
- **WebSocket Integration**: Live progress updates
- **Progress Tracking**: Visual command execution progress
- **State Notifications**: Immediate state change alerts
- **Error Broadcasting**: Real-time error notifications

## 📦 Installation

### Prerequisites
```bash
# Install FreeCAD (required)
sudo apt install freecad  # Ubuntu/Debian
# or
brew install freecad      # macOS

# Install Redis (optional, for state caching)
sudo apt install redis-server  # Ubuntu/Debian
# or
brew install redis            # macOS
```

### Install Dependencies
```bash
# Clone the repository
git clone <repository-url>
cd freecad-llm-automation

# Install Python dependencies
pip install -r requirements.txt

# Install additional WebSocket dependencies
pip install websockets fastapi uvicorn
```

### Configuration
1. Set your LLM API key:
   ```bash
   export GOOGLE_API_KEY="your-api-key"
   # or
   export OPENAI_API_KEY="your-api-key"
   ```

2. Start Redis (optional but recommended):
   ```bash
   redis-server
   ```

## 🎮 Usage

### Quick Start
```bash
# Run the enhanced system with full features
python enhanced_main.py
```

### WebSocket Client (Real-time Updates)
```bash
# In a separate terminal, run the WebSocket client
python websocket_client.py
```

### Basic Usage
```python
from src.core.orchestrator import SystemOrchestrator

# Initialize with configuration
config = {
    'redis_host': 'localhost',
    'redis_port': 6379,
    'llm_provider': 'google',
    'enable_realtime': True,
    'websocket_port': 8765
}

orchestrator = SystemOrchestrator(config)
orchestrator.start_system()

# Process user commands with full state awareness
result = orchestrator.process_user_input_enhanced(
    "Create a cube and then add a cylinder next to it",
    session_id="my_session"
)

print(f"Result: {result['status']}")
print(f"Objects created: {result['execution']['objects_created']}")
```

## 🔧 System Components

### 1. State-LLM Integration (`state_llm_integration.py`)
- Integrates state retrieval with LLM decision making
- Provides context-aware command generation
- Handles validation and execution with full state context

### 2. Enhanced Queue Manager (`queue_manager.py`)
- Priority-based command queuing
- Dependency resolution
- Concurrent execution with load balancing
- Real-time progress tracking

### 3. WebSocket Manager (`websocket_manager.py`)
- Real-time client connections
- Progress update broadcasting
- State change notifications
- Error and system status updates

### 4. Intent Processor (`intent_processor.py`)
- Natural language understanding
- Context-aware intent classification
- Entity extraction and parameter parsing
- Confidence scoring

### 5. System Orchestrator (`orchestrator.py`)
- Central coordination of all components
- Session management
- Performance monitoring
- State checkpointing

## 📊 State Management

### Automatic State Checkpointing
The system automatically saves design state every 30 seconds (configurable):

```python
# Force immediate state checkpoint
result = orchestrator.force_state_checkpoint("session_id")

# Get current session state
state = orchestrator.get_session_state("session_id")
```

### State Context for LLM Decisions
Every LLM decision includes full context:

- **Current Objects**: All objects in the FreeCAD document
- **Object Properties**: Dimensions, positions, materials
- **Command History**: Previous commands and their results
- **User Intent**: Processed natural language intent
- **System Constraints**: Memory, time, and capability limits

## 🌐 Real-time Features

### WebSocket API
Connect to `ws://localhost:8765` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8765');

// Register for a session
ws.send(JSON.stringify({
    type: 'register_session',
    session_id: 'my_session'
}));

// Receive real-time updates
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Update:', data);
};
```

### Message Types
- `progress_update`: Command execution progress
- `command_status`: Command completion status
- `state_change`: Design state changes
- `error`: Error notifications
- `user_notification`: System messages

## 📈 Performance Monitoring

### Metrics Available
```python
metrics = orchestrator.get_performance_metrics()

# Key metrics include:
# - Average processing time per command
# - LLM decision time
# - State retrieval time
# - Command execution time
# - Success rate
# - Cache hit rate
# - WebSocket connection count
# - Queue status
```

### Performance Optimization
- **State Caching**: Redis-based state storage
- **Command Batching**: Efficient execution grouping
- **Async Processing**: Non-blocking operations
- **Smart Caching**: LLM decision caching
- **Connection Pooling**: Efficient resource usage

## 🧪 Testing

### Demo Commands
The system includes comprehensive test commands:

```python
test_commands = [
    "Create a cube with dimensions 10x10x10",
    "Add a cylinder next to the cube", 
    "Change the cube color to red",
    "Analyze the current design",
    "Export the design as STL file",
    "What objects are currently in the document?"
]
```

### Running Tests
```bash
# Run the full demo with all test commands
python enhanced_main.py

# Run specific component tests
python -m pytest tests/
```

## 🔧 Configuration Options

```python
config = {
    # Redis Configuration
    'redis_host': 'localhost',
    'redis_port': 6379,
    
    # LLM Configuration  
    'llm_provider': 'google',  # or 'openai'
    'llm_api_key': 'your-api-key',
    
    # System Configuration
    'headless': True,
    'max_concurrent': 3,
    
    # Real-time Features
    'enable_realtime': True,
    'websocket_host': 'localhost', 
    'websocket_port': 8765,
    
    # Performance
    'state_checkpoint_interval': 30,  # seconds
    'command_timeout': 60,            # seconds
    'cache_ttl': 300                  # seconds
}
```

## 🚨 Error Handling

The system includes comprehensive error handling:

- **Command Validation**: Prevents dangerous operations
- **Execution Monitoring**: Timeout and failure detection
- **State Recovery**: Automatic checkpoint restoration
- **Graceful Degradation**: Fallback mechanisms
- **Real-time Error Notifications**: Immediate error reporting

## 🔒 Safety Features

- **Command Sanitization**: Prevents dangerous operations
- **Execution Sandboxing**: Isolated command execution  
- **State Validation**: Ensures consistency
- **Timeout Protection**: Prevents infinite loops
- **Resource Monitoring**: Memory and CPU limits

## 📚 API Reference

### Main Classes

#### `SystemOrchestrator`
- `start_system()`: Initialize and start all components
- `process_user_input_enhanced(input, session_id)`: Enhanced processing with full state context
- `get_session_state(session_id)`: Retrieve current session state
- `force_state_checkpoint(session_id)`: Force immediate state save

#### `StateLLMIntegration`  
- `process_user_request(input, session_id)`: Complete state-aware processing
- `get_performance_metrics()`: LLM and state performance data

#### `WebSocketManager`
- `start_server()`: Start WebSocket server
- `send_progress_update()`: Send progress notifications
- `send_state_change()`: Notify state changes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FreeCAD community for the excellent CAD platform
- OpenAI and Google for LLM capabilities
- Redis for high-performance caching
- WebSocket protocol for real-time communication

---

## 🚀 Quick Demo

To see the system in action:

1. **Start the system**: `python enhanced_main.py`
2. **Connect WebSocket client**: `python websocket_client.py` (in another terminal)
3. **Watch real-time updates** as the system processes commands
4. **Observe intelligent decision-making** based on current state

The system will demonstrate:
- ✅ Intent understanding and processing
- ✅ State-aware LLM decision making  
- ✅ Real-time progress tracking
- ✅ Automatic state management
- ✅ Error handling and recovery
- ✅ Performance monitoring

Experience the future of AI-powered CAD automation! 🎉
