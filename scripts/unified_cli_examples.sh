#!/bin/bash
"""
Unified LLM CLI Usage Examples
Demonstrates the new integrated system with provider switching
"""

echo "🚀 Unified LLM FreeCAD CLI - Usage Examples"
echo "=========================================="

# Activate virtual environment
source venv/bin/activate

echo ""
echo "1️⃣ AUTO MODE (Recommended) - System auto-selects best provider"
echo "python -m ai_designer.cli --llm-provider auto --command \"Create a simple cube\""
echo "python -m ai_designer.cli --llm-provider auto --command \"Create complex gear assembly\""

echo ""
echo "2️⃣ DEEPSEEK MODE - Force DeepSeek R1 for complex reasoning"
echo "python -m ai_designer.cli --llm-provider deepseek --command \"Design innovative bracket\""
echo "python -m ai_designer.cli --llm-provider deepseek --llm-mode creative --command \"Create artistic sculpture\""

echo ""
echo "3️⃣ GOOGLE GEMINI MODE - Force Google Gemini for fast responses"
echo "python -m ai_designer.cli --llm-provider google --command \"Create box 10x20x30\""
echo "python -m ai_designer.cli --llm-provider google --llm-mode fast --command \"Create simple cylinder\""

echo ""
echo "4️⃣ INTERACTIVE MODE with Provider Switching"
echo "python -m ai_designer.cli --llm-provider auto"
echo "# Then use these commands in interactive mode:"
echo "#   llm-status                    # Show current provider status"
echo "#   switch-provider deepseek      # Switch to DeepSeek R1"
echo "#   switch-provider google        # Switch to Google Gemini"
echo "#   switch-provider auto          # Enable auto-selection"
echo "#   unified create complex gear   # Use unified manager"
echo "#   unified create box --mode fast # Force fast mode"

echo ""
echo "5️⃣ DIFFERENT GENERATION MODES"
echo "python -m ai_designer.cli --llm-provider auto --llm-mode fast --command \"Create sphere\""
echo "python -m ai_designer.cli --llm-provider auto --llm-mode complex --command \"Design gear\""
echo "python -m ai_designer.cli --llm-provider auto --llm-mode creative --command \"Create artistic shape\""
echo "python -m ai_designer.cli --llm-provider auto --llm-mode technical --command \"Precision part\""

echo ""
echo "6️⃣ LEGACY DEEPSEEK COMMANDS (Still supported)"
echo "python -m ai_designer.cli --deepseek-enabled --command \"Create complex mechanical part\""

echo ""
echo "💡 AUTOMATIC PROVIDER SELECTION LOGIC:"
echo "   • Simple commands (box, sphere, cylinder) → Google Gemini (fast)"
echo "   • Complex commands (gear, assembly, analysis) → DeepSeek R1 (reasoning)"
echo "   • Creative requests → DeepSeek R1 creative mode"
echo "   • Technical precision → DeepSeek R1 technical mode"
echo "   • Fast mode requests → Google Gemini"
echo "   • Complex mode requests → DeepSeek R1"

echo ""
echo "🔧 TESTING THE SYSTEM:"
echo "1. Test auto-selection:"
echo "   python -m ai_designer.cli --llm-provider auto --command \"Create simple box\""
echo ""
echo "2. Test provider switching:"
echo "   python -m ai_designer.cli --llm-provider auto"
echo "   # In interactive mode: switch-provider deepseek"
echo ""
echo "3. Test unified commands:"
echo "   python -m ai_designer.cli --llm-provider auto"
echo "   # In interactive mode: unified create complex gear --mode reasoning"

echo ""
echo "📊 MONITORING AND STATUS:"
echo "   • Use 'llm-status' in interactive mode to see provider status"
echo "   • View performance metrics and success rates"
echo "   • Check which provider was used for each request"
