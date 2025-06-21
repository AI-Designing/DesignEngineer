class PromptTemplates:
    @staticmethod
    def format_command(command):
        return f"Execute the following command in FreeCAD: {command}"

    @staticmethod
    def format_state_request(state):
        return f"Current state of FreeCAD: {state}"

    @staticmethod
    def format_feedback(feedback):
        return f"User feedback: {feedback}"