#!/bin/bash

# Enhanced FreeCAD LLM Automation System Test Script
# This script helps you test different modes of the enhanced system

echo "🚀 Enhanced FreeCAD LLM Automation System Test"
echo "=============================================="

# Check if API key is provided
if [ -z "$1" ]; then
    echo "❌ Please provide your LLM API key as the first argument"
    echo ""
    echo "Usage: $0 <API_KEY> [mode]"
    echo ""
    echo "Available modes:"
    echo "  demo           - Run predefined demo commands (default)"
    echo "  interactive    - Interactive command input"
    echo "  complex        - Test complex shape generation"
    echo "  single         - Execute a single command"
    echo ""
    echo "Examples:"
    echo "  $0 your-api-key demo"
    echo "  $0 your-api-key interactive"
    echo "  $0 your-api-key complex"
    echo "  $0 your-api-key single"
    exit 1
fi

API_KEY="$1"
MODE="${2:-demo}"

echo "🔑 API Key: ${API_KEY:0:10}..."
echo "🎯 Mode: $MODE"
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

case "$MODE" in
    "demo")
        echo "🎭 Running demo mode with predefined commands..."
        python enhanced_main.py --llm-api-key "$API_KEY" --demo-mode
        ;;

    "interactive")
        echo "💬 Starting interactive mode..."
        echo "You can enter commands like:"
        echo "  - 'create a cone and cylinder together'"
        echo "  - 'make a red cube'"
        echo "  - 'analyze current design'"
        echo "  - 'quit' to exit"
        echo ""
        python enhanced_main.py --llm-api-key "$API_KEY" --interactive
        ;;

    "complex")
        echo "🔧 Testing complex shape generation..."
        python enhanced_main.py --llm-api-key "$API_KEY" --test-complex-shapes
        ;;

    "single")
        echo "⚡ Single command mode - testing cone and cylinder creation..."
        python enhanced_main.py --llm-api-key "$API_KEY" --single-command "create a cone and cylinder together"
        ;;

    *)
        echo "❌ Unknown mode: $MODE"
        echo "Available modes: demo, interactive, complex, single"
        exit 1
        ;;
esac
