# FreeCAD State Management System

This document describes the comprehensive state management system that integrates FreeCAD state analysis with Redis caching for persistent storage and retrieval.

## 🏗️ Architecture Overview

The system consists of several key components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FreeCAD       │    │ State Service   │    │   Redis Cache   │
│   Document      │───▶│   (Analysis &   │───▶│   (Persistent   │
│   Analysis      │    │   Integration)  │    │    Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   CLI & Demo    │
                       │   Interfaces    │
                       └─────────────────┘
```

## 📦 Components

### 1. Enhanced Redis Client (`src/redis/client.py`)
- **Basic Operations**: set, get, delete, exists
- **Advanced Operations**: hash operations (hset, hget, hgetall)
- **Utility Functions**: keys listing, pattern matching, database flushing
- **Connection Management**: Automatic connection handling with error checking

### 2. State Cache (`src/redis/state_cache.py`)
- **Intelligent Key Generation**: Automatic key generation with timestamps and metadata
- **Data Serialization**: JSON serialization with metadata enhancement
- **Organized Storage**: Separate prefixes for states vs analyses
- **Retrieval Functions**: Latest data retrieval, historical access, filtered searches
- **Metadata Management**: Comprehensive metadata tracking and indexing

### 3. State Service (`src/services/state_service.py`)
- **Integration Layer**: Combines FreeCAD analysis with Redis caching
- **Analysis & Caching**: One-step analysis and storage
- **State Monitoring**: Condition-based monitoring with customizable targets
- **Data Management**: Export, cleanup, comparison utilities
- **History Tracking**: Complete state history with timeline analysis

## 🚀 Quick Start

### Prerequisites
1. **Redis Server**: Install and start Redis
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   redis-server
   
   # Or using Docker
   docker run -d -p 6379:6379 redis:latest
   ```

2. **Python Dependencies**: Install required packages
   ```bash
   pip install -r requirements.txt
   ```

### Basic Usage

#### 1. Using the State Service Directly

```python
from services.state_service import FreeCADStateService

# Initialize service
service = FreeCADStateService(
    redis_host='localhost',
    redis_port=6379,
    redis_db=0
)

# Connect to Redis
if service.connect():
    print("Connected to Redis!")
    
    # Analyze and cache current FreeCAD state
    result = service.analyze_and_cache_state(
        document_name="MyProject",
        session_id="session_001",
        expiration=3600  # 1 hour
    )
    
    if result['success']:
        print(f"Analysis cached with key: {result['analysis_key']}")
        
        # Retrieve current state
        current_state = service.get_current_state("MyProject")
        print("Current state:", current_state)
```

#### 2. Using the Command Line Interface

```bash
# Analyze current FreeCAD state
python state_cli.py analyze --document "MyProject" --session "session1"

# Get current state
python state_cli.py get-state --document "MyProject"

# Monitor specific conditions
python state_cli.py monitor --document "MyProject" \
    --conditions '{"Pad Created": true, "No Errors": true}'

# List all cached states
python state_cli.py list-states --document "MyProject"

# Get state history
python state_cli.py history --document "MyProject" --limit 5

# Export data
python state_cli.py export --document "MyProject" --output project_data.json
```

#### 3. Running the Demo

```bash
# Run the comprehensive demo
python demo_state_management.py
```

## 🔧 Key Management System

The system uses a hierarchical key structure for organized data storage:

### Key Patterns

#### State Keys
```
freecad:state:<document_name>:<session_id>:<timestamp>
freecad:state:<document_name>:<timestamp>
freecad:state:<session_id>:<timestamp>
freecad:state:<uuid>:<timestamp>
```

#### Analysis Keys
```
freecad:analysis:<analysis_type>:<document_name>:<timestamp>
freecad:analysis:<analysis_type>:<timestamp>
```

#### Metadata Keys
```
freecad:metadata:<original_key>
```

### Examples
```
freecad:state:MyProject:session_001:1642534567
freecad:analysis:full_analysis:MyProject:1642534567
freecad:metadata:freecad:state:MyProject:session_001:1642534567
```

## 📊 Data Structure

### Cached State Data
```json
{
  "data": {
    "Pad Created": true,
    "Face Available": true,
    "Active Body": true,
    "Sketch Plane Ready": true,
    "Constrained Base Sketch": false,
    "Safe References": true,
    "No Errors": true
  },
  "metadata": {
    "timestamp": "2024-01-18T10:30:45.123456",
    "document_name": "MyProject",
    "session_id": "session_001",
    "key": "freecad:state:MyProject:session_001:1642534567",
    "type": "state"
  }
}
```

### Cached Analysis Data
```json
{
  "data": {
    "status": "success",
    "analysis": {
      "Pad Created": true,
      "Face Available": true,
      // ... other analysis results
    },
    "document": "MyProject",
    "object_count": 5,
    "objects": [
      {"name": "Body", "type": "PartDesign::Body"},
      {"name": "Sketch", "type": "Sketcher::SketchObject"}
    ]
  },
  "metadata": {
    "timestamp": "2024-01-18T10:30:45.123456",
    "document_name": "MyProject",
    "analysis_type": "full_analysis",
    "key": "freecad:analysis:full_analysis:MyProject:1642534567",
    "type": "analysis"
  }
}
```

## 🔍 Advanced Features

### 1. State Monitoring
Monitor specific conditions and get notified when they change:

```python
# Define target conditions
target_conditions = {
    "Pad Created": True,
    "Active Body": True,
    "No Errors": True
}

# Monitor current state
result = service.monitor_state_changes("MyProject", target_conditions)

if result['success']:
    if result['all_conditions_satisfied']:
        print("✅ All conditions met!")
    else:
        print("❌ Some conditions not satisfied:")
        for condition, check in result['conditions_met'].items():
            if not check['satisfied']:
                print(f"  {condition}: Expected {check['expected']}, got {check['actual']}")
```

### 2. State Comparison
Compare different states to track changes:

```python
# Get two state keys from history
history = service.get_state_history("MyProject", limit=2)
key1 = history[0]['key']
key2 = history[1]['key']

# Compare states
comparison = service.compare_states(key1, key2)

if not comparison['states_equal']:
    print("States differ:")
    for field, diff in comparison['differences'].items():
        print(f"  {field}: {diff['state1']} → {diff['state2']}")
```

### 3. Data Export and Backup
Export all data for a document:

```python
# Export as JSON string
json_data = service.export_data("MyProject", format="json")

# Export as Python dict
dict_data = service.export_data("MyProject", format="dict")

# Save to file
with open("myproject_backup.json", "w") as f:
    f.write(json_data)
```

### 4. Automatic Cleanup
Remove old data automatically:

```python
# Clean up data older than 24 hours
result = service.cleanup_old_data(older_than_hours=24)
print(f"Deleted {result['deleted_states']} states and {result['deleted_analyses']} analyses")
```

## 🔧 Configuration

### Redis Configuration
The system connects to Redis using these default settings:
- **Host**: localhost
- **Port**: 6379
- **Database**: 0

You can customize these when initializing the service:

```python
service = FreeCADStateService(
    redis_host='your-redis-host',
    redis_port=6380,
    redis_db=1
)
```

### Cache Expiration
Set custom expiration times for different data types:

```python
# Short-term session data (30 minutes)
service.analyze_and_cache_state(
    document_name="TempWork",
    expiration=1800
)

# Long-term project data (7 days)
service.analyze_and_cache_state(
    document_name="ImportantProject", 
    expiration=604800
)

# Permanent data (no expiration)
service.analyze_and_cache_state(
    document_name="ReferenceModel",
    expiration=None
)
```

## 📈 Performance Considerations

### Memory Usage
- Each state entry typically uses 1-5 KB of Redis memory
- Analysis data is usually 2-10 KB per entry
- Metadata adds approximately 500 bytes per entry

### Recommended Limits
- **States per document**: 100-1000 depending on frequency
- **Total cache size**: Monitor Redis memory usage
- **Cleanup frequency**: Run cleanup daily or weekly

### Optimization Tips
1. **Use appropriate expiration times** to prevent memory bloat
2. **Regular cleanup** of old data
3. **Monitor Redis memory usage** with `redis-cli info memory`
4. **Use specific document/session filters** when retrieving data

## 🧪 Testing

Run the included tests to verify functionality:

```bash
# Test Redis connectivity
python -c "
from services.state_service import FreeCADStateService
service = FreeCADStateService()
print('Redis connection:', service.connect())
"

# Run the demo
python demo_state_management.py

# Test CLI
python state_cli.py status
```

## 🎯 Use Cases

### 1. CAD Design Workflow Tracking
- Track design progression through different stages
- Monitor completion of key design milestones
- Identify when designs meet specific criteria

### 2. Automated Quality Assurance
- Continuously monitor for design errors
- Ensure sketches remain properly constrained
- Verify geometric relationships are maintained

### 3. Collaborative Design
- Share design state across team members
- Track changes made by different users
- Maintain design history for review

### 4. Design Automation
- Trigger automated actions when conditions are met
- Build design workflows based on state changes
- Create design validation pipelines

## 🔮 Future Enhancements

### Planned Features
1. **Real-time notifications** when monitored conditions change
2. **Web dashboard** for visualizing state data
3. **Integration with CI/CD pipelines** for automated design validation
4. **Machine learning** analysis of design patterns
5. **Distributed caching** for multi-user environments

### Extension Points
- Custom analysis functions
- Additional data storage backends
- Integration with other CAD systems
- Custom notification channels

## 🤝 Contributing

To extend or modify the system:

1. **Add new analysis functions** in `FreeCADStateAnalyzer`
2. **Extend storage capabilities** in `StateCache`
3. **Add new CLI commands** in `state_cli.py`
4. **Create custom monitoring conditions** in the service layer

## 📝 License

This project is part of the FreeCAD LLM Automation system. See the main project documentation for licensing information.
