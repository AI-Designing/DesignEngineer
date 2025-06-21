import sys
from llm.client import LLMClient
from freecad.api_client import FreeCADAPIClient
from freecad.command_executor import CommandExecutor
from redis.client import RedisClient
from redis.state_cache import StateCache
from parsers.command_parser import CommandParser

def main():
    llm_client = LLMClient()
    freecad_client = FreeCADAPIClient()
    redis_client = RedisClient()
    command_executor = CommandExecutor()
    state_cache = StateCache()
    command_parser = CommandParser()

    # Connect to Redis
    redis_client.connect()

    # Connect to FreeCAD
    freecad_client.connect()

    while True:
        user_input = input("Enter your command: ")
        
        # Parse the command
        parsed_command = command_parser.parse(user_input)
        
        # Execute the command
        if command_executor.validate_command(parsed_command):
            command_executor.execute(parsed_command)
            current_state = command_executor.get_state()
            state_cache.cache_state(current_state)
        else:
            print("Invalid command. Please try again.")

if __name__ == "__main__":
    main()