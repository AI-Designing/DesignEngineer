# FreeCAD LLM Automation

This project aims to create a software application that allows users to interact with FreeCAD using natural language commands. By leveraging a Large Language Model (LLM), the application translates user input into executable commands for FreeCAD, maintaining the state of the environment using Redis for low-latency performance.

## Project Structure

```
freecad-llm-automation
├── src
│   ├── main.py                # Entry point of the application
│   ├── llm                    # LLM related functionalities
│   │   ├── client.py          # Handles communication with the LLM
│   │   └── prompt_templates.py # Predefined prompt templates
│   ├── freecad                # FreeCAD API interaction
│   │   ├── api_client.py      # Manages connection to FreeCAD API
│   │   ├── command_executor.py # Executes commands in FreeCAD
│   │   └── state_manager.py    # Maintains the current state of FreeCAD
│   ├── redis                  # Redis database interaction
│   │   ├── client.py          # Manages connection to Redis
│   │   └── state_cache.py     # Caches FreeCAD state in Redis
│   ├── parsers                # Command parsing
│   │   └── command_parser.py   # Parses natural language commands
│   └── utils                  # Utility functions
│       └── helpers.py         # Various helper functions
├── config
│   ├── config.yaml            # Configuration settings
│   └── redis.conf             # Redis server configuration
├── tests                      # Unit tests
│   ├── test_llm.py           # Tests for LLM client
│   ├── test_freecad.py       # Tests for FreeCAD API client
│   └── test_redis.py         # Tests for Redis client
├── requirements.txt           # Project dependencies
├── docker-compose.yml         # Docker configuration
└── README.md                  # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd freecad-llm-automation
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the application by editing `config/config.yaml` and `config/redis.conf` as needed.

## Usage

To run the application, execute the following command:
```
python src/main.py
```

Follow the prompts to input natural language commands for FreeCAD. The application will process the commands and execute them in the FreeCAD environment.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.