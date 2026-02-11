import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..schemas.design_state import DesignState, ExecutionStatus


class StateCache:
    """
    Enhanced state cache for storing design state and FreeCAD analysis data in Redis.

    Supports both:
    - DesignState (Pydantic) for multi-agent workflow state
    - Legacy FreeCAD state analysis data (dict-based)
    """

    def __init__(self, redis_client):
        self.redis_client = redis_client
        # Legacy prefixes (preserved for backwards compatibility)
        self.key_prefix = "freecad"
        self.state_prefix = f"{self.key_prefix}:state"
        self.analysis_prefix = f"{self.key_prefix}:analysis"
        self.metadata_prefix = f"{self.key_prefix}:metadata"
        # New DesignState prefix
        self.design_prefix = "design"

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

    def store_state(
        self, state_key: str, state_data: Dict[str, Any], expiration: int = None
    ) -> bool:
        """Store state data in Redis (alias for cache_state)"""
        try:
            self.cache_state(state_data, state_key, expiration=expiration)
            return True
        except Exception:
            return False

    # =========================================================================
    # DesignState Persistence (Pydantic-based)
    # =========================================================================

    def _get_design_state_key(self, request_id: UUID) -> str:
        """Get Redis key for DesignState storage."""
        return f"{self.design_prefix}:{request_id}:state"

    def cache_design_state(
        self,
        design_state: DesignState,
        ttl_seconds: Optional[int] = 86400,  # 24 hours default
    ) -> bool:
        """
        Cache DesignState using Pydantic serialization.

        Args:
            design_state: DesignState object to cache
            ttl_seconds: Expiration time in seconds (default 24h, None for no expiration)

        Returns:
            True if cached successfully
        """
        try:
            key = self._get_design_state_key(design_state.request_id)

            # Serialize using Pydantic's model_dump_json for efficient JSON serialization
            serialized = design_state.model_dump_json()

            # Store with optional TTL
            self.redis_client.set(key, serialized, ex=ttl_seconds)

            # Update index for listing
            index_key = f"{self.design_prefix}:index"
            self.redis_client.hset(
                index_key,
                str(design_state.request_id),
                json.dumps(
                    {
                        "status": design_state.status.value,
                        "created_at": design_state.created_at.isoformat(),
                        "updated_at": design_state.updated_at.isoformat(),
                    }
                ),
            )

            return True
        except Exception as e:
            print(f"Failed to cache DesignState: {e}")
            return False

    def retrieve_design_state(self, request_id: UUID) -> Optional[DesignState]:
        """
        Retrieve DesignState with automatic Pydantic deserialization.

        Args:
            request_id: Design request ID

        Returns:
            DesignState object or None if not found
        """
        try:
            key = self._get_design_state_key(request_id)
            data = self.redis_client.get(key)

            if not data:
                return None

            # Deserialize using Pydantic's model_validate_json
            decoded = data.decode("utf-8") if isinstance(data, bytes) else data
            return DesignState.model_validate_json(decoded)

        except Exception as e:
            print(f"Failed to retrieve DesignState: {e}")
            return None

    def update_design_state(
        self, design_state: DesignState, ttl_seconds: Optional[int] = 86400
    ) -> bool:
        """
        Update existing DesignState (alias for cache_design_state).

        Args:
            design_state: Updated DesignState object
            ttl_seconds: Reset TTL to this value (default 24h)

        Returns:
            True if updated successfully
        """
        # Update timestamp
        design_state.updated_at = datetime.utcnow()
        return self.cache_design_state(design_state, ttl_seconds)

    def delete_design_state(self, request_id: UUID) -> bool:
        """
        Delete DesignState from cache.

        Args:
            request_id: Design request ID

        Returns:
            True if deleted successfully
        """
        try:
            key = self._get_design_state_key(request_id)
            self.redis_client.delete(key)

            # Remove from index
            index_key = f"{self.design_prefix}:index"
            self.redis_client.hdel(index_key, str(request_id))

            return True
        except Exception as e:
            print(f"Failed to delete DesignState: {e}")
            return False

    def list_design_states(
        self, status: Optional[ExecutionStatus] = None
    ) -> List[UUID]:
        """
        List all design request IDs, optionally filtered by status.

        Args:
            status: Filter by execution status (optional)

        Returns:
            List of request IDs
        """
        try:
            index_key = f"{self.design_prefix}:index"
            all_entries = self.redis_client.hgetall(index_key)

            if not all_entries:
                return []

            request_ids = []
            for request_id_str, metadata_str in all_entries.items():
                try:
                    metadata = json.loads(metadata_str)
                    # Filter by status if specified
                    if status is None or metadata.get("status") == status.value:
                        request_ids.append(UUID(request_id_str))
                except Exception:
                    continue

            return request_ids

        except Exception as e:
            print(f"Failed to list design states: {e}")
            return []

    def set_design_ttl(self, request_id: UUID, ttl_seconds: int = 86400) -> bool:
        """
        Set or update TTL for a DesignState.

        Args:
            request_id: Design request ID
            ttl_seconds: Expiration time in seconds (default 24h)

        Returns:
            True if TTL was set
        """
        try:
            key = self._get_design_state_key(request_id)
            return self.redis_client.expire(key, ttl_seconds)
        except Exception as e:
            print(f"Failed to set TTL: {e}")
            return False

    def get_design_ttl(self, request_id: UUID) -> int:
        """
        Get remaining TTL for a DesignState.

        Args:
            request_id: Design request ID

        Returns:
            Seconds remaining, -1 if no expiration, -2 if doesn't exist
        """
        try:
            key = self._get_design_state_key(request_id)
            return self.redis_client.ttl(key)
        except Exception as e:
            print(f"Failed to get TTL: {e}")
            return -2

    def cleanup_completed_designs(self, older_than_hours: int = 24) -> int:
        """
        Cleanup completed designs older than specified hours.

        Args:
            older_than_hours: Delete designs completed more than this many hours ago

        Returns:
            Number of designs deleted
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.utcnow().timestamp() - (older_than_hours * 3600)

            # Get all completed designs
            completed_ids = self.list_design_states(status=ExecutionStatus.COMPLETED)

            for request_id in completed_ids:
                state = self.retrieve_design_state(request_id)
                if state and state.completed_at:
                    if state.completed_at.timestamp() < cutoff_time:
                        if self.delete_design_state(request_id):
                            deleted_count += 1

            return deleted_count

        except Exception as e:
            print(f"Failed to cleanup designs: {e}")
            return 0

    # =========================================================================
    # Legacy FreeCAD State Cache Methods (preserved for backwards compatibility)
    # =========================================================================

