#!/bin/bash

# Enhanced FreeCAD Complex Shape Demo
# This script demonstrates the new complex shape generation capabilities

echo "🏗️  FreeCAD Complex Shape Generation Demo"
echo "=========================================="
echo ""

# Navigate to the project directory
cd /home/vansh5632/DesignEng/freecad-llm-automation

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found, using system Python"
fi

echo ""
echo "🚀 Starting FreeCAD with enhanced complex shape generation..."
echo ""

# Demo commands showcasing complex shape generation
echo -e "help
complex
create a cone and cylinder together
state
create a tower with cone roof
state
build a rocket with fins
state
analyze
gui
exit" | python src/main.py --llm-provider google --llm-api-key AIzaSyDjw_g1kQZAofU-DOsdsCjgkf3_06R2UEk

echo ""
echo "✅ Demo completed!"
echo ""
echo "💡 What was demonstrated:"
echo "   🔧 Multi-step complex shape creation"
echo "   🎯 Automatic detection of complex requests"
echo "   🔄 Sequential execution of operations"
echo "   📊 State analysis after each complex operation"
echo "   🖥️  GUI visualization of created objects"
echo ""
echo "🏗️  Try these complex shape commands:"
echo "   • create a cone and cylinder together"
echo "   • build a tower with cone roof"
echo "   • make a rocket with fins"
echo "   • create complex building structure"
echo "   • make a lighthouse with base and tower"
echo ""
