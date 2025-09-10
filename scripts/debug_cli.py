#!/usr/bin/env python3
"""
Quick test script to check CLI initialization issues
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    print("🔍 Testing imports...")
    from ai_designer.llm.unified_manager import (
        GenerationMode,
        LLMProvider,
        LLMRequest,
        UnifiedLLMManager,
    )

    print("✅ Unified manager imports successful")

    from ai_designer.cli import FreeCADCLI

    print("✅ CLI import successful")

    print("\n🔍 Testing CLI initialization...")
    cli = FreeCADCLI(
        use_headless=True,
        llm_provider="deepseek",
        enable_websocket=False,
        enable_persistent_gui=False,
        deepseek_enabled=True,
    )
    print("✅ CLI object created")

    print("\n🔍 Testing basic initialization...")
    success = cli.initialize()
    print(f"✅ CLI initialization: {'Success' if success else 'Failed'}")

    if cli.unified_llm_manager:
        status = cli.unified_llm_manager.get_provider_status()
        print(f"✅ Provider status: {status['active_provider']}")

        for provider, info in status["providers"].items():
            status_icon = "✅" if info["available"] else "❌"
            print(f"   {status_icon} {provider}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
