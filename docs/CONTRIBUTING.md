# Contributing to AI Designer

Thank you for your interest in contributing to AI Designer! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/ai-designing-designengineer.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install in development mode: `pip install -e .[dev]`

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use Black for code formatting: `black src/ tests/`
- Run linting with flake8: `flake8 src/ tests/`
- Type hints are encouraged: `mypy src/`

### Testing

- Write tests for new features
- Run tests with pytest: `pytest`
- Maintain test coverage above 80%

### Documentation

- Update docstrings for new functions and classes
- Update README.md if adding new features
- Add examples in the `examples/` directory

## Submitting Changes

1. Create a feature branch: `git checkout -b feature-name`
2. Make your changes
3. Write or update tests
4. Ensure all tests pass: `pytest`
5. Format code: `black src/ tests/`
6. Commit your changes: `git commit -m "Add feature description"`
7. Push to your fork: `git push origin feature-name`
8. Submit a pull request

## Pull Request Guidelines

- Provide a clear description of changes
- Reference any related issues
- Include tests for new functionality
- Update documentation as needed
- Ensure CI checks pass

## Reporting Issues

- Use the GitHub issue tracker
- Include Python version, OS, and FreeCAD version
- Provide a minimal reproducible example
- Include error messages and stack traces

## Development Setup

### Prerequisites

- Python 3.8+
- FreeCAD 0.19+
- Redis (for enhanced features)

### Environment Variables

For development, you may need to set:
- `OPENAI_API_KEY` or `GOOGLE_API_KEY`
- `REDIS_URL` (if using Redis features)

## Questions?

Feel free to open an issue for questions or join our discussions.

Thank you for contributing!
