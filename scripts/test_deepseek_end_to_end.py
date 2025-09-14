#!/usr/bin/env python3
"""
End-to-End DeepSeek R1 Testing CLI
Tests the complete system: DeepSeek R1 local model → FreeCAD complex drawing generation
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import system components
try:
    from ai_designer.cli import FreeCADCLI
    from ai_designer.core.enhanced_complex_generator import (
        EnhancedComplexShapeGenerator,
    )
    from ai_designer.freecad.api_client import FreeCADAPIClient
    from ai_designer.llm.deepseek_client import (
        DeepSeekConfig,
        DeepSeekMode,
        DeepSeekR1Client,
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DeepSeekEndToEndTester:
    """End-to-end testing for DeepSeek R1 integration"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results = []
        self.start_time = time.time()

    def log(self, message: str, level: str = "info"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "error":
            print(f"🔴 [{timestamp}] {message}")
            logger.error(message)
        elif level == "warning":
            print(f"🟡 [{timestamp}] {message}")
            logger.warning(message)
        elif level == "success":
            print(f"🟢 [{timestamp}] {message}")
            logger.info(message)
        else:
            print(f"ℹ️  [{timestamp}] {message}")
            logger.info(message)

    def check_deepseek_server(self) -> bool:
        """Check if DeepSeek R1 server is running"""
        self.log("🔍 Checking DeepSeek R1 server connection...")

        try:
            import requests

            # Try different possible endpoints
            possible_endpoints = [
                "http://localhost:8000/health",
                "http://localhost:11434/api/tags",  # Ollama default
                "http://localhost:8080/health",
                "http://localhost:3000/health",
            ]

            for endpoint in possible_endpoints:
                try:
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        self.log(f"✅ DeepSeek R1 server found at {endpoint}", "success")
                        return True
                except (requests.exceptions.RequestException, OSError):
                    # Connection failed, try next endpoint
                    continue

            self.log("❌ No DeepSeek R1 server found on common ports", "error")
            self.log(
                "💡 Try starting the server with: ./scripts/setup_deepseek_r1.sh", "info"
            )
            return False

        except ImportError:
            self.log(
                "❌ 'requests' library not found. Install with: pip install requests",
                "error",
            )
            return False

    def test_deepseek_client_direct(self) -> bool:
        """Test DeepSeek client direct API call"""
        self.log("🧪 Testing DeepSeek R1 client direct API...")

        try:
            # Configure DeepSeek client
            config = DeepSeekConfig(
                host="localhost",
                port=8000,
                model_name="deepseek-r1:14b",
                timeout=120,
                reasoning_enabled=True,
            )

            client = DeepSeekR1Client(config)

            # Test simple request
            test_prompt = "Create a simple cube with 10mm dimensions"

            self.log(f"📤 Sending test request: '{test_prompt}'")
            response = client.generate_complex_part(
                requirements=test_prompt,
                mode=DeepSeekMode.FAST,
            )

            if response.status == "success":
                self.log("✅ DeepSeek R1 direct API test passed", "success")
                self.log(f"📊 Confidence: {response.confidence_score:.2f}")
                self.log(f"⏱️  Response time: {response.execution_time:.2f}s")
                if self.verbose and response.generated_code:
                    self.log("📝 Generated code preview:")
                    print(
                        response.generated_code[:200] + "..."
                        if len(response.generated_code) > 200
                        else response.generated_code
                    )
                return True
            else:
                self.log(
                    f"❌ DeepSeek R1 direct API test failed: {response.error_message}",
                    "error",
                )
                return False

        except Exception as e:
            self.log(f"❌ DeepSeek R1 client test error: {e}", "error")
            return False

    def test_complex_drawing_generation(self) -> bool:
        """Test complex drawing generation through the full system"""
        self.log("🎨 Testing complex drawing generation...")

        test_cases = [
            {
                "name": "Precision Shaft",
                "prompt": "Create a precision shaft with 100mm length, 20mm diameter, and 5mm keyway",
                "mode": DeepSeekMode.TECHNICAL,
                "expected_elements": ["shaft", "keyway", "cylinder"],
            },
            {
                "name": "Gear Assembly",
                "prompt": "Design a gear assembly with 20 teeth main gear and 10 teeth pinion",
                "mode": DeepSeekMode.REASONING,
                "expected_elements": ["gear", "teeth", "pinion"],
            },
            {
                "name": "Creative Phone Stand",
                "prompt": "Design an innovative adjustable phone stand with cable management",
                "mode": DeepSeekMode.CREATIVE,
                "expected_elements": ["stand", "adjustable", "phone"],
            },
        ]

        passed_tests = 0

        for i, test_case in enumerate(test_cases, 1):
            self.log(f"📋 Test {i}/3: {test_case['name']}")

            try:
                # Use CLI with DeepSeek enabled
                cli = FreeCADCLI(
                    deepseek_enabled=True,
                    deepseek_mode=test_case["mode"].value,
                    gui_mode=False,  # Headless for testing
                )

                # Execute the command
                self.log(f"🚀 Executing: '{test_case['prompt']}'")
                success = cli.execute_deepseek_command(test_case["prompt"])

                if success:
                    self.log(
                        f"✅ {test_case['name']} - Generation successful", "success"
                    )
                    passed_tests += 1
                else:
                    self.log(f"❌ {test_case['name']} - Generation failed", "error")

            except Exception as e:
                self.log(f"❌ {test_case['name']} - Error: {e}", "error")

            # Small delay between tests
            time.sleep(2)

        success_rate = passed_tests / len(test_cases)
        if success_rate >= 0.8:
            self.log(
                f"✅ Complex drawing tests passed: {passed_tests}/{len(test_cases)}",
                "success",
            )
            return True
        else:
            self.log(
                f"❌ Complex drawing tests insufficient: {passed_tests}/{len(test_cases)}",
                "error",
            )
            return False

    def test_freecad_integration(self) -> bool:
        """Test FreeCAD integration and output"""
        self.log("🔧 Testing FreeCAD integration...")

        try:
            # Check if FreeCAD is available
            result = subprocess.run(
                ["python", "-c", "import FreeCAD; print('FreeCAD available')"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self.log("✅ FreeCAD Python module available", "success")
                return True
            else:
                self.log("❌ FreeCAD Python module not available", "error")
                self.log("💡 Install FreeCAD: sudo apt install freecad-python3", "info")
                return False

        except subprocess.TimeoutExpired:
            self.log("❌ FreeCAD test timed out", "error")
            return False
        except Exception as e:
            self.log(f"❌ FreeCAD test error: {e}", "error")
            return False

    def detect_and_report_mocks(self) -> List[str]:
        """Detect any mock implementations in the system"""
        self.log("🔍 Scanning for mock implementations...")

        mock_files = []
        mock_patterns = [
            ("Mock", "Mock classes or functions"),
            ("mock", "Mock usage"),
            ("TODO", "TODO items that might indicate incomplete implementations"),
            ("FIXME", "FIXME items"),
            ("demo_mode", "Demo mode flags"),
            ("test_mode", "Test mode flags"),
        ]

        search_paths = [
            "src/ai_designer",
            "scripts",
            "examples",
        ]

        for search_path in search_paths:
            full_path = Path(__file__).parent.parent / search_path
            if full_path.exists():
                for py_file in full_path.rglob("*.py"):
                    try:
                        content = py_file.read_text()
                        for pattern, description in mock_patterns:
                            if pattern in content:
                                mock_files.append(f"{py_file}: {description}")
                                if self.verbose:
                                    lines = content.split("\n")
                                    for i, line in enumerate(lines, 1):
                                        if pattern in line:
                                            self.log(f"   Line {i}: {line.strip()}")
                    except (OSError, UnicodeDecodeError, PermissionError):
                        # File read error, skip this file
                        continue

        if mock_files:
            self.log(
                f"⚠️  Found {len(mock_files)} files with potential mock implementations:",
                "warning",
            )
            for mock_file in mock_files[:10]:  # Show first 10
                self.log(f"   📄 {mock_file}")
            if len(mock_files) > 10:
                self.log(f"   ... and {len(mock_files) - 10} more")
        else:
            self.log("✅ No obvious mock implementations found", "success")

        return mock_files

    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive end-to-end test"""
        self.log("🚀 Starting DeepSeek R1 End-to-End Testing")
        self.log("=" * 60)

        results = {
            "server_connection": False,
            "direct_api": False,
            "complex_generation": False,
            "freecad_integration": False,
            "mock_files": [],
            "overall_success": False,
            "execution_time": 0,
        }

        # Test 1: Server Connection
        results["server_connection"] = self.check_deepseek_server()

        # Test 2: Direct API (if server is running)
        if results["server_connection"]:
            results["direct_api"] = self.test_deepseek_client_direct()

        # Test 3: Complex Generation (if API works)
        if results["direct_api"]:
            results["complex_generation"] = self.test_complex_drawing_generation()

        # Test 4: FreeCAD Integration
        results["freecad_integration"] = self.test_freecad_integration()

        # Test 5: Mock Detection
        results["mock_files"] = self.detect_and_report_mocks()

        # Overall result
        core_tests_passed = (
            results["server_connection"]
            and results["direct_api"]
            and results["complex_generation"]
            and results["freecad_integration"]
        )

        results["overall_success"] = core_tests_passed
        results["execution_time"] = time.time() - self.start_time

        # Final report
        self.log("=" * 60)
        self.log("📊 FINAL TEST REPORT")
        self.log("=" * 60)

        status_emoji = "✅" if results["overall_success"] else "❌"
        self.log(
            f"{status_emoji} Overall Status: {'PASSED' if results['overall_success'] else 'FAILED'}"
        )
        self.log(f"⏱️  Total Execution Time: {results['execution_time']:.2f}s")

        self.log("\n📋 Individual Test Results:")
        for test_name, passed in results.items():
            if test_name in ["overall_success", "execution_time", "mock_files"]:
                continue
            emoji = "✅" if passed else "❌"
            self.log(
                f"   {emoji} {test_name.replace('_', ' ').title()}: {'PASS' if passed else 'FAIL'}"
            )

        if results["mock_files"]:
            self.log(f"\n⚠️  Mock Files Found: {len(results['mock_files'])}")
            self.log(
                "💡 Consider reviewing and removing these mock implementations for production use"
            )

        return results


def main():
    parser = argparse.ArgumentParser(description="End-to-End DeepSeek R1 Testing CLI")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed logs",
    )
    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Run quick tests only (skip complex generation)",
    )
    parser.add_argument("--report-file", help="Save test report to JSON file")

    args = parser.parse_args()

    # Create tester
    tester = DeepSeekEndToEndTester(verbose=args.verbose)

    try:
        if args.quick:
            tester.log("🏃 Running quick tests only...")
            results = {
                "server_connection": tester.check_deepseek_server(),
                "freecad_integration": tester.test_freecad_integration(),
                "mock_files": tester.detect_and_report_mocks(),
            }
            results["overall_success"] = (
                results["server_connection"] and results["freecad_integration"]
            )
        else:
            results = tester.run_comprehensive_test()

        # Save report if requested
        if args.report_file:
            with open(args.report_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
            tester.log(f"📄 Test report saved to {args.report_file}")

        # Exit with appropriate code
        sys.exit(0 if results["overall_success"] else 1)

    except KeyboardInterrupt:
        tester.log("\n⏹️  Test interrupted by user", "warning")
        sys.exit(130)
    except Exception as e:
        tester.log(f"💥 Unexpected error: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
