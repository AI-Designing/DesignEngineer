import json

class StateCache:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.default_state_key = "freecad_state"

    def cache_state(self, state_data, state_key=None):
        """Cache state data in Redis"""
        key = state_key or self.default_state_key
        
        # Serialize the state data to JSON
        serialized_data = json.dumps(state_data)
        self.redis_client.set(key, serialized_data)

    def retrieve_state(self, state_key=None):
        """Retrieve state data from Redis"""
        key = state_key or self.default_state_key
        
        data = self.redis_client.get(key)
        if data:
            # Deserialize the JSON data
            return json.loads(data.decode('utf-8') if isinstance(data, bytes) else data)
        return None

    def clear_state(self, state_key=None):
        """Clear state data from Redis"""
        key = state_key or self.default_state_key
        self.redis_client.delete(key)