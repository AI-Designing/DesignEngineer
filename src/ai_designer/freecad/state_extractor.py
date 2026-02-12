"""
FreeCAD Document State Extractor

Extracts comprehensive state information from FreeCAD documents including:
- Object list with types and dimensions
- Feature tree hierarchy
- Recompute status and errors
- Constraints and dependencies
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StateExtractor:
    """
    Extracts state information from FreeCAD documents.

    Uses freecadcmd subprocess to open and analyze saved documents,
    extracting object information, feature trees, and error states.
    """

    def __init__(self, freecad_cmd: str = "freecadcmd"):
        """
        Initialize state extractor.

        Args:
            freecad_cmd: Path to freecadcmd executable (default: "freecadcmd")
        """
        self.freecad_cmd = freecad_cmd

    def extract_state(self, doc_path: Path, timeout: int = 30) -> Dict[str, Any]:
        """
        Extract complete state from FreeCAD document.

        Args:
            doc_path: Path to FreeCAD document (.FCStd file)
            timeout: Extraction timeout in seconds (default: 30)

        Returns:
            Dictionary with document state:
            {
                "success": bool,
                "document_name": str,
                "object_count": int,
                "objects": List[Dict],  # name, type, label, bbox, state
                "feature_tree": Dict,   # hierarchical structure
                "recompute_errors": List[str],
                "constraints": Dict,    # constraint counts
                "metadata": Dict        # additional info
            }
        """
        if not doc_path.exists():
            return {
                "success": False,
                "error": f"Document not found: {doc_path}",
            }

        logger.info(f"Extracting state from: {doc_path}")

        # Create extraction script
        extraction_script = self._create_extraction_script(doc_path)

        # Execute via freecadcmd
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(extraction_script)
                script_path = temp_file.name

            try:
                result = subprocess.run(
                    [self.freecad_cmd, script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                # Parse JSON output
                state = self._parse_extraction_output(result.stdout, result.stderr)

                if result.returncode == 0:
                    state["success"] = True
                    logger.info(
                        f"Extracted state: {state.get('object_count', 0)} objects"
                    )
                else:
                    state["success"] = False
                    state["error"] = f"Extraction failed: {result.stderr}"
                    logger.error(f"State extraction failed: {result.stderr}")

                return state

            finally:
                # Cleanup temp file
                try:
                    Path(script_path).unlink()
                except Exception:
                    pass

        except subprocess.TimeoutExpired:
            logger.error(f"State extraction timeout ({timeout}s)")
            return {
                "success": False,
                "error": f"Extraction timeout ({timeout}s)",
            }

        except Exception as e:
            logger.error(f"State extraction error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _create_extraction_script(self, doc_path: Path) -> str:
        """Create Python script for state extraction."""
        return f'''#!/usr/bin/env python3
"""
FreeCAD state extraction script
Document: {doc_path}
"""

import json
import sys

try:
    import FreeCAD as App
    import Part
except ImportError as e:
    print(json.dumps({{"success": False, "error": f"Failed to import FreeCAD: {{e}}"}}))
    sys.exit(1)

try:
    # Open document
    doc = App.openDocument("{doc_path}")

    # Extract object information
    objects = []
    for obj in doc.Objects:
        obj_info = {{
            "name": obj.Name,
            "label": obj.Label,
            "type": obj.TypeId if hasattr(obj, 'TypeId') else 'Unknown',
            "visible": obj.ViewObject.Visibility if hasattr(obj, 'ViewObject') else True,
            "state": obj.State if hasattr(obj, 'State') else 0,
        }}

        # Add bounding box for objects with Shape
        if hasattr(obj, 'Shape') and hasattr(obj.Shape, 'BoundBox'):
            bbox = obj.Shape.BoundBox
            obj_info["bbox"] = {{
                "xmin": bbox.XMin,
                "ymin": bbox.YMin,
                "zmin": bbox.ZMin,
                "xmax": bbox.XMax,
                "ymax": bbox.YMax,
                "zmax": bbox.ZMax,
            }}

        # Add dimensions for specific object types
        if hasattr(obj, 'Height'):
            obj_info["height"] = float(obj.Height)
        if hasattr(obj, 'Width'):
            obj_info["width"] = float(obj.Width)
        if hasattr(obj, 'Length'):
            obj_info["length"] = float(obj.Length)
        if hasattr(obj, 'Radius'):
            obj_info["radius"] = float(obj.Radius)

        objects.append(obj_info)

    # Build feature tree
    feature_tree = {{}}
    for obj in doc.Objects:
        parents = [p.Name for p in obj.InList] if hasattr(obj, 'InList') else []
        children = [c.Name for c in obj.OutList] if hasattr(obj, 'OutList') else []

        feature_tree[obj.Name] = {{
            "label": obj.Label,
            "type": obj.TypeId if hasattr(obj, 'TypeId') else 'Unknown',
            "parents": parents,
            "children": children,
        }}

    # Check for recompute errors
    recompute_errors = []
    for obj in doc.Objects:
        if hasattr(obj, 'State') and obj.State != 0:
            error_msg = f"Object '{{obj.Label}}' has state {{obj.State}}"
            if obj.State == 3:
                error_msg += " (Error)"
            elif obj.State == 4:
                error_msg += " (InvalidParameter)"
            recompute_errors.append(error_msg)

    # Count constraints (for Sketcher objects)
    constraints = {{
        "total": 0,
        "by_type": {{}},
    }}

    for obj in doc.Objects:
        if obj.TypeId.startswith("Sketcher::"):
            if hasattr(obj, 'Constraints'):
                constraints["total"] += len(obj.Constraints)
                for constraint in obj.Constraints:
                    ctype = str(constraint.Type) if hasattr(constraint, 'Type') else 'Unknown'
                    constraints["by_type"][ctype] = constraints["by_type"].get(ctype, 0) + 1

    # Compile state
    state = {{
        "success": True,
        "document_name": doc.Name,
        "document_path": "{doc_path}",
        "object_count": len(objects),
        "objects": objects,
        "feature_tree": feature_tree,
        "recompute_errors": recompute_errors,
        "constraints": constraints,
        "metadata": {{
            "label": doc.Label if hasattr(doc, 'Label') else doc.Name,
            "author": doc.LastModifiedBy if hasattr(doc, 'LastModifiedBy') else "Unknown",
            "has_errors": len(recompute_errors) > 0,
        }}
    }}

    # Output as JSON
    print("STATE_JSON_START")
    print(json.dumps(state, indent=2))
    print("STATE_JSON_END")

    # Close document
    App.closeDocument(doc.Name)

except Exception as e:
    import traceback
    print(json.dumps({{
        "success": False,
        "error": f"State extraction failed: {{e}}",
        "traceback": traceback.format_exc(),
    }}))
    sys.exit(1)
'''

    def _parse_extraction_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse state extraction output."""
        try:
            # Look for JSON between markers
            if "STATE_JSON_START" in stdout and "STATE_JSON_END" in stdout:
                start_idx = stdout.index("STATE_JSON_START") + len("STATE_JSON_START")
                end_idx = stdout.index("STATE_JSON_END")
                json_str = stdout[start_idx:end_idx].strip()

                state = json.loads(json_str)
                return state

            # Fallback: try to parse entire stdout as JSON
            state = json.loads(stdout)
            return state

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction output: {e}")
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "raw_output": stdout[:500],  # First 500 chars for debugging
            }

        except Exception as e:
            logger.error(f"Output parsing error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_feature_tree_hierarchy(
        self, feature_tree: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build hierarchical feature tree from flat structure.

        Args:
            feature_tree: Flat feature tree from extract_state()

        Returns:
            Hierarchical tree structure with nested children
        """
        # Find root objects (those with no parents)
        roots = []
        for name, info in feature_tree.items():
            if not info.get("parents"):
                roots.append(name)

        def build_hierarchy(obj_name: str) -> Dict[str, Any]:
            """Recursively build hierarchy for an object."""
            obj_info = feature_tree.get(obj_name, {})
            node = {
                "name": obj_name,
                "label": obj_info.get("label", obj_name),
                "type": obj_info.get("type", "Unknown"),
                "children": [],
            }

            # Add children recursively
            for child_name in obj_info.get("children", []):
                if child_name in feature_tree:  # Avoid circular refs
                    node["children"].append(build_hierarchy(child_name))

            return node

        # Build hierarchy from roots
        hierarchy = {
            "roots": [build_hierarchy(root) for root in roots],
            "total_objects": len(feature_tree),
            "root_count": len(roots),
        }

        return hierarchy

    def extract_object_dimensions(
        self, objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract dimensional summary from objects.

        Args:
            objects: Object list from extract_state()

        Returns:
            Dictionary with dimensional statistics
        """
        dimensions = {
            "total_objects": len(objects),
            "objects_with_bbox": 0,
            "overall_bbox": None,
            "by_type": {},
        }

        all_x = []
        all_y = []
        all_z = []

        for obj in objects:
            obj_type = obj.get("type", "Unknown")

            # Count by type
            if obj_type not in dimensions["by_type"]:
                dimensions["by_type"][obj_type] = 0
            dimensions["by_type"][obj_type] += 1

            # Collect bounding box info
            if "bbox" in obj:
                dimensions["objects_with_bbox"] += 1
                bbox = obj["bbox"]

                all_x.extend([bbox["xmin"], bbox["xmax"]])
                all_y.extend([bbox["ymin"], bbox["ymax"]])
                all_z.extend([bbox["zmin"], bbox["zmax"]])

        # Calculate overall bounding box
        if all_x and all_y and all_z:
            dimensions["overall_bbox"] = {
                "xmin": min(all_x),
                "ymin": min(all_y),
                "zmin": min(all_z),
                "xmax": max(all_x),
                "ymax": max(all_y),
                "zmax": max(all_z),
            }

        return dimensions
