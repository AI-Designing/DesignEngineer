import unittest
from ai_designer.redis_utils.client import RedisClient
from ai_designer.redis_utils.state_cache import StateCache

class TestStateCache(unittest.TestCase):
    def setUp(self):
        self.redis_client = RedisClient()
        # Connect to Redis
        if not self.redis_client.connect():
            self.skipTest("Redis server is not available")
        
        self.state_cache = StateCache(self.redis_client)
        # Clean up any existing test data
        self.cleanup_test_data()

    def tearDown(self):
        """Clean up test data after each test"""
        self.cleanup_test_data()

    def cleanup_test_data(self):
        """Remove any test keys from Redis"""
        try:
            keys = self.redis_client.keys("freecad:*test*")
            for key in keys:
                self.redis_client.delete(key)
        except:
            pass

    def test_cache_and_retrieve_state(self):
        """Test caching and retrieving state data"""
        state_data = {'key': 'value', 'objects': ['cube', 'sphere'], 'step': 1}
        
        # Cache state with specific parameters
        state_key = self.state_cache.cache_state(
            state_data, 
            document_name="test_document", 
            session_id="test_session"
        )
        
        # Verify key was returned
        self.assertIsNotNone(state_key)
        self.assertIn("freecad:state", state_key)
        
        # Retrieve the cached state
        cached_state = self.state_cache.retrieve_state(state_key)
        self.assertEqual(state_data, cached_state)

    def test_cache_and_retrieve_analysis(self):
        """Test caching and retrieving analysis data"""
        analysis_data = {
            'document_state': 'ready',
            'objects_count': 2,
            'recommendations': ['add constraints', 'create sketch']
        }
        
        # Cache analysis
        analysis_key = self.state_cache.cache_analysis(
            analysis_data,
            document_name="test_document",
            analysis_type="state_analysis"
        )
        
        # Verify key was returned
        self.assertIsNotNone(analysis_key)
        self.assertIn("freecad:analysis", analysis_key)
        
        # Retrieve the cached analysis
        cached_analysis = self.state_cache.retrieve_analysis(analysis_key)
        self.assertEqual(analysis_data, cached_analysis)

    def test_retrieve_nonexistent_state(self):
        """Test retrieving a non-existent state returns None"""
        cached_state = self.state_cache.retrieve_state("nonexistent_key")
        self.assertIsNone(cached_state)

    def test_list_states(self):
        """Test listing cached states"""
        # Cache multiple states
        state1 = {'step': 1, 'action': 'create_cube'}
        state2 = {'step': 2, 'action': 'create_sphere'}
        
        key1 = self.state_cache.cache_state(state1, document_name="test_document", session_id="session1")
        key2 = self.state_cache.cache_state(state2, document_name="test_document", session_id="session2")
        
        # List all states for the test document
        state_keys = self.state_cache.list_states(document_name="test_document")
        
        # Verify both keys are in the list
        self.assertIn(key1, state_keys)
        self.assertIn(key2, state_keys)
        self.assertEqual(len(state_keys), 2)

    def test_redis_connection(self):
        """Test Redis connection is working"""
        # Test basic Redis operations
        test_key = "test_connection_key"
        test_value = "test_value"
        
        # Set and get a simple value
        self.assertTrue(self.redis_client.set(test_key, test_value))
        retrieved_value = self.redis_client.get(test_key)
        
        if isinstance(retrieved_value, bytes):
            retrieved_value = retrieved_value.decode('utf-8')
            
        self.assertEqual(test_value, retrieved_value)
        
        # Clean up
        self.redis_client.delete(test_key)

if __name__ == '__main__':
    unittest.main()