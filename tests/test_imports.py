#!/usr/bin/env python3
"""
Simple test to check imports and identify issues
"""

import os
import sys

print("🔍 Starting import diagnostics...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
print(f"Adding to path: {os.path.abspath(src_path)}")
sys.path.insert(0, src_path)

try:
    print("🧪 Testing basic imports...")

    print("  - Importing time...")
    import time

    print("  ✅ time imported")

    print("  - Importing redis...")
    import redis

    print("  ✅ redis imported")

    print("  - Importing requests...")
    import requests

    print("  ✅ requests imported")

    print("  - Importing unified_manager...")
    from ai_designer.llm.unified_manager import LLMProvider, UnifiedLLMManager

    print("  ✅ unified_manager imported")

    print("  - Testing Redis connection...")
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        print("  ✅ Redis connection successful")
    except Exception as redis_error:
        print(f"  ⚠️ Redis connection failed: {redis_error}")

    print("  - Importing FreeCAD CLI...")
    from ai_designer.cli import FreeCADCLI

    print("  ✅ CLI imported")

    print("\n🎉 All basic imports successful!")

except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback

    traceback.print_exc()
