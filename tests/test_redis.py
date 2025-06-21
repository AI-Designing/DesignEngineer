import unittest
from src.redis.client import RedisClient
from src.redis.state_cache import StateCache

class TestStateCache(unittest.TestCase):
    def setUp(self):
        self.redis_client = RedisClient()
        self.state_cache = StateCache(self.redis_client)

    def test_cache_state(self):
        state = {'key': 'value'}
        self.state_cache.cache_state(state)
        cached_state = self.state_cache.retrieve_state()
        self.assertEqual(state, cached_state)

    def test_retrieve_state_empty(self):
        cached_state = self.state_cache.retrieve_state()
        self.assertIsNone(cached_state)

if __name__ == '__main__':
    unittest.main()