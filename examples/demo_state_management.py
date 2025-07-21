#!/usr/bin/env python3
"""
Demo script for FreeCAD State Management System

This script demonstrates how to use the integrated state management system
to analyze FreeCAD documents and store/retrieve the results from Redis.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_designer.redis_utils.client import RedisClient

class MockFreeCADStateService:
    """Mock FreeCAD State Service for demonstration purposes"""
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, redis_db: int = 0):
        self.redis_client = RedisClient(host=redis_host, port=redis_port, db=redis_db)
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to Redis"""
        self.connected = self.redis_client.connect()
        return self.connected
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status"""
        status = {
            'connected': self.connected,
            'redis_connection': {
                'host': self.redis_client.host,
                'port': self.redis_client.port,
                'db': self.redis_client.db
            }
        }
        
        if self.connected:
            # Get cache summary
            state_keys = self.redis_client.keys("state:*")
            analysis_keys = self.redis_client.keys("analysis:*")
            
            status['cache_summary'] = {
                'total_states': len(state_keys),
                'total_analyses': len(analysis_keys)
            }
        
        return status
    
    def analyze_and_cache_state(self, document_name: str, session_id: str, expiration: int = 3600) -> Dict[str, Any]:
        """Analyze and cache FreeCAD state (mock implementation)"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected to Redis'}
        
        # Mock analysis data
        timestamp = datetime.now().isoformat()
        
        # Mock state data
        state_data = {
            'document_name': document_name,
            'session_id': session_id,
            'timestamp': timestamp,
            'object_count': 5,
            'active_document': True,
            'active_body': True,
            'sketch_count': 2,
            'solid_count': 1
        }
        
        # Mock analysis data
        analysis_data = {
            'document': document_name,
            'session_id': session_id,
            'timestamp': timestamp,
            'object_count': 5,
            'analysis': {
                'Pad Created': True,
                'Active Body': True,
                'Sketch Plane Ready': True,
                'No Errors': True,
                'Has Constraints': True
            }
        }
        
        # Store in Redis
        state_key = f"state:{document_name}:{session_id}"
        analysis_key = f"analysis:{document_name}:{session_id}"
        
        try:
            self.redis_client.set(state_key, json.dumps(state_data), ex=expiration)
            self.redis_client.set(analysis_key, json.dumps(analysis_data), ex=expiration)
            
            # Store in document history
            history_key = f"history:{document_name}"
            history_entry = {
                'key': state_key,
                'timestamp': timestamp,
                'session_id': session_id
            }
            self.redis_client.hset(history_key, timestamp, json.dumps(history_entry))
            
            return {
                'success': True,
                'state_key': state_key,
                'analysis_key': analysis_key,
                'analysis_result': analysis_data
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_current_state(self, document_name: str) -> Optional[Dict[str, Any]]:
        """Get current state for a document"""
        if not self.connected:
            return None
        
        # Get the most recent state
        state_keys = self.redis_client.keys(f"state:{document_name}:*")
        if not state_keys:
            return None
        
        # Get the first available state (in real implementation, would get most recent)
        state_data = self.redis_client.get(state_keys[0])
        if state_data:
            try:
                return json.loads(state_data)
            except json.JSONDecodeError:
                return None
        return None
    
    def get_current_analysis(self, document_name: str) -> Optional[Dict[str, Any]]:
        """Get current analysis for a document"""
        if not self.connected:
            return None
        
        # Get the most recent analysis
        analysis_keys = self.redis_client.keys(f"analysis:{document_name}:*")
        if not analysis_keys:
            return None
        
        # Get the first available analysis
        analysis_data = self.redis_client.get(analysis_keys[0])
        if analysis_data:
            try:
                return json.loads(analysis_data)
            except json.JSONDecodeError:
                return None
        return None
    
    def get_state_history(self, document_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get state history for a document"""
        if not self.connected:
            return []
        
        history_key = f"history:{document_name}"
        history_data = self.redis_client.hgetall(history_key)
        
        history = []
        for timestamp, entry_data in history_data.items():
            try:
                entry = json.loads(entry_data)
                entry['metadata'] = {'timestamp': timestamp}
                history.append(entry)
            except json.JSONDecodeError:
                continue
        
        # Sort by timestamp and limit
        history.sort(key=lambda x: x['metadata']['timestamp'], reverse=True)
        return history[:limit]
    
    def monitor_state_changes(self, document_name: str, target_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor state changes against target conditions"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected to Redis'}
        
        # Get current analysis
        current_analysis = self.get_current_analysis(document_name)
        if not current_analysis:
            return {'success': False, 'error': 'No analysis data available'}
        
        analysis_results = current_analysis.get('analysis', {})
        
        conditions_met = {}
        all_satisfied = True
        
        for condition, expected_value in target_conditions.items():
            actual_value = analysis_results.get(condition, False)
            is_satisfied = actual_value == expected_value
            
            conditions_met[condition] = {
                'expected': expected_value,
                'actual': actual_value,
                'satisfied': is_satisfied
            }
            
            if not is_satisfied:
                all_satisfied = False
        
        return {
            'success': True,
            'all_conditions_satisfied': all_satisfied,
            'conditions_met': conditions_met
        }
    
    def compare_states(self, state_key1: str, state_key2: str) -> Dict[str, Any]:
        """Compare two states"""
        if not self.connected:
            return {'error': 'Not connected to Redis'}
        
        state1_data = self.redis_client.get(state_key1)
        state2_data = self.redis_client.get(state_key2)
        
        if not state1_data or not state2_data:
            return {'error': 'One or both states not found'}
        
        try:
            state1 = json.loads(state1_data)
            state2 = json.loads(state2_data)
            
            differences = {}
            all_keys = set(state1.keys()) | set(state2.keys())
            
            for key in all_keys:
                val1 = state1.get(key)
                val2 = state2.get(key)
                
                if val1 != val2:
                    differences[key] = {
                        'state1': val1,
                        'state2': val2
                    }
            
            return {
                'states_equal': len(differences) == 0,
                'differences': differences
            }
            
        except json.JSONDecodeError:
            return {'error': 'Failed to parse state data'}
    
    def export_data(self, document_name: str, format: str = "dict") -> Dict[str, Any]:
        """Export data for a document"""
        if not self.connected:
            return {'states': [], 'analyses': []}
        
        # Get all states and analyses for the document
        state_keys = self.redis_client.keys(f"state:{document_name}:*")
        analysis_keys = self.redis_client.keys(f"analysis:{document_name}:*")
        
        states = []
        analyses = []
        
        # Export states
        for key in state_keys:
            state_data = self.redis_client.get(key)
            if state_data:
                try:
                    state = json.loads(state_data)
                    state['_key'] = key
                    states.append(state)
                except json.JSONDecodeError:
                    continue
        
        # Export analyses
        for key in analysis_keys:
            analysis_data = self.redis_client.get(key)
            if analysis_data:
                try:
                    analysis = json.loads(analysis_data)
                    analysis['_key'] = key
                    analyses.append(analysis)
                except json.JSONDecodeError:
                    continue
        
        return {
            'states': states,
            'analyses': analyses
        }
    
    def cleanup_old_data(self, older_than_hours: int = 24) -> Dict[str, Any]:
        """Cleanup old data (mock implementation)"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected to Redis'}
        
        # In a real implementation, this would delete old entries
        # For now, just return success
        return {
            'success': True,
            'deleted_states': 0,
            'deleted_analyses': 0
        }


def demo_basic_usage():
    """Demonstrate basic usage of the state service"""
    print("🚀 FreeCAD State Management Demo")
    print("=" * 50)
    
    # Initialize the service
    print("1. Initializing state service...")
    service = MockFreeCADStateService(
        redis_host='localhost',
        redis_port=6379,
        redis_db=0
    )
    
    # Connect to Redis
    print("2. Connecting to Redis...")
    if not service.connect():
        print("❌ Failed to connect to Redis. Make sure Redis server is running.")
        return None, None
    
    print("✅ Connected to Redis successfully!")
    
    # Get service status
    print("\n3. Service Status:")
    status = service.get_service_status()
    print(f"   Connected: {status['connected']}")
    print(f"   Redis: {status['redis_connection']['host']}:{status['redis_connection']['port']}")
    if 'cache_summary' in status:
        summary = status['cache_summary']
        print(f"   Cached States: {summary['total_states']}")
        print(f"   Cached Analyses: {summary['total_analyses']}")
    
    # Analyze and cache current state
    print("\n4. Analyzing and caching FreeCAD state...")
    result = service.analyze_and_cache_state(
        document_name="demo_document",
        session_id="demo_session_001",
        expiration=3600  # 1 hour
    )
    
    if result['success']:
        print("✅ State analysis completed and cached!")
        print(f"   Analysis Key: {result['analysis_key']}")
        print(f"   State Key: {result['state_key']}")
        
        # Display analysis results
        if 'analysis_result' in result and 'analysis' in result['analysis_result']:
            print("\n   📋 State Analysis Results:")
            analysis = result['analysis_result']['analysis']
            for key, value in analysis.items():
                status_icon = '✅' if value else '❌'
                print(f"      {key}: {status_icon}")
    else:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        return None, None
    
    return service, result


def demo_state_retrieval(service, cached_result):
    """Demonstrate state retrieval functionality"""
    print("\n5. Demonstrating State Retrieval...")
    print("-" * 40)
    
    # Get current state
    current_state = service.get_current_state("demo_document")
    if current_state:
        print("✅ Retrieved current state:")
        for key, value in current_state.items():
            print(f"   {key}: {value}")
    
    # Get current analysis
    current_analysis = service.get_current_analysis("demo_document")
    if current_analysis:
        print(f"\n✅ Retrieved current analysis for document: {current_analysis.get('document', 'Unknown')}")
        print(f"   Objects in document: {current_analysis.get('object_count', 0)}")
    
    # Get state history
    history = service.get_state_history("demo_document", limit=5)
    print(f"\n✅ State history (last {len(history)} entries):")
    for i, entry in enumerate(history):
        metadata = entry.get('metadata', {})
        timestamp = metadata.get('timestamp', 'Unknown')
        print(f"   {i+1}. {entry['key']} - {timestamp}")


def demo_monitoring(service):
    """Demonstrate state monitoring functionality"""
    print("\n6. Demonstrating State Monitoring...")
    print("-" * 40)
    
    # Define target conditions we want to monitor
    target_conditions = {
        "Pad Created": True,
        "Active Body": True,
        "Sketch Plane Ready": True,
        "No Errors": True
    }
    
    print("🔍 Monitoring conditions:")
    for condition, expected in target_conditions.items():
        print(f"   {condition}: {expected}")
    
    # Monitor current state
    monitoring_result = service.monitor_state_changes("demo_document", target_conditions)
    
    if monitoring_result['success']:
        print(f"\n📊 Monitoring Results:")
        print(f"   All conditions satisfied: {'✅' if monitoring_result['all_conditions_satisfied'] else '❌'}")
        
        for condition, result in monitoring_result['conditions_met'].items():
            status = '✅' if result['satisfied'] else '❌'
            print(f"   {condition}: {status} (Expected: {result['expected']}, Actual: {result['actual']})")
    else:
        print(f"❌ Monitoring failed: {monitoring_result.get('error', 'Unknown error')}")


def demo_advanced_features(service):
    """Demonstrate advanced features"""
    print("\n7. Demonstrating Advanced Features...")
    print("-" * 40)
    
    # Simulate multiple state captures over time
    print("📈 Simulating multiple state captures...")
    
    for i in range(3):
        time.sleep(1)  # Small delay between captures
        result = service.analyze_and_cache_state(
            document_name="demo_document",
            session_id=f"demo_session_{i+2:03d}",
            expiration=1800  # 30 minutes
        )
        if result['success']:
            print(f"   Capture {i+1}: {result['state_key']}")
    
    # Compare states
    print("\n🔄 Comparing states...")
    history = service.get_state_history("demo_document", limit=2)
    if len(history) >= 2:
        key1 = history[0]['key']
        key2 = history[1]['key']
        
        comparison = service.compare_states(key1, key2)
        if 'error' not in comparison:
            print(f"   States equal: {'✅' if comparison['states_equal'] else '❌'}")
            if comparison['differences']:
                print("   Differences found:")
                for field, diff in comparison['differences'].items():
                    print(f"      {field}: {diff['state1']} → {diff['state2']}")
            else:
                print("   No differences found")
    
    # Export data
    print("\n📤 Exporting data...")
    export_data = service.export_data("demo_document", format="dict")
    print(f"   Exported {len(export_data['states'])} states and {len(export_data['analyses'])} analyses")
    
    # Cleanup demo (optional)
    print("\n🧹 Cleanup options available:")
    print("   - service.cleanup_old_data(older_than_hours=1)")
    print("   - Clear all demo data from Redis")


def main():
    """Main demo function"""
    try:
        # Basic usage
        service, result = demo_basic_usage()
        
        if service is None:
            print("\n❌ Cannot proceed without Redis connection")
            print("\nMake sure Redis server is running:")
            print("   sudo systemctl start redis")
            print("   # or")
            print("   redis-server")
            return
        
        # State retrieval
        demo_state_retrieval(service, result)
        
        # Monitoring
        demo_monitoring(service)
        
        # Advanced features
        demo_advanced_features(service)
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Install Redis: sudo apt install redis-server")
        print("2. Start Redis server: redis-server")
        print("3. Install Python Redis client: pip install redis")
        print("4. Run this script: python demo_state_management.py")
        print("5. Integration with actual FreeCAD coming next!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()