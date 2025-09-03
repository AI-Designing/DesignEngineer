# Contributing to AI Designer

Thank you for your interest in contributing to AI Designer! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Quick Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd freecad-llm-automation
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Run the automated setup script:
```bash
./scripts/setup-dev.sh
```

### Manual Setup

If you prefer to set up manually:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run initial checks
make dev
```

## Development Workflow

### Code Quality Standards

We maintain high code quality standards using several tools:

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting
- **flake8**: Linting and style checking
- **mypy**: Static type checking
- **pylint**: Advanced linting
- **bandit**: Security vulnerability scanning
- **pytest**: Testing framework

### Development Commands

Use the Makefile for common development tasks:

```bash
# Show all available commands
make help

# Quick development workflow
make dev              # format + lint + test

# Individual commands
make format           # Format code with black and isort
make lint             # Run all linting tools
make test             # Run tests
make test-cov         # Run tests with coverage
make security         # Run security checks
make pre-commit       # Run pre-commit hooks
make clean            # Clean build artifacts
```

### Pre-commit Hooks

Pre-commit hooks are automatically installed and will run on every commit. They include:

- Trailing whitespace removal
- End-of-file fixing
- YAML/JSON/TOML validation
- Code formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)

To run pre-commit hooks manually:
```bash
pre-commit run --all-files
```

### Code Style Guidelines

#### Python Code Style

1. **Formatting**: Use Black with 88 character line length
2. **Imports**: Use isort with Black profile
3. **Type Hints**: All functions should have type hints
4. **Docstrings**: Use Google-style docstrings
5. **Naming**: Follow PEP 8 conventions

#### Example Function

```python
def process_cad_data(
    file_path: str,
    options: Dict[str, Any],
    *,
    validate: bool = True
) -> ProcessingResult:
    """Process CAD data from the specified file.

    Args:
        file_path: Path to the CAD file to process.
        options: Processing options and parameters.
        validate: Whether to validate input data.

    Returns:
        ProcessingResult containing the processed data.

    Raises:
        FileNotFoundError: If the specified file doesn't exist.
        ValidationError: If validation fails and validate=True.
    """
    # Implementation here
    pass
```

### Testing

#### Writing Tests

- Place tests in the `tests/` directory
- Use pytest as the testing framework
- Follow the naming convention: `test_*.py`
- Write both unit tests and integration tests
- Aim for high test coverage (>80%)

#### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_specific_module.py

# Run tests matching a pattern
pytest -k "test_cad_processing"
```

### Security

#### Security Checks

We use several tools to ensure code security:

- **bandit**: Scans for common security issues
- **safety**: Checks for known vulnerabilities in dependencies

#### Security Guidelines

1. Never commit sensitive data (API keys, passwords)
2. Use environment variables for configuration
3. Validate all user inputs
4. Follow secure coding practices
5. Regularly update dependencies

### Documentation

#### Code Documentation

- All public functions/classes must have docstrings
- Use Google-style docstrings
- Include type hints for all parameters and return values
- Add examples for complex functions

#### Project Documentation

- Update README.md for user-facing changes
- Update this CONTRIBUTING.md for development process changes
- Document new features in appropriate files

### Submitting Changes

#### Pull Request Process

1. **Create a Feature Branch**:
```bash
git checkout -b feature/your-feature-name
```

2. **Make Changes**:
   - Write code following our style guidelines
   - Add/update tests as needed
   - Update documentation

3. **Run Quality Checks**:
```bash
make dev  # This runs format, lint, and test
```

4. **Commit Changes**:
```bash
git add .
git commit -m "feat: add new CAD processing feature"
```

5. **Push and Create PR**:
```bash
git push origin feature/your-feature-name
```

#### Commit Message Guidelines

Follow conventional commits format:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes (no logic changes)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Examples:
```
feat: add support for STEP file processing
fix: resolve memory leak in CAD parser
docs: update API documentation for new endpoints
test: add integration tests for file processing
```

### Code Review

#### Review Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Security considerations addressed
- [ ] Performance implications considered
- [ ] Breaking changes documented

#### What to Look For

1. **Correctness**: Does the code do what it's supposed to do?
2. **Performance**: Are there any performance issues?
3. **Security**: Are there any security vulnerabilities?
4. **Maintainability**: Is the code readable and maintainable?
5. **Testing**: Are there adequate tests?

### Issue Reporting

When reporting issues:

1. Use the issue templates
2. Provide clear reproduction steps
3. Include environment information
4. Add relevant logs or error messages
5. Label appropriately

### Getting Help

- Check existing documentation
- Search existing issues
- Ask questions in discussions
- Reach out to maintainers

## Release Process

### Version Bumping

We follow semantic versioning (SemVer):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped
- [ ] Tagged release
- [ ] Package built and tested

Thank you for contributing to AI Designer! 🚀
