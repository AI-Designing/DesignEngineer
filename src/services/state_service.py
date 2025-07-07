"""
FreeCAD State Management Service

This service integrates the FreeCAD state analyzer with Redis caching
to provide a complete state management solution.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from redis_utils.client import RedisClient
from redis_utils.state_cache import StateCache
from freecad.state_manager import FreeCADStateAnalyzer

class FreeCADStateService:
    """
    Comprehensive state management service for FreeCAD
    
    This service provides:
    - Document state analysis and caching
    - Historical state tracking
    - State comparison and monitoring
    - Easy retrieval and management of cached states
    """
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, api_client=None):
        """
        Initialize the state service
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            api_client: FreeCAD API client for subprocess operations
        """
        # Initialize Redis client and connect
        self.redis_client = RedisClient(redis_host, redis_port, redis_db)
        self.state_cache = StateCache(self.redis_client)
        self.state_analyzer = FreeCADStateAnalyzer(api_client)
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to Redis server"""
        try:
            self.connected = self.redis_client.connect()
            return self.connected
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            return False
    
    def analyze_and_cache_state(self, doc_path: str = None, document_name: str = None, 
                               session_id: str = None, expiration: int = 3600) -> Dict[str, Any]:
        """
        Analyze FreeCAD document state and cache the results
        
        Args:
            doc_path: Path to FreeCAD document (optional)
            document_name: Name of the document for key generation
            session_id: Session identifier
            expiration: Cache expiration time in seconds (default 1 hour)
            
        Returns:
            Dictionary containing analysis results and cache information
        """
        if not self.connected:
            raise ConnectionError("Not connected to Redis. Call connect() first.")
        
        # Perform state analysis
        analysis_result = self.state_analyzer.analyze_document_state(doc_path)
        
        if "error" in analysis_result:
            return {
                "success": False,
                "error": analysis_result["error"],
                "timestamp": datetime.now().isoformat()
            }
        
        # Extract document name from analysis if not provided
        if not document_name and "document" in analysis_result:
            document_name = analysis_result["document"]
        
        # Cache the analysis result
        analysis_key = self.state_cache.cache_analysis(
            analysis_data=analysis_result,
            document_name=document_name,
            analysis_type="full_analysis",
            expiration=expiration
        )
        
        # Cache individual state components for quick access
        if "analysis" in analysis_result:
            state_key = self.state_cache.cache_state(
                state_data=analysis_result["analysis"],
                document_name=document_name,
                session_id=session_id,
                expiration=expiration
            )
        else:
            state_key = None
        
        return {
            "success": True,
            "analysis_key": analysis_key,
            "state_key": state_key,
            "document_name": document_name,
            "analysis_result": analysis_result,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_current_state(self, document_name: str = None, session_id: str = None) -> Optional[Dict[str, Any]]:
        """Get the most recent state for a document/session"""
        if not self.connected:
            raise ConnectionError("Not connected to Redis")
        
        latest_key = self.state_cache.get_latest_state(document_name, session_id)
        if latest_key:
            return self.state_cache.retrieve_state(latest_key)
        return None
    
    def get_current_analysis(self, document_name: str = None) -> Optional[Dict[str, Any]]:
        """Get the most recent analysis for a document"""
        if not self.connected:
            raise ConnectionError("Not connected to Redis")
        
        latest_key = self.state_cache.get_latest_analysis(document_name, "full_analysis")
        if latest_key:
            return self.state_cache.retrieve_analysis(latest_key)
        return None
    
    def get_state_history(self, document_name: str = None, session_id: str = None, 
                         limit: int = 10) -> List[Dict[str, Any]]:
        """Get historical states for a document/session"""
        if not self.connected:
            raise ConnectionError("Not connected to Redis")
        
        keys = self.state_cache.list_states(document_name, session_id)
        
        # Get the most recent entries (up to limit)
        recent_keys = keys[-limit:] if len(keys) > limit else keys
        
        history = []
        for key in reversed(recent_keys):  # Most recent first
            state_data = self.state_cache.retrieve_with_metadata(key)
            if state_data:
                history.append({
                    "key": key,
                    "state": state_data.get("data"),
                    "metadata": state_data.get("metadata"),
                })
        
        return history
    
    def compare_states(self, key1: str, key2: str) -> Dict[str, Any]:
        """Compare two cached states"""
        if not self.connected:
            raise ConnectionError("Not connected to Redis")
        
        state1 = self.state_cache.retrieve_state(key1)
        state2 = self.state_cache.retrieve_state(key2)
        
        if not state1 or not state2:
            return {"error": "One or both states not found"}
        
        comparison = {
            "states_equal": state1 == state2,
            "differences": {},
            "key1": key1,
            "key2": key2
        }
        
        # Compare each field
        all_keys = set(state1.keys()) | set(state2.keys())
        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)
            
            if val1 != val2:
                comparison["differences"][key] = {
                    "state1": val1,
                    "state2": val2
                }
        
        return comparison
    
    def monitor_state_changes(self, document_name: str, target_conditions: Dict[str, bool]) -> Dict[str, Any]:
        """
        Monitor if specific conditions are met in the current state
        
        Args:
            document_name: Name of the document to monitor
            target_conditions: Dictionary of conditions to check (e.g., {"Pad Created": True})
            
        Returns:
            Monitoring result with status of each condition
        """
        current_state = self.get_current_state(document_name)
        
        if not current_state:
            return {
                "success": False,
                "error": "No current state found",
                "document_name": document_name
            }
        
        monitoring_result = {
            "success": True,
            "document_name": document_name,
            "timestamp": datetime.now().isoformat(),
            "conditions_met": {},
            "all_conditions_satisfied": True
        }
        
        for condition, expected_value in target_conditions.items():
            actual_value = current_state.get(condition)
            condition_met = actual_value == expected_value
            
            monitoring_result["conditions_met"][condition] = {
                "expected": expected_value,
                "actual": actual_value,
                "satisfied": condition_met
            }
            
            if not condition_met:
                monitoring_result["all_conditions_satisfied"] = False
        
        return monitoring_result
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of the state service"""
        status = {
            "connected": self.connected,
            "redis_connection": {
                "host": self.redis_client.host,
                "port": self.redis_client.port,
                "db": self.redis_client.db
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if self.connected:
            try:
                summary = self.state_cache.get_metadata_summary()
                status["cache_summary"] = summary
            except Exception as e:
                status["cache_error"] = str(e)
        
        return status
    
    def cleanup_old_data(self, older_than_hours: int = 24) -> Dict[str, int]:
        """Clean up old cached data"""
        if not self.connected:
            raise ConnectionError("Not connected to Redis")
        
        cutoff_time = time.time() - (older_than_hours * 3600)
        
        # Get all keys
        state_keys = self.state_cache.list_states()
        analysis_keys = self.state_cache.list_analyses()
        
        deleted_states = 0
        deleted_analyses = 0
        
        # Delete old state keys (based on timestamp in key)
        for key in state_keys:
            try:
                timestamp = int(key.split(":")[-1])
                if timestamp < cutoff_time:
                    if self.state_cache.delete_state(key):
                        deleted_states += 1
            except (ValueError, IndexError):
                continue
        
        # Delete old analysis keys
        for key in analysis_keys:
            try:
                timestamp = int(key.split(":")[-1])
                if timestamp < cutoff_time:
                    if self.state_cache.delete_analysis(key):
                        deleted_analyses += 1
            except (ValueError, IndexError):
                continue
        
        return {
            "deleted_states": deleted_states,
            "deleted_analyses": deleted_analyses,
            "cutoff_hours": older_than_hours
        }
    
    def export_data(self, document_name: str = None, format: str = "json") -> Union[str, Dict[str, Any]]:
        """Export cached data for a document"""
        if not self.connected:
            raise ConnectionError("Not connected to Redis")
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "document_name": document_name,
            "states": [],
            "analyses": []
        }
        
        # Get states
        state_keys = self.state_cache.list_states(document_name)
        for key in state_keys:
            state_data = self.state_cache.retrieve_with_metadata(key)
            if state_data:
                export_data["states"].append({
                    "key": key,
                    "data": state_data
                })
        
        # Get analyses
        analysis_keys = self.state_cache.list_analyses(document_name)
        for key in analysis_keys:
            analysis_data = self.state_cache.retrieve_with_metadata(key)
            if analysis_data:
                export_data["analyses"].append({
                    "key": key,
                    "data": analysis_data
                })
        
        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            return export_data
