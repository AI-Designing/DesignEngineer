class StateManager:
    def __init__(self):
        self.current_state = {}

    def get_state(self):
        return self.current_state

    def update_state(self, new_state):
        self.current_state.update(new_state)