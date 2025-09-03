import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class StateCache:
    """Enhanced state cache for storing FreeCAD state analysis data in Redis"""

    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.key_prefix = "freecad"
        self.state_prefix = f"{self.key_prefix}:state"
        self.analysis_prefix = f"{self.key_prefix}:analysis"
        self.metadata_prefix = f"{self.key_prefix}:metadata"

    def generate_state_key(
        self, document_name: str = None, session_id: str = None
    ) -> str:
        """Generate a unique key for state data"""
        timestamp = int(time.time())
        if document_name:
            doc_key = document_name.replace(" ", "_").replace(".", "_")
            if session_id:
                return f"{self.state_prefix}:{doc_key}:{session_id}:{timestamp}"
            return f"{self.state_prefix}:{doc_key}:{timestamp}"

        if session_id:
            return f"{self.state_prefix}:{session_id}:{timestamp}"

        return f"{self.state_prefix}:{uuid.uuid4().hex[:8]}:{timestamp}"

    def generate_analysis_key(
        self, document_name: str = None, analysis_type: str = "general"
    ) -> str:
        """Generate a unique key for analysis data"""
        timestamp = int(time.time())
        if document_name:
            doc_key = document_name.replace(" ", "_").replace(".", "_")
            return f"{self.analysis_prefix}:{analysis_type}:{doc_key}:{timestamp}"
        return f"{self.analysis_prefix}:{analysis_type}:{timestamp}"

    def cache_state(
        self,
        state_data: Dict[str, Any],
        state_key: str = None,
        document_name: str = None,
        session_id: str = None,
        expiration: int = None,
    ) -> str:
        """
        Cache state data in Redis with metadata

        Args:
            state_data: The state data to cache
            state_key: Custom key (optional)
            document_name: Name of the FreeCAD document
            session_id: Session identifier
            expiration: Expiration time in seconds

        Returns:
            The key used to store the data
        """
        # Generate key if not provided
        if not state_key:
            state_key = self.generate_state_key(document_name, session_id)

        # Add metadata to state data
        enhanced_data = {
            "data": state_data,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "document_name": document_name,
                "session_id": session_id,
                "key": state_key,
                "type": "state",
            },
        }

        # Serialize and store
        serialized_data = json.dumps(enhanced_data)
        self.redis_client.set(state_key, serialized_data, ex=expiration)

        # Store in metadata index for easy retrieval
        self._update_metadata_index(state_key, enhanced_data["metadata"])

        return state_key

    def cache_analysis(
        self,
        analysis_data: Dict[str, Any],
        analysis_key: str = None,
        document_name: str = None,
        analysis_type: str = "general",
        expiration: int = None,
    ) -> str:
        """
        Cache analysis data in Redis with metadata

        Args:
            analysis_data: The analysis data to cache
            analysis_key: Custom key (optional)
            document_name: Name of the FreeCAD document
            analysis_type: Type of analysis (general, detailed, etc.)
            expiration: Expiration time in seconds

        Returns:
            The key used to store the data
        """
        # Generate key if not provided
        if not analysis_key:
            analysis_key = self.generate_analysis_key(document_name, analysis_type)

        # Add metadata to analysis data
        enhanced_data = {
            "data": analysis_data,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "document_name": document_name,
                "analysis_type": analysis_type,
                "key": analysis_key,
                "type": "analysis",
            },
        }

        # Serialize and store
        serialized_data = json.dumps(enhanced_data)
        self.redis_client.set(analysis_key, serialized_data, ex=expiration)

        # Store in metadata index for easy retrieval
        self._update_metadata_index(analysis_key, enhanced_data["metadata"])

        return analysis_key

    def retrieve_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve state data from Redis"""
        data = self.redis_client.get(state_key)
        if data:
            try:
                decoded_data = data.decode("utf-8") if isinstance(data, bytes) else data
                parsed_data = json.loads(decoded_data)
                return parsed_data.get("data") if "data" in parsed_data else parsed_data
            except json.JSONDecodeError:
                return None
        return None

    def retrieve_analysis(self, analysis_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis data from Redis"""
        return self.retrieve_state(analysis_key)  # Same logic as retrieve_state

    def retrieve_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data with full metadata"""
        data = self.redis_client.get(key)
        if data:
            try:
                decoded_data = data.decode("utf-8") if isinstance(data, bytes) else data
                return json.loads(decoded_data)
            except json.JSONDecodeError:
                return None
        return None

    def list_states(
        self, document_name: str = None, session_id: str = None
    ) -> List[str]:
        """List all state keys, optionally filtered by document or session"""
        pattern = f"{self.state_prefix}:*"
        if document_name:
            doc_key = document_name.replace(" ", "_").replace(".", "_")
            pattern = f"{self.state_prefix}:{doc_key}:*"

        keys = self.redis_client.keys(pattern)

        if session_id:
            keys = [k for k in keys if session_id in k]

        return sorted(keys)

    def list_analyses(
        self, document_name: str = None, analysis_type: str = None
    ) -> List[str]:
        """List all analysis keys, optionally filtered by document or type"""
        pattern = f"{self.analysis_prefix}:*"
        if analysis_type:
            pattern = f"{self.analysis_prefix}:{analysis_type}:*"
        if document_name:
            doc_key = document_name.replace(" ", "_").replace(".", "_")
            if analysis_type:
                pattern = f"{self.analysis_prefix}:{analysis_type}:{doc_key}:*"
            else:
                pattern = f"{self.analysis_prefix}:*:{doc_key}:*"

        return sorted(self.redis_client.keys(pattern))

    def get_latest_state(
        self, document_name: str = None, session_id: str = None
    ) -> Optional[str]:
        """Get the most recent state key for a document/session"""
        keys = self.list_states(document_name, session_id)
        return keys[-1] if keys else None

    def get_latest_analysis(
        self, document_name: str = None, analysis_type: str = None
    ) -> Optional[str]:
        """Get the most recent analysis key for a document/type"""
        keys = self.list_analyses(document_name, analysis_type)
        return keys[-1] if keys else None

    def delete_state(self, state_key: str) -> bool:
        """Delete a state entry"""
        result = self.redis_client.delete(state_key)
        self._remove_from_metadata_index(state_key)
        return bool(result)

    def delete_analysis(self, analysis_key: str) -> bool:
        """Delete an analysis entry"""
        return self.delete_state(analysis_key)  # Same logic

    def clear_all_states(self, document_name: str = None) -> int:
        """Clear all states, optionally filtered by document"""
        keys = self.list_states(document_name)
        count = 0
        for key in keys:
            if self.delete_state(key):
                count += 1
        return count

    def clear_all_analyses(self, document_name: str = None) -> int:
        """Clear all analyses, optionally filtered by document"""
        keys = self.list_analyses(document_name)
        count = 0
        for key in keys:
            if self.delete_analysis(key):
                count += 1
        return count

    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get a summary of all cached data"""
        state_keys = self.list_states()
        analysis_keys = self.list_analyses()

        return {
            "total_states": len(state_keys),
            "total_analyses": len(analysis_keys),
            "state_keys": state_keys[:10],  # Show first 10
            "analysis_keys": analysis_keys[:10],  # Show first 10
            "documents": list(
                set(self._extract_document_names(state_keys + analysis_keys))
            ),
        }

    def _update_metadata_index(self, key: str, metadata: Dict[str, Any]):
        """Update metadata index for easy searching"""
        metadata_key = f"{self.metadata_prefix}:{key}"
        self.redis_client.set(
            metadata_key, json.dumps(metadata), ex=86400
        )  # 24 hour expiry

    def _remove_from_metadata_index(self, key: str):
        """Remove entry from metadata index"""
        metadata_key = f"{self.metadata_prefix}:{key}"
        self.redis_client.delete(metadata_key)

    def _extract_document_names(self, keys: List[str]) -> List[str]:
        """Extract document names from keys"""
        documents = []
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 3:
                # Extract document name (usually the 3rd part)
                doc_part = parts[2]
                if (
                    not doc_part.isdigit() and len(doc_part) > 8
                ):  # Not timestamp or UUID
                    documents.append(doc_part.replace("_", " "))
        return documents

    def update_state(self, state_data: Dict[str, Any], state_key: str = None) -> str:
        """Update state data in Redis (alias for cache_state)"""
        return self.cache_state(state_data, state_key)
