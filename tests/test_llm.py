import unittest
from ai_designer.llm.client import LLMClient

class TestLLMClient(unittest.TestCase):

    def setUp(self):
        self.llm_client = LLMClient()

    def test_send_command(self):
        command = "Create a new document"
        response = self.llm_client.send_command(command)
        self.assertIsNotNone(response)
        self.assertIn("success", response.lower())

    def test_receive_response(self):
        response = "Document created successfully."
        processed_response = self.llm_client.receive_response(response)
        self.assertEqual(processed_response, "Document created successfully.")

    def test_invalid_command(self):
        command = "Invalid command"
        response = self.llm_client.send_command(command)
        self.assertIsNotNone(response)
        self.assertIn("error", response.lower())

if __name__ == '__main__':
    unittest.main()