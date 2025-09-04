#!/usr/bin/env python3
"""
Real-time Generation Monitor
Monitor and display the progress of component generation
"""

import glob
import json
import os
import time
from datetime import datetime
from pathlib import Path


def monitor_generation_progress():
    """Monitor the outputs directory for new generations"""

    print("🔍 Real-time Generation Monitor")
    print("=" * 50)
    print("👁️ Monitoring outputs directory...")
    print("Press Ctrl+C to stop")
    print()

    seen_files = set()
    generation_count = 0

    try:
        while True:
            # Check for new output directories
            output_dirs = list(Path("outputs").glob("*generation_*"))

            for output_dir in output_dirs:
                if output_dir not in seen_files:
                    seen_files.add(output_dir)
                    generation_count += 1

                    print(f"🆕 New Generation Detected: {output_dir.name}")

                    # Check for metadata
                    metadata_file = output_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, "r") as f:
                                metadata = json.load(f)

                            print(
                                f"   📋 Requirements: {metadata.get('requirements', 'N/A')[:80]}..."
                            )
                            print(f"   ⚙️ Mode: {metadata.get('mode', 'N/A')}")
                            print(
                                f"   🎯 Confidence: {metadata.get('confidence_score', 0):.2f}"
                            )
                            print(
                                f"   ⏱️ Time: {metadata.get('generation_time', 0):.1f}s"
                            )
                            print(
                                f"   🧠 Reasoning Steps: {metadata.get('reasoning_steps', 0)}"
                            )

                        except Exception as e:
                            print(f"   ⚠️ Could not read metadata: {e}")

                    # Check for generated files
                    code_files = list(output_dir.glob("*.py"))
                    model_files = list(output_dir.glob("*.FCStd"))
                    step_files = list(output_dir.glob("*.step"))

                    print(
                        f"   📁 Files: {len(code_files)} Python, {len(model_files)} FreeCAD, {len(step_files)} STEP"
                    )
                    print()

            # Display running total
            if generation_count > 0:
                print(f"\\r📊 Total Generations: {generation_count}", end="", flush=True)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\\n\\n🛑 Monitoring stopped")
        print(f"📈 Final Count: {generation_count} generations detected")


def display_generation_summary():
    """Display a summary of all generations"""

    print("\\n📊 Generation Summary")
    print("=" * 30)

    output_dirs = list(Path("outputs").glob("*generation_*"))

    if not output_dirs:
        print("❌ No generations found")
        return

    total_time = 0
    total_confidence = 0
    successful = 0

    for output_dir in sorted(output_dirs):
        metadata_file = output_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                if metadata.get("status") == "success":
                    successful += 1
                    total_time += metadata.get("generation_time", 0)
                    total_confidence += metadata.get("confidence_score", 0)

                print(f"📁 {output_dir.name}")
                print(
                    f"   Status: {'✅' if metadata.get('status') == 'success' else '❌'}"
                )
                print(f"   Confidence: {metadata.get('confidence_score', 0):.2f}")
                print(f"   Time: {metadata.get('generation_time', 0):.1f}s")

            except Exception as e:
                print(f"❌ Error reading {output_dir.name}: {e}")

    if successful > 0:
        avg_time = total_time / successful
        avg_confidence = total_confidence / successful

        print(f"\\n📈 Statistics:")
        print(f"   Total Generations: {len(output_dirs)}")
        print(f"   Successful: {successful}")
        print(f"   Success Rate: {(successful/len(output_dirs)*100):.1f}%")
        print(f"   Average Time: {avg_time:.1f}s")
        print(f"   Average Confidence: {avg_confidence:.2f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        display_generation_summary()
    else:
        try:
            monitor_generation_progress()
        except KeyboardInterrupt:
            pass
        finally:
            display_generation_summary()
