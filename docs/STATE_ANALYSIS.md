# FreeCAD State Analysis

This document explains how to use the FreeCAD state analysis functionality that has been integrated into the system.

## Overview

The state analysis system provides comprehensive analysis of FreeCAD documents, checking for various design readiness indicators including:

- ✅ **Pad Created**: Check if document has Pad objects
- ✅ **Face Available**: Check if faces are available for operations
- ✅ **Active Body**: Check if there's an active PartDesign body
- ✅ **Sketch Plane Ready**: Check if sketches are mapped to planes
- ✅ **Constrained Base Sketch**: Check if sketches are fully constrained
- ✅ **Safe References**: Check external reference integrity
- ✅ **No Errors**: Check for document errors

## Usage

### Interactive Mode

Start the interactive CLI:
```bash
python src/main.py
```

Available analysis commands:
- `analyze` - Analyze current document
- `analyze /path/to/file.FCStd` - Analyze specific file
- `state` - Show basic document state

### Command Line Analysis

Analyze a specific file:
```bash
python src/main.py analyze /path/to/your/file.FCStd
```

Using the dedicated analysis script:
```bash
python src/analyze.py /path/to/your/file.FCStd
python src/analyze.py --verbose /path/to/your/file.FCStd
python src/analyze.py --batch *.FCStd
```

### CLI Arguments

```bash
python src/cli.py --analyze /path/to/file.FCStd
python src/cli.py --command "create box 10x10x10"
python src/cli.py --auto-analyze  # Analyze after each command
```

### Automatic Analysis

The system automatically performs state analysis after each successful command execution, providing immediate feedback on the document state.

## Example Output

```
==================================================
🔍 FreeCAD Document Analysis
==================================================
📄 Document: TestDocument
📊 Objects: 3

📋 State Analysis:
------------------------------
Pad Created: ✅
Face Available: ✅
Active Body: ❌
Sketch Plane Ready: ✅
Constrained Base Sketch: ❌
Safe References: ✅
No Errors: ✅

🏗️  Objects in Document:
------------------------------
  • TestBox (Part::Box)
  • TestCylinder (Part::Cylinder)
  • Sketch001 (Sketcher::SketchObject)
==================================================

📊 Overall Readiness Score: 71.4% (5/7)
⚠️  Document needs attention before production
```

## Integration with Existing System

The analysis functionality is fully integrated with:

1. **Command Executor**: Automatic analysis after command execution
2. **State Manager**: Caching of analysis results in Redis
3. **API Client**: Works with both direct and subprocess execution modes
4. **CLI Interface**: New commands and modes for analysis

## Testing

Run the test suite to verify functionality:
```bash
python tests/test_state_analysis.py
```

## Error Handling

The system gracefully handles:
- Missing FreeCAD installations
- Corrupted or invalid files
- Network/Redis connectivity issues
- Permission problems

All errors are reported with clear messages and suggestions for resolution.
