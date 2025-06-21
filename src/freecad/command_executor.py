class CommandExecutor:
    def __init__(self, api_client, state_manager):
        self.api_client = api_client
        self.state_manager = state_manager

    def execute(self, command):
        if self.validate_command(command):
            response = self.api_client.execute_command(command)
            self.state_manager.update_state(response)
            return response
        else:
            raise ValueError("Invalid command")

    def validate_command(self, command):
        # Implement command validation logic here
        return True  # Placeholder for actual validation logic