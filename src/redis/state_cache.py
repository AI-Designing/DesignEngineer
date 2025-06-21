class StateCache:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def cache_state(self, state_key, state_data):
        self.redis_client.set(state_key, state_data)

    def retrieve_state(self, state_key):
        return self.redis_client.get(state_key)