.PHONY: install install-dev lint format test test-cov clean security pre-commit build help all

# Default target
all: install-dev lint test

help:
	@echo "Available targets:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  lint          Run all linting tools"
	@echo "  format        Format code with black and isort"
	@echo "  test          Run tests with pytest"
	@echo "  test-cov      Run tests with coverage report"
	@echo "  security      Run security checks"
	@echo "  pre-commit    Run pre-commit hooks on all files"
	@echo "  clean         Clean build artifacts and cache"
	@echo "  build         Build the package"
	@echo "  all           Run install-dev, lint, and test"

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
	@echo "Running tests..."
	pytest -v
	@echo "✓ Tests passed!"

test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=src --cov-report=term-missing --cov-report=html
	@echo "✓ Tests with coverage completed!"
	@echo "Coverage report available in htmlcov/index.html"

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
dev: format lint test

# CI workflow
ci: install-dev lint test-cov security

# Release workflow
release: clean lint test-cov security build
