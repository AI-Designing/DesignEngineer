#!/bin/bash

# Setup script for AI Designer development environment
# This script installs all necessary tools and dependencies for development

set -e  # Exit on any error

echo "🚀 Setting up AI Designer development environment..."

# Check if Python 3.8+ is available
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "❌ Error: Python 3.8+ is required, but found version $python_version"
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

echo "✅ Python version check passed (found $python_version)"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: You're not in a virtual environment."
    echo "It's recommended to create and activate a virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Upgrade pip
echo "📦 Upgrading pip..."
python3 -m pip install --upgrade pip

# Install the package in development mode with dev dependencies
echo "📦 Installing development dependencies..."
pip install -e ".[dev]"

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

echo "🔧 Setting up pre-commit hooks for commit messages..."
pre-commit install --hook-type commit-msg

# Run initial pre-commit check
echo "🧹 Running initial code quality check..."
if pre-commit run --all-files; then
    echo "✅ All pre-commit checks passed!"
else
    echo "⚠️  Some pre-commit checks failed. This is normal for first-time setup."
    echo "The issues have been automatically fixed where possible."
    echo "Please review the changes and commit them."
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Available commands:"
echo "  make help          - Show all available make targets"
echo "  make dev           - Quick development workflow (format + lint + test)"
echo "  make test          - Run tests"
echo "  make lint          - Run linting tools"
echo "  make format        - Format code"
echo "  make security      - Run security checks"
echo ""
echo "Git hooks are now installed and will run automatically on commit."
echo "To run them manually: pre-commit run --all-files"
echo ""
echo "Happy coding! 🚀"
