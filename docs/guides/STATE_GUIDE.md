# State Management Comprehensive Guide

## Table of Contents
1. [Overview](#overview)
2. [Redis Integration](#redis-integration)
3. [State Analysis](#state-analysis)
4. [Usage](#usage)
5. [Best Practices](#best-practices)

---

## Overview

The FreeCAD State Management System provides comprehensive analysis and persistence of CAD document states through intelligent Redis caching and real-time analysis capabilities. This system enables continuous monitoring, historical tracking, and intelligent decision-making based on document state.

### Core Capabilities

The system provides:
- **🔍 Real-time State Analysis**: Continuous monitoring of FreeCAD document state
- **💾 Persistent Storage**: Redis-based caching with intelligent key management
- **📊 Historical Tracking**: Complete state history with timeline analysis
- **🎯 Condition Monitoring**: Track specific design milestones and requirements
- **🔄 State Comparison**: Compare states to identify changes and progressions
- **📈 Quality Metrics**: Comprehensive quality assessment and readiness scoring

### Key Features

#### State Analysis
- **Pad Created**: Check for Pad objects in document
- **Face Available**: Verify faces available for operations
- **Active Body**: Confirm active PartDesign body exists
- **Sketch Plane Ready**: Validate sketches mapped to planes
- **Constrained Base Sketch**: Check sketch constraint status
- **Safe References**: Verify external reference integrity
- **No Errors**: Document error detection and reporting

#### Data Management
- **Intelligent Caching**: Automatic state serialization with metadata
- **Key Organization**: Hierarchical key structure for easy retrieval
- **Expiration Control**: Configurable TTL for different data types
- **Query Capabilities**: Pattern matching and filtered searches
- **Export Functions**: JSON/dict export for backup and analysis

---

## Redis Integration

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │  CLI Interface │  │  WebSocket     │  │   REST API    │ │
│  └────────────────┘  └────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           FreeCAD State Service                     │    │
│  │  • Analysis & Caching    • State Monitoring         │    │
│  │  • History Management    • Comparison Tools         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Cache Layer                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              State Cache                            │    │
│  │  • Key Generation      • Serialization              │    │
│  │  • Metadata Management • Query Interface            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Redis Client                           │    │
│  │  • Connection Pool     • Command Interface          │    │
│  │  • Error Handling      • Retry Logic                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────────────┐
                    │ Redis Server  │
                    └───────────────┘
```

### Redis Client

**Location**: `src/redis/client.py`

The enhanced Redis client provides:

#### Basic Operations
```python
from redis_client import EnhancedRedisClient

# Initialize client
redis = EnhancedRedisClient(
    host='localhost',
    port=6379,
    db=0
)

# Connect
redis.connect()

# Basic operations
redis.set('key', 'value', expiration=3600)
value = redis.get('key')
exists = redis.exists('key')
redis.delete('key')
```

#### Hash Operations
```python
# Store complex objects as hashes
redis.hset('user:1', 'name', 'John')
redis.hset('user:1', 'age', '30')

# Retrieve single field
name = redis.hget('user:1', 'name')

# Retrieve all fields
user_data = redis.hgetall('user:1')
# Returns: {'name': 'John', 'age': '30'}
```

#### Advanced Operations
```python
# Find keys by pattern
state_keys = redis.keys('freecad:state:*')

# Delete all matching keys
redis.delete_pattern('temp:*')

# Clear entire database (use with caution!)
redis.flushdb()
```

### State Cache

**Location**: `src/redis/state_cache.py`

The state cache provides intelligent state management:

#### Key Generation

The system uses hierarchical keys for organization:

```python
# State keys
freecad:state:<document_name>:<session_id>:<timestamp>
freecad:state:<document_name>:<timestamp>
freecad:state:<session_id>:<timestamp>
freecad:state:<uuid>:<timestamp>

# Analysis keys
freecad:analysis:<analysis_type>:<document_name>:<timestamp>
freecad:analysis:<analysis_type>:<timestamp>

# Metadata keys
freecad:metadata:<original_key>
```

#### Cache Operations

```python
from redis.state_cache import StateCache

# Initialize cache
cache = StateCache(redis_client)

# Cache state data
cache.cache_state(
    state_data={'Pad Created': True, 'No Errors': True},
    document_name='MyProject',
    session_id='session_001',
    expiration=3600
)

# Cache analysis data
cache.cache_analysis(
    analysis_data=analysis_result,
    document_name='MyProject',
    analysis_type='full_analysis',
    expiration=7200
)

# Retrieve latest data
latest_state = cache.get_latest_state('MyProject')
latest_analysis = cache.get_latest_analysis('MyProject', 'full_analysis')
```

#### Data Structure

**Cached State Data:**
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

**Cached Analysis Data:**
```json
{
  "data": {
    "status": "success",
    "analysis": {
      "Pad Created": true,
      "Face Available": true,
      "Active Body": true,
      "Sketch Plane Ready": true,
      "Constrained Base Sketch": false,
      "Safe References": true,
      "No Errors": true
    },
    "document": "MyProject",
    "object_count": 5,
    "objects": [
      {"name": "Body", "type": "PartDesign::Body"},
      {"name": "Sketch", "type": "Sketcher::SketchObject"},
      {"name": "Pad", "type": "PartDesign::Pad"}
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

---

## State Analysis

### State Service

**Location**: `src/services/state_service.py`

The state service integrates FreeCAD analysis with Redis caching:

#### Basic Analysis

```python
from services.state_service import FreeCADStateService

# Initialize service
service = FreeCADStateService(
    redis_host='localhost',
    redis_port=6379,
    redis_db=0
)

# Connect
if service.connect():
    # Analyze and cache current state
    result = service.analyze_and_cache_state(
        document_name="MyProject",
        session_id="session_001",
        expiration=3600
    )

    if result['success']:
        print(f"State cached: {result['state_key']}")
        print(f"Analysis cached: {result['analysis_key']}")
```

#### Analysis Results

The analysis checks multiple conditions:

| Condition | Check | Purpose |
|-----------|-------|---------|
| **Pad Created** | Document has Pad objects | Verify 3D geometry exists |
| **Face Available** | Faces available for operations | Enable face-based operations |
| **Active Body** | Active PartDesign body exists | Confirm working context |
| **Sketch Plane Ready** | Sketches mapped to planes | Validate sketch setup |
| **Constrained Base Sketch** | Base sketch fully constrained | Ensure design stability |
| **Safe References** | External references valid | Prevent broken links |
| **No Errors** | Document error-free | Confirm document health |

#### Readiness Scoring

```python
def calculate_readiness_score(analysis):
    """Calculate overall readiness percentage"""
    total_checks = len(analysis)
    passed_checks = sum(1 for v in analysis.values() if v)

    score = (passed_checks / total_checks) * 100

    if score >= 90:
        status = "✅ Production ready"
    elif score >= 70:
        status = "⚠️ Needs attention"
    else:
        status = "❌ Significant issues"

    return {
        'score': score,
        'passed': passed_checks,
        'total': total_checks,
        'status': status
    }
```

### State Monitoring

#### Condition-Based Monitoring

```python
# Define target conditions
target_conditions = {
    "Pad Created": True,
    "Active Body": True,
    "No Errors": True
}

# Monitor current state against targets
result = service.monitor_state_changes(
    document_name="MyProject",
    target_conditions=target_conditions
)

if result['success']:
    if result['all_conditions_satisfied']:
        print("✅ All conditions met!")
    else:
        print("❌ Conditions not satisfied:")
        for condition, check in result['conditions_met'].items():
            if not check['satisfied']:
                print(f"  {condition}:")
                print(f"    Expected: {check['expected']}")
                print(f"    Actual: {check['actual']}")
```

#### Real-Time Monitoring

```python
import time

def monitor_design_progress(service, document_name, interval=5):
    """Monitor design progress in real-time"""

    previous_state = None

    while True:
        # Get current state
        current_state = service.get_current_state(document_name)

        if current_state and current_state != previous_state:
            # State changed - analyze
            readiness = calculate_readiness_score(
                current_state['data']
            )

            print(f"\n[{time.strftime('%H:%M:%S')}] State Update:")
            print(f"  Readiness: {readiness['score']:.1f}%")
            print(f"  Status: {readiness['status']}")

            # Check for improvements
            if previous_state:
                changes = compare_states(previous_state, current_state)
                if changes:
                    print(f"  Changes: {', '.join(changes)}")

            previous_state = current_state

        time.sleep(interval)
```

### State Comparison

```python
def compare_states(state1_key, state2_key):
    """Compare two cached states"""

    result = service.compare_states(state1_key, state2_key)

    if not result['states_equal']:
        print("States differ:")

        for field, diff in result['differences'].items():
            old_value = diff['state1']
            new_value = diff['state2']

            if old_value and not new_value:
                print(f"  ❌ {field}: Regression")
            elif not old_value and new_value:
                print(f"  ✅ {field}: Improvement")
            else:
                print(f"  🔄 {field}: Changed")
    else:
        print("States are identical")
```

---

## Usage

### Command Line Interface

**Location**: `state_cli.py`

The CLI provides comprehensive state management:

#### Basic Commands

```bash
# Analyze current state
python state_cli.py analyze --document "MyProject" --session "session1"

# Get current state
python state_cli.py get-state --document "MyProject"

# Get state history
python state_cli.py history --document "MyProject" --limit 10

# List all states
python state_cli.py list-states --document "MyProject"
```

#### Advanced Commands

```bash
# Monitor specific conditions
python state_cli.py monitor --document "MyProject" \
    --conditions '{"Pad Created": true, "No Errors": true}'

# Compare states
python state_cli.py compare \
    --key1 "freecad:state:MyProject:1642534567" \
    --key2 "freecad:state:MyProject:1642535000"

# Export data
python state_cli.py export --document "MyProject" \
    --output project_data.json --format json

# Clean up old data
python state_cli.py cleanup --older-than 24
```

#### Status and Diagnostics

```bash
# Check Redis connection
python state_cli.py status

# Get statistics
python state_cli.py stats --document "MyProject"

# Clear cache
python state_cli.py clear-cache --document "MyProject"
```

### Python API

#### Basic Usage

```python
from services.state_service import FreeCADStateService

# Initialize
service = FreeCADStateService()

# Connect to Redis
if not service.connect():
    print("Failed to connect to Redis")
    exit(1)

# Analyze and cache
result = service.analyze_and_cache_state(
    document_name="MyProject",
    session_id="demo_session"
)

# Get current state
current = service.get_current_state("MyProject")
print(f"Current readiness: {calculate_readiness_score(current['data'])['score']:.1f}%")

# Get history
history = service.get_state_history("MyProject", limit=5)
for entry in history:
    print(f"  {entry['timestamp']}: {entry['readiness']:.1f}%")
```

#### Advanced Usage

```python
# Custom expiration times
service.analyze_and_cache_state(
    document_name="TempWork",
    expiration=1800  # 30 minutes
)

service.analyze_and_cache_state(
    document_name="Production",
    expiration=604800  # 7 days
)

# Filtered searches
states = service.state_cache.get_states_by_pattern(
    pattern='freecad:state:MyProject:production_*'
)

# Export for backup
backup_data = service.export_data(
    document_name="MyProject",
    format="json"
)

with open('backup.json', 'w') as f:
    f.write(backup_data)

# Cleanup old data
cleanup_result = service.cleanup_old_data(older_than_hours=48)
print(f"Deleted {cleanup_result['deleted_states']} old states")
```

### Demo Application

**Location**: `demo_state_management.py`

Run the comprehensive demo:

```bash
python demo_state_management.py
```

The demo demonstrates:
1. Connection establishment
2. State analysis and caching
3. History retrieval
4. Condition monitoring
5. State comparison
6. Data export
7. Cleanup operations

---

## Best Practices

### 1. Connection Management

```python
# Use context manager for automatic cleanup
from contextlib import contextmanager

@contextmanager
def state_service_session(host='localhost', port=6379, db=0):
    """Context manager for state service"""
    service = FreeCADStateService(host, port, db)

    try:
        if not service.connect():
            raise ConnectionError("Failed to connect to Redis")
        yield service
    finally:
        service.disconnect()

# Usage
with state_service_session() as service:
    service.analyze_and_cache_state("MyProject")
```

### 2. Error Handling

```python
def safe_state_analysis(service, document_name):
    """Perform state analysis with error handling"""
    try:
        result = service.analyze_and_cache_state(
            document_name=document_name
        )

        if result['success']:
            return result
        else:
            logging.error(f"Analysis failed: {result.get('error')}")
            return None

    except ConnectionError as e:
        logging.error(f"Redis connection error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None
```

### 3. Performance Optimization

```python
# Batch operations
def analyze_multiple_documents(service, documents):
    """Analyze multiple documents efficiently"""
    results = []

    for doc in documents:
        # Use shorter expiration for batch analysis
        result = service.analyze_and_cache_state(
            document_name=doc,
            expiration=1800  # 30 minutes
        )
        results.append(result)

    return results

# Caching strategy
def get_or_analyze_state(service, document_name, max_age=300):
    """Get cached state or perform fresh analysis"""

    # Try to get recent state
    current = service.get_current_state(document_name)

    if current:
        # Check age
        timestamp = datetime.fromisoformat(
            current['metadata']['timestamp']
        )
        age = (datetime.now() - timestamp).total_seconds()

        if age < max_age:
            return current  # Use cached

    # Perform fresh analysis
    service.analyze_and_cache_state(document_name)
    return service.get_current_state(document_name)
```

### 4. Memory Management

```python
# Regular cleanup
import schedule

def scheduled_cleanup(service):
    """Schedule regular cleanup"""

    # Clean up data older than 24 hours
    result = service.cleanup_old_data(older_than_hours=24)
    logging.info(f"Cleanup: deleted {result['deleted_states']} states")

# Run cleanup daily at 2 AM
schedule.every().day.at("02:00").do(
    lambda: scheduled_cleanup(service)
)

# Manual cleanup with confirmation
def interactive_cleanup(service, older_than_hours):
    """Interactive cleanup with confirmation"""

    # Dry run to see what will be deleted
    keys_to_delete = service.state_cache.get_states_by_age(
        older_than_hours=older_than_hours
    )

    print(f"Will delete {len(keys_to_delete)} states")

    if input("Proceed? (y/n): ").lower() == 'y':
        result = service.cleanup_old_data(older_than_hours)
        print(f"Deleted {result['deleted_states']} states")
```

### 5. Monitoring and Alerting

```python
class StateMonitor:
    """Monitor state changes and send alerts"""

    def __init__(self, service):
        self.service = service
        self.alert_handlers = []

    def add_alert_handler(self, handler):
        """Add alert handler"""
        self.alert_handlers.append(handler)

    def monitor_condition(self, document_name, condition, interval=10):
        """Monitor specific condition"""

        previous_value = None

        while True:
            current_state = self.service.get_current_state(document_name)

            if current_state:
                current_value = current_state['data'].get(condition)

                # Check for changes
                if current_value != previous_value:
                    self._trigger_alerts({
                        'document': document_name,
                        'condition': condition,
                        'old_value': previous_value,
                        'new_value': current_value,
                        'timestamp': datetime.now()
                    })

                    previous_value = current_value

            time.sleep(interval)

    def _trigger_alerts(self, alert_data):
        """Trigger all registered alert handlers"""
        for handler in self.alert_handlers:
            handler(alert_data)

# Usage
def email_alert(alert_data):
    """Send email alert"""
    print(f"Email: {alert_data['condition']} changed in {alert_data['document']}")

def slack_alert(alert_data):
    """Send Slack alert"""
    print(f"Slack: {alert_data['condition']} changed in {alert_data['document']}")

monitor = StateMonitor(service)
monitor.add_alert_handler(email_alert)
monitor.add_alert_handler(slack_alert)
monitor.monitor_condition("CriticalProject", "No Errors")
```

### 6. Data Validation

```python
def validate_state_data(state_data):
    """Validate state data integrity"""

    required_fields = [
        'Pad Created',
        'Face Available',
        'Active Body',
        'Sketch Plane Ready',
        'Constrained Base Sketch',
        'Safe References',
        'No Errors'
    ]

    # Check all required fields present
    missing = [f for f in required_fields if f not in state_data]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    # Check all values are boolean
    invalid = [
        f for f, v in state_data.items()
        if not isinstance(v, bool)
    ]
    if invalid:
        raise ValueError(f"Invalid boolean values: {invalid}")

    return True
```

### 7. Backup and Recovery

```python
def backup_all_states(service, backup_dir='./backups'):
    """Backup all cached states"""

    import os
    from datetime import datetime

    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)

    # Get all documents
    all_keys = service.redis_client.keys('freecad:state:*')
    documents = set(key.split(':')[2] for key in all_keys)

    # Backup each document
    for doc in documents:
        data = service.export_data(doc, format='json')

        filename = f"{doc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(backup_dir, filename)

        with open(filepath, 'w') as f:
            f.write(data)

        print(f"Backed up {doc} to {filepath}")

def restore_from_backup(service, backup_file):
    """Restore states from backup"""

    import json

    with open(backup_file, 'r') as f:
        data = json.load(f)

    # Restore each state
    for state_entry in data.get('states', []):
        service.state_cache.cache_state(
            state_data=state_entry['data'],
            document_name=state_entry['metadata']['document_name'],
            session_id=state_entry['metadata'].get('session_id'),
            expiration=None  # No expiration for restored data
        )

    print(f"Restored {len(data.get('states', []))} states")
```

---

## Configuration

### Redis Configuration

**File**: `config/redis.conf`

```conf
# Network
bind 127.0.0.1
port 6379
timeout 300

# Memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis.log
```

### Service Configuration

**File**: `config/config.yaml`

```yaml
redis:
  host: localhost
  port: 6379
  db: 0
  timeout: 5
  retry_attempts: 3
  retry_delay: 1

state_service:
  default_expiration: 3600  # 1 hour
  max_history_items: 100
  cleanup_interval: 86400  # 24 hours

state_analysis:
  checks:
    - Pad Created
    - Face Available
    - Active Body
    - Sketch Plane Ready
    - Constrained Base Sketch
    - Safe References
    - No Errors

  thresholds:
    production_ready: 0.90
    needs_attention: 0.70
```

---

## Performance Considerations

### Memory Usage

- **State entry**: 1-5 KB
- **Analysis entry**: 2-10 KB
- **Metadata**: ~500 bytes per entry

### Recommended Limits

- **States per document**: 100-1000
- **Total cache size**: Monitor with `redis-cli info memory`
- **Cleanup frequency**: Daily or weekly

### Optimization Tips

1. **Use appropriate expiration times**
   ```python
   # Short-lived session data
   expiration=1800  # 30 minutes

   # Long-term project data
   expiration=604800  # 7 days

   # Permanent reference data
   expiration=None
   ```

2. **Regular cleanup**
   ```python
   # Daily cleanup of old data
   service.cleanup_old_data(older_than_hours=24)
   ```

3. **Efficient queries**
   ```python
   # Use specific patterns
   states = cache.get_states_by_pattern('freecad:state:MyProject:*')

   # Limit result sets
   history = service.get_state_history('MyProject', limit=10)
   ```

4. **Batch operations**
   ```python
   # Analyze multiple documents
   for doc in documents:
       service.analyze_and_cache_state(doc, expiration=1800)
   ```

---

## Troubleshooting

### Connection Issues

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Check connectivity
redis-cli -h localhost -p 6379 ping

# View Redis logs
tail -f /var/log/redis/redis.log
```

### Memory Issues

```bash
# Check memory usage
redis-cli info memory

# Clear all data (use with caution!)
redis-cli flushall

# Clear specific database
redis-cli -n 0 flushdb
```

### Performance Issues

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Monitor slow operations
service = FreeCADStateService()
service.redis_client.config_set('slowlog-log-slower-than', 1000)
```

---

## Use Cases

### 1. Design Workflow Tracking
Monitor design progression through stages and milestones.

### 2. Automated Quality Assurance
Continuously monitor for errors and constraint violations.

### 3. Collaborative Design
Share design state across team members with real-time updates.

### 4. Design Automation
Trigger automated actions when specific conditions are met.

---

**Version**: 1.0.0
**Last Updated**: February 2026
**Status**: Production Ready
