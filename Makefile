.PHONY: install install-dev lint format test test-unit test-integration test-cov test-coverage clean security pre-commit build help all

# Default target
all: install-dev lint test

help:
	@echo "Available targets:"
	@echo "  install           Install production dependencies"
	@echo "  install-dev       Install development dependencies"
	@echo "  lint              Run all linting tools"
	@echo "  format            Format code with black and isort"
	@echo "  test              Run all tests (unit + integration)"
	@echo "  test-unit         Run unit tests only (fast, no infrastructure)"
	@echo "  test-integration  Run integration tests only (requires Redis)"
	@echo "  test-cov          Run tests with coverage report"
	@echo "  test-coverage     Alias for test-cov"
	@echo "  security          Run security checks"
	@echo "  pre-commit        Run pre-commit hooks on all files"
	@echo "  clean             Clean build artifacts and cache"
	@echo "  build             Build the package"
	@echo "  all               Run install-dev, lint, and test"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

lint:
	@echo "Running code quality checks..."
	flake8 src/ tests/ examples/
	pylint src/
	mypy src/
	@echo "✓ All linting checks passed!"

format:
	@echo "Formatting code..."
	black src/ tests/ examples/
	isort src/ tests/ examples/
	@echo "✓ Code formatted!"

test:
	@echo "Running all tests..."
	PYTHONPATH="" ./venv/bin/pytest -v
	@echo "✓ All tests passed!"

test-unit:
	@echo "Running unit tests (fast, no infrastructure required)..."
	PYTHONPATH="" ./venv/bin/pytest tests/unit/ -v -m "not integration" --ignore=tests/unit/test_sandbox.py
	@echo "✓ Unit tests passed!"

test-integration:
	@echo "Running integration tests (requires Redis)..."
	PYTHONPATH="" ./venv/bin/pytest tests/integration/ -v -m "integration or not integration"
	@echo "✓ Integration tests passed!"
	@echo "Note: Ensure Redis is running for integration tests"

test-cov:
	@echo "Running tests with coverage..."
	PYTHONPATH="" ./venv/bin/pytest --cov=src/ai_designer --cov-report=term-missing --cov-report=html --cov-fail-under=80
	@echo "✓ Tests with coverage completed!"
	@echo "Coverage report available in htmlcov/index.html"
	@echo "Coverage threshold: 80%"

test-coverage: test-cov

security:
	@echo "Running security checks..."
	bandit -r src/
	safety check
	@echo "✓ Security checks passed!"

pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files
	@echo "✓ Pre-commit hooks passed!"

clean:
	@echo "Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Cleanup completed!"

build: clean
	@echo "Building package..."
	python -m build
	@echo "✓ Package built successfully!"

# Quick development workflow
dev: format lint test-unit

# CI workflow
ci: install-dev lint test-coverage security

# Release workflow
release: clean lint test-cov security build
