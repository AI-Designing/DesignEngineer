#!/bin/bash

# FreeCAD Enhanced System Test Script
# This script shows you how to run the enhanced_main.py with different options

echo "🔧 FreeCAD Enhanced System - Test Runner"
echo "========================================="
echo ""

# Set your API key here
API_KEY="AIzaSyDjw_g1kQZAofU-DOsdsCjgkf3_06R2UEk"

# Navigate to project directory
cd /home/vansh5632/DesignEng/freecad-llm-automation

# Activate virtual environment
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found"
fi

echo ""
echo "🧪 Available Test Options:"
echo "=========================="
echo ""

echo "1️⃣  Single Command Test:"
echo "   python examples/run_freecad.py --single-command 'create a cone and cylinder together'"
echo ""

echo "2️⃣  Complex Shape Tests:"
echo "   python enhanced_main.py --llm-api-key $API_KEY --test-complex-shapes"
echo ""

echo "3️⃣  Interactive Mode:"
echo "   python enhanced_main.py --llm-api-key $API_KEY --interactive"
echo ""

echo "4️⃣  Full Demo Mode (default):"
echo "   python enhanced_main.py --llm-api-key $API_KEY"
echo ""

echo "5️⃣  Disable Real-time Features:"
echo "   python enhanced_main.py --llm-api-key $API_KEY --disable-realtime"
echo ""

echo "6️⃣  Custom Configuration:"
echo "   python enhanced_main.py --llm-api-key $API_KEY --websocket-port 8888 --max-concurrent 5"
echo ""

echo "🚀 Choose a test to run:"
echo "========================"
read -p "Enter test number (1-6) or 'q' to quit: " choice

case $choice in
    1)
        echo "🧪 Running single command test..."
        python enhanced_main.py --llm-api-key $API_KEY --single-command "create a cone and cylinder together"
        ;;
    2)
        echo "🏗️  Running complex shape tests..."
        python enhanced_main.py --llm-api-key $API_KEY --test-complex-shapes
        ;;
    3)
        echo "💬 Starting interactive mode..."
        python enhanced_main.py --llm-api-key $API_KEY --interactive
        ;;
    4)
        echo "🎬 Running full demo..."
        python enhanced_main.py --llm-api-key $API_KEY
        ;;
    5)
        echo "🔇 Running without real-time features..."
        python enhanced_main.py --llm-api-key $API_KEY --disable-realtime
        ;;
    6)
        echo "⚙️  Running with custom configuration..."
        python enhanced_main.py --llm-api-key $API_KEY --websocket-port 8888 --max-concurrent 5
        ;;
    q|Q)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. Running default demo..."
        python enhanced_main.py --llm-api-key $API_KEY
        ;;
esac

echo ""
echo "✅ Test completed!"
echo ""
echo "💡 What happened:"
echo "   🧠 The system used Google Gemini LLM with your API key"
echo "   📊 State management tracked all operations"
echo "   ⚡ Commands were processed with full context awareness"
echo "   🌐 Real-time updates were sent via WebSocket (if enabled)"
echo "   🎯 LLM made intelligent decisions based on current state"
echo ""
echo "🔍 To see more details, check the output above!"
