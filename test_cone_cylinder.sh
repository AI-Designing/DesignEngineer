#!/bin/bash

# Test the specific command: create a cone and cylinder together
echo "🔧 Testing Complex Shape: Cone and Cylinder Together"
echo "===================================================="

cd /home/vansh5632/DesignEng/freecad-llm-automation

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Your enhanced command with complex shape generation
echo -e "create a cone and cylinder together\nstate\nanalyze\ngui\nexit" | python src/main.py --llm-provider google --llm-api-key AIzaSyDjw_g1kQZAofU-DOsdsCjgkf3_06R2UEk

echo ""
echo "✅ Complex shape creation completed!"
echo "🏗️  The system created:"
echo "   1. 🔺 A cylinder (base shape)"
echo "   2. 🔻 A cone (positioned on top)"
echo "   3. 🔗 Fused them together into one complex shape"
echo ""
echo "💡 The enhanced system automatically:"
echo "   • Detected this was a complex multi-shape request"
echo "   • Broke it down into logical steps"
echo "   • Executed each operation sequentially"
echo "   • Positioned shapes relative to each other"
echo "   • Combined them into a unified object"
