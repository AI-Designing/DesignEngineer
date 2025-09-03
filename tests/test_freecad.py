import unittest

from ai_designer.freecad.api_client import FreeCADAPIClient
from ai_designer.freecad.command_executor import CommandExecutor
from ai_designer.freecad.state_manager import StateManager


class TestFreeCADAPIClient(unittest.TestCase):
    def setUp(self):
        self.api_client = FreeCADAPIClient()
        self.command_executor = CommandExecutor()
        self.state_manager = StateManager()

    def test_connect(self):
        self.assertTrue(self.api_client.connect())

    def test_execute_command(self):
        command = "create a box"
        result = self.command_executor.execute(command)
        self.assertIsNotNone(result)

    def test_get_state(self):
        state = self.state_manager.get_state()
        self.assertIsInstance(state, dict)

    def test_update_state(self):
        initial_state = self.state_manager.get_state()
        self.state_manager.update_state({"new_key": "new_value"})
        updated_state = self.state_manager.get_state()
        self.assertNotEqual(initial_state, updated_state)


if __name__ == "__main__":
    unittest.main()
