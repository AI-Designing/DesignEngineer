#!/usr/bin/env python3
"""
FreeCAD State Analysis Tool

This script provides comprehensive analysis of FreeCAD documents,
checking for various design readiness indicators.
"""
import sys
import os
import argparse

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from freecad.api_client import FreeCADAPIClient
from freecad.state_manager import FreeCADStateAnalyzer

def analyze_file(file_path, verbose=False):
    """Analyze a specific FreeCAD file"""
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return False
    
    print(f"🔍 Analyzing FreeCAD file: {file_path}")
    print("=" * 60)
    
    try:
        # Initialize API client and analyzer
        api_client = FreeCADAPIClient(use_headless=True)
        if not api_client.connect():
            print("❌ Error: Failed to connect to FreeCAD")
            return False
        
        analyzer = FreeCADStateAnalyzer(api_client)
        
        # Perform analysis
        analysis = analyzer.analyze_document_state(file_path)
        
        if "error" in analysis:
            print(f"❌ Analysis Error: {analysis['error']}")
            return False
        
        # Print results
        analyzer.print_analysis_results(analysis)
        
        if verbose and "objects" in analysis:
            print(f"\n🔧 Detailed Object Information:")
            print("-" * 40)
            for obj in analysis["objects"]:
                print(f"  📦 {obj['name']}")
                print(f"     Type: {obj['type']}")
        
        # Calculate overall readiness score
        if "analysis" in analysis:
            results = analysis["analysis"]
            passed = sum(1 for v in results.values() if v)
            total = len(results)
            score = (passed / total) * 100
            
            print(f"\n📊 Overall Readiness Score: {score:.1f}% ({passed}/{total})")
            
            if score == 100:
                print("🎉 Document is fully ready for production!")
            elif score >= 80:
                print("✅ Document is mostly ready with minor issues")
            elif score >= 60:
                print("⚠️  Document needs attention before production")
            else:
                print("❌ Document requires significant work")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Analyze FreeCAD documents for design readiness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze.py my_design.FCStd
  python analyze.py --verbose my_design.FCStd
  python analyze.py --batch *.FCStd
        """
    )
    
    parser.add_argument('files', nargs='+', help='FreeCAD files to analyze')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Show detailed information')
    parser.add_argument('--batch', action='store_true',
                       help='Batch mode: analyze multiple files')
    
    args = parser.parse_args()
    
    success_count = 0
    total_count = len(args.files)
    
    for i, file_path in enumerate(args.files):
        if total_count > 1:
            print(f"\n[{i+1}/{total_count}] Processing: {file_path}")
        
        if analyze_file(file_path, args.verbose):
            success_count += 1
        
        if i < total_count - 1:  # Not the last file
            print("\n" + "="*60)
    
    # Summary for batch mode
    if total_count > 1:
        print(f"\n📈 Batch Analysis Summary:")
        print(f"   Successfully analyzed: {success_count}/{total_count}")
        print(f"   Success rate: {(success_count/total_count)*100:.1f}%")

if __name__ == "__main__":
    main()
