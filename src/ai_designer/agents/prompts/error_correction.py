"""
Error Correction Prompts for Validation Failures

Specialized prompts for handling different types of errors:
- Syntax errors in generated code
- FreeCAD recompute failures
- Design intent mismatches
- Geometric validation failures

Version: 1.0.0
"""

from typing import Dict, Literal

ErrorType = Literal["syntax", "recompute", "intent", "geometry", "workflow"]

# ============================================================================
# Base Error Correction Template
# ============================================================================

ERROR_CORRECTION_BASE = """You previously generated code that encountered an error.

**Original User Request:**
{user_prompt}

**Your Previous Code:**
```python
{previous_script}
```

**Error Encountered:**
{error_message}

**Error Type:** {error_type}

{specific_guidance}

Please generate a corrected version of the script that addresses the error.
Focus on fixing the specific issue while maintaining the overall design intent.
"""

# ============================================================================
# Syntax Error Correction
# ============================================================================

SYNTAX_ERROR_GUIDANCE = """
**Error Analysis:**
This is a Python syntax error. The code has invalid Python syntax that prevents execution.

**Common Causes:**
1. Missing/mismatched parentheses, brackets, or braces
2. Incorrect indentation
3. Missing colons after if/for/while/def/class statements
4. Invalid variable names (e.g., starting with numbers, using reserved keywords)
5. String quote mismatches
6. Missing commas in lists or function arguments

**Fix Strategy:**
1. Review the error message for the specific line and issue
2. Check for balanced parentheses/brackets/braces
3. Verify indentation is consistent (use 4 spaces)
4. Ensure all statements are properly closed
5. Validate variable and function names
6. Test the syntax with Python's ast module mentally

**Example Fix:**
Before (error):
```python
sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 25)
# Missing closing parenthesis
```

After (fixed):
```python
sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 25))
```
"""

# ============================================================================
# Recompute Error Correction
# ============================================================================

RECOMPUTE_ERROR_GUIDANCE = """
**Error Analysis:**
FreeCAD's recompute() failed. This means the geometry could not be computed correctly.

**Common Causes:**
1. **Sketch not fully constrained:** Too many or too few degrees of freedom
2. **Invalid feature sequence:** Features depend on non-existent objects
3. **Geometric impossibility:** Trying to create invalid shapes (e.g., negative dimensions)
4. **Reference errors:** Referencing wrong faces/edges (e.g., Face6 doesn't exist)
5. **Self-intersecting sketches:** Sketch geometry overlaps itself
6. **Broken dependencies:** Feature references object that was deleted or failed

**Fix Strategy:**
1. **For sketch issues:**
   - Ensure sketch is on a valid plane/face
   - Check all geometry is properly connected
   - Verify constraints don't conflict
   - Add missing constraints or remove redundant ones

2. **For feature issues:**
   - Verify the Profile/Base references exist
   - Check dimensions are positive and reasonable
   - Ensure feature order is correct (can't fillet before creating solid)
   - Verify face/edge references match actual geometry

3. **For reference issues:**
   - Use correct face numbering (Face1, Face2, etc.)
   - Ensure referenced object completed successfully
   - Check support plane exists before creating sketch

**Example Fix:**
Before (error):
```python
# Trying to fillet before creating the solid
fillet = doc.addObject("PartDesign::Fillet", "Fillet")
body.addObject(fillet)
fillet.Base = (pad, ['Edge1'])  # 'pad' doesn't exist yet!
fillet.Radius = 2

pad = doc.addObject("PartDesign::Pad", "Pad")  # Created AFTER fillet
```

After (fixed):
```python
# Create pad FIRST, then fillet
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 10

doc.recompute()  # Recompute before fillet

fillet = doc.addObject("PartDesign::Fillet", "Fillet")
body.addObject(fillet)
fillet.Base = (pad, ['Edge1'])
fillet.Radius = 2
```

**Debugging Checklist:**
- [ ] All referenced objects are created before use
- [ ] doc.recompute() called between dependent features
- [ ] All dimensions are positive
- [ ] Face/edge references are valid
- [ ] Sketch is properly attached to a support
- [ ] Feature sequence follows logical order
"""

# ============================================================================
# Intent Mismatch Correction
# ============================================================================

INTENT_MISMATCH_GUIDANCE = """
**Error Analysis:**
The generated design doesn't match what the user requested.

**Validation Feedback:**
{validation_feedback}

**Common Issues:**
1. **Wrong dimensions:** Sizes don't match specifications
2. **Missing features:** User requested holes/fillets/etc. that are absent
3. **Extra features:** Created things not requested
4. **Wrong position:** Features in incorrect locations
5. **Wrong shape type:** Created box instead of cylinder, etc.
6. **Incorrect quantity:** Wrong number of repetitions/patterns

**Fix Strategy:**
1. **Review user request carefully:**
   - Extract all dimension specifications
   - List all requested features
   - Note any position/orientation requirements
   - Identify any quantity requirements (e.g., "4 holes")

2. **Compare to generated design:**
   - Check each requested feature is present
   - Verify all dimensions match
   - Confirm positions/orientations
   - Validate quantities

3. **Make targeted fixes:**
   - Add missing features
   - Correct dimensions
   - Adjust positions
   - Fix quantities

**Example Fix:**
User Request: "Box 100x50x30mm with 2 holes 10mm diameter"

Before (wrong):
```python
# Only created box, missing holes
pad.Length = 30
```

After (fixed):
```python
# Box correct
pad.Length = 30

doc.recompute()

# Add the 2 holes
hole_sketch = doc.addObject("Sketcher::SketchObject", "HoleSketch")
body.addObject(hole_sketch)
hole_sketch.Support = (pad, ['Face6'])

# Two circles for holes
hole_sketch.addGeometry(Part.Circle(App.Vector(-30, 0, 0), App.Vector(0, 0, 1), 5))
hole_sketch.addGeometry(Part.Circle(App.Vector(30, 0, 0), App.Vector(0, 0, 1), 5))

pocket = doc.addObject("PartDesign::Pocket", "Pocket")
body.addObject(pocket)
pocket.Profile = hole_sketch
pocket.Type = 1  # Through all
```
"""

# ============================================================================
# Geometry Validation Error
# ============================================================================

GEOMETRY_ERROR_GUIDANCE = """
**Error Analysis:**
The geometry is invalid or malformed.

**Issues Detected:**
{geometry_issues}

**Common Problems:**
1. **Zero-volume solid:** Shape has no volume (collapsed to a plane/line)
2. **Self-intersecting:** Geometry crosses itself
3. **Non-manifold edges:** Edges shared by more than 2 faces
4. **Degenerate geometry:** Zero-length edges, zero-area faces
5. **Invalid boolean operation:** Cut/union/intersection failed

**Fix Strategy:**
1. **For zero-volume:**
   - Check pad/pocket lengths are positive and non-zero
   - Verify sketch is not degenerate
   - Ensure extrusion direction is correct

2. **For self-intersection:**
   - Simplify sketch geometry
   - Check pocket depth doesn't go through entire solid
   - Verify fillet radius isn't too large for edge length

3. **For invalid booleans:**
   - Ensure sketches are closed
   - Check profiles don't have gaps
   - Verify shapes actually overlap for boolean operations

**Example Fix:**
Before (zero volume):
```python
pad.Length = 0  # Zero extrusion!
```

After (fixed):
```python
pad.Length = 10  # Positive extrusion
```
"""

# ============================================================================
# Workflow Error Correction
# ============================================================================

WORKFLOW_ERROR_GUIDANCE = """
**Error Analysis:**
The code doesn't follow proper FreeCAD PartDesign workflow.

**Workflow Issues:**
{workflow_issues}

**PartDesign Best Practices:**
1. **Always start with Body:** Container for all features
2. **Sketch on plane/face:** Sketches need support
3. **Close sketch before 3D:** Sketch must be complete before Pad/Pocket
4. **Features build on features:** Logical sequence matters
5. **Recompute between features:** Call doc.recompute() after each major step
6. **Reference existing geometry:** Use faces/edges from previous features

**Common Workflow Violations:**
- Creating features without Body
- Sketch not attached to support
- Trying to pocket before creating solid
- Fillet/chamfer before base feature
- Wrong dependency order

**Example Fix:**
Before (bad workflow):
```python
# No body!
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
# Sketch floating in space, no support!
```

After (proper workflow):
```python
# Create Body first
body = doc.addObject("PartDesign::Body", "Body")

# Attach sketch to Body and support plane
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])
```
"""

# ============================================================================
# Error Correction Prompts Dictionary
# ============================================================================

ERROR_CORRECTION_PROMPTS = {
    "syntax": {
        "template": ERROR_CORRECTION_BASE,
        "guidance": SYNTAX_ERROR_GUIDANCE,
    },
    "recompute": {
        "template": ERROR_CORRECTION_BASE,
        "guidance": RECOMPUTE_ERROR_GUIDANCE,
    },
    "intent": {
        "template": ERROR_CORRECTION_BASE,
        "guidance": INTENT_MISMATCH_GUIDANCE,
    },
    "geometry": {
        "template": ERROR_CORRECTION_BASE,
        "guidance": GEOMETRY_ERROR_GUIDANCE,
    },
    "workflow": {
        "template": ERROR_CORRECTION_BASE,
        "guidance": WORKFLOW_ERROR_GUIDANCE,
    },
}


def get_error_correction_prompt(
    error_type: ErrorType,
    user_prompt: str,
    previous_script: str,
    error_message: str,
    additional_context: Dict[str, str] = None,
) -> str:
    """
    Generate error correction prompt for a specific error type.

    Args:
        error_type: Type of error (syntax, recompute, intent, geometry, workflow)
        user_prompt: Original user request
        previous_script: The script that failed
        error_message: Error message from execution/validation
        additional_context: Additional context (validation_feedback, geometry_issues, etc.)

    Returns:
        Formatted error correction prompt

    Example:
        >>> prompt = get_error_correction_prompt(
        ...     "syntax",
        ...     "Create a box",
        ...     "sketch.addGeometry(Part.Circle...",
        ...     "SyntaxError: unexpected EOF"
        ... )
        >>> "syntax error" in prompt.lower()
        True
    """
    if error_type not in ERROR_CORRECTION_PROMPTS:
        raise ValueError(f"Unknown error type: {error_type}")

    config = ERROR_CORRECTION_PROMPTS[error_type]
    guidance = config["guidance"]

    # Format additional context into guidance
    if additional_context:
        guidance = guidance.format(**additional_context)

    prompt = config["template"].format(
        user_prompt=user_prompt,
        previous_script=previous_script,
        error_message=error_message,
        error_type=error_type,
        specific_guidance=guidance,
    )

    return prompt


def get_syntax_fix_prompt(script: str, error: str) -> str:
    """
    Quick syntax error fix prompt.

    Args:
        script: Script with syntax error
        error: Syntax error message

    Returns:
        Syntax fix prompt

    Example:
        >>> prompt = get_syntax_fix_prompt("def foo(", "SyntaxError: EOF")
        >>> "syntax" in prompt.lower()
        True
    """
    return f"""Fix this Python syntax error:

```python
{script}
```

Error: {error}

{SYNTAX_ERROR_GUIDANCE}

Generate the corrected script.
"""


def get_recompute_fix_prompt(
    script: str, error: str, execution_context: str = ""
) -> str:
    """
    Quick recompute error fix prompt.

    Args:
        script: Script that failed recompute
        error: Recompute error message
        execution_context: Additional execution context (optional)

    Returns:
        Recompute fix prompt

    Example:
        >>> prompt = get_recompute_fix_prompt(
        ...     "pad.Length = -10",
        ...     "Recompute failed"
        ... )
        >>> "recompute" in prompt.lower()
        True
    """
    context = (
        f"\n\nExecution Context:\n{execution_context}" if execution_context else ""
    )

    return f"""Fix this FreeCAD recompute error:

```python
{script}
```

Error: {error}{context}

{RECOMPUTE_ERROR_GUIDANCE}

Generate the corrected script.
"""


def classify_error(error_message: str) -> ErrorType:
    """
    Classify error type from error message.

    Args:
        error_message: Error message from execution

    Returns:
        Classified error type

    Example:
        >>> classify_error("SyntaxError: invalid syntax")
        'syntax'
        >>> classify_error("Recompute of Pad001 failed")
        'recompute'
    """
    error_lower = error_message.lower()

    if any(
        keyword in error_lower
        for keyword in [
            "syntaxerror",
            "indentation",
            "unexpected eof",
            "invalid syntax",
        ]
    ):
        return "syntax"

    if any(
        keyword in error_lower
        for keyword in ["recompute", "compute failed", "broken reference"]
    ):
        return "recompute"

    if any(
        keyword in error_lower
        for keyword in [
            "self-intersect",
            "invalid geometry",
            "zero volume",
            "degenerate",
        ]
    ):
        return "geometry"

    if any(
        keyword in error_lower for keyword in ["no body", "no support", "not attached"]
    ):
        return "workflow"

    # Default to recompute for FreeCAD-related errors
    return "recompute"
