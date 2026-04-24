"""
FreeCAD Document State Extractor

Extracts comprehensive state information from FreeCAD documents including:
- Object list with types and dimensions
- Feature tree hierarchy
- Recompute status and errors
- Constraints and dependencies
- Geometry summary, topology counts, sketch constraint summaries (Track 7)

Track 5 coordination: orchestration should pass ``geometry_summary`` (and related
fields from ``result["state"]``) into ``execution_result`` for the validator;
this module only produces the nested state dict on the executor result.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_designer.schemas.document_state import (
    DEFAULT_DETAIL_LEVEL,
    DETAIL_LEVELS,
    STATE_SCHEMA_VERSION,
)

logger = logging.getLogger(__name__)

# Max constraint rows across all sketches (keeps JSON bounded for LLM paths).
_MAX_SKETCH_CONSTRAINT_ROWS = 100


_EXTRACTION_SCRIPT_TEMPLATE = r'''#!/usr/bin/env python3
"""FreeCAD state extraction script (generated)."""

import json
import os

STATE_SCHEMA_VERSION = __STATE_SCHEMA_INT__
DETAIL_LEVEL = __DETAIL_LEVEL__

try:
    import FreeCAD as App
except ImportError as e:
    print(json.dumps({"success": False, "error": "Failed to import FreeCAD: %s" % (e,)}))
    os._exit(1)

def _constraint_row(c, idx):
    row = {}
    try:
        if hasattr(c, "Type"):
            try:
                row["type"] = int(c.Type)
            except Exception:
                row["type"] = None
            row["type_name"] = str(c.Type)
        if hasattr(c, "Name") and c.Name:
            row["id"] = str(c.Name)
        else:
            row["id"] = str(idx)
        for key in ("First", "Second", "Third"):
            if hasattr(c, key):
                v = getattr(c, key)
                try:
                    row[key.lower()] = int(v) if isinstance(v, (int, float)) else str(v)
                except Exception:
                    row[key.lower()] = str(v)
    except Exception:
        row["type_name"] = "Unknown"
    return row


try:
    doc = App.openDocument(__DOC_PATH__)

    objects = []
    sketch_constraints_remaining = __MAX_SKETCH_CONSTRAINT_ROWS__
    sketch_constraints_truncated = False
    sketches = []
    constraints = {"total": 0, "by_type": {}}

    for obj in doc.Objects:
        obj_info = {
            "name": obj.Name,
            "label": obj.Label,
            "type": obj.TypeId if hasattr(obj, "TypeId") else "Unknown",
            "visible": obj.ViewObject.Visibility if hasattr(obj, "ViewObject") and obj.ViewObject else True,
            "state": obj.State if hasattr(obj, "State") else 0,
        }

        if hasattr(obj, "Shape") and hasattr(obj.Shape, "BoundBox"):
            try:
                if not obj.Shape.isNull():
                    bbox = obj.Shape.BoundBox
                    obj_info["bbox"] = {
                        "xmin": float(bbox.XMin),
                        "ymin": float(bbox.YMin),
                        "zmin": float(bbox.ZMin),
                        "xmax": float(bbox.XMax),
                        "ymax": float(bbox.YMax),
                        "zmax": float(bbox.ZMax),
                    }
            except Exception:
                pass

        if hasattr(obj, "Height"):
            obj_info["height"] = float(obj.Height)
        if hasattr(obj, "Width"):
            obj_info["width"] = float(obj.Width)
        if hasattr(obj, "Length"):
            obj_info["length"] = float(obj.Length)
        if hasattr(obj, "Radius"):
            obj_info["radius"] = float(obj.Radius)

        if DETAIL_LEVEL != "minimal" and hasattr(obj, "Shape") and hasattr(obj.Shape, "isNull"):
            try:
                sh = obj.Shape
                if not sh.isNull():
                    try:
                        v = float(sh.Volume)
                        if v >= 0:
                            obj_info["volume_mm3"] = v
                    except Exception:
                        pass
                    try:
                        com = sh.CenterOfMass
                        obj_info["center_of_mass"] = {
                            "x": float(com.x),
                            "y": float(com.y),
                            "z": float(com.z),
                        }
                    except Exception:
                        pass
                    try:
                        obj_info["surface_area_mm2"] = float(sh.Area)
                    except Exception:
                        pass
            except Exception:
                pass

        if DETAIL_LEVEL in ("standard", "full") and hasattr(obj, "Shape") and hasattr(obj.Shape, "isNull"):
            try:
                sh = obj.Shape
                if not sh.isNull():
                    try:
                        obj_info["topology"] = {
                            "face_count": len(sh.Faces),
                            "edge_count": len(sh.Edges),
                            "vertex_count": len(sh.Vertexes),
                        }
                    except Exception:
                        pass
            except Exception:
                pass

        tid = getattr(obj, "TypeId", "") or ""
        if tid.startswith("Sketcher::") and hasattr(obj, "Constraints"):
            try:
                cons_list = []
                dof_unknown = True
                fully_constrained = None
                if hasattr(obj, "FullyConstrained"):
                    try:
                        fully_constrained = bool(obj.FullyConstrained)
                        dof_unknown = False
                    except Exception:
                        pass
                for idx, constraint in enumerate(obj.Constraints):
                    constraints["total"] += 1
                    ctype = str(constraint.Type) if hasattr(constraint, "Type") else "Unknown"
                    constraints["by_type"][ctype] = constraints["by_type"].get(ctype, 0) + 1
                    if sketch_constraints_remaining > 0:
                        cons_list.append(_constraint_row(constraint, idx))
                        sketch_constraints_remaining -= 1
                    else:
                        sketch_constraints_truncated = True
                sketches.append({
                    "sketch_name": obj.Name,
                    "sketch_label": obj.Label,
                    "constraints": cons_list,
                    "fully_constrained": fully_constrained,
                    "dof_unknown": dof_unknown,
                })
            except Exception:
                pass

        objects.append(obj_info)

    feature_tree = {}
    for obj in doc.Objects:
        parents = [p.Name for p in obj.InList] if hasattr(obj, "InList") else []
        children = [c.Name for c in obj.OutList] if hasattr(obj, "OutList") else []
        feature_tree[obj.Name] = {
            "label": obj.Label,
            "type": obj.TypeId if hasattr(obj, "TypeId") else "Unknown",
            "parents": parents,
            "children": children,
        }

    recompute_issues = []
    recompute_errors = []
    for obj in doc.Objects:
        if hasattr(obj, "State") and obj.State != 0:
            msg = "Object '%s' has state %s" % (obj.Label, obj.State)
            if obj.State == 3:
                msg += " (Error)"
            elif obj.State == 4:
                msg += " (InvalidParameter)"
            recompute_errors.append(msg)
            recompute_issues.append({
                "name": obj.Name,
                "label": obj.Label,
                "state": int(obj.State),
                "message": msg,
            })

    all_x, all_y, all_z = [], [], []
    total_volume = 0.0
    solid_object_count = 0
    largest_name = None
    largest_vol = -1.0
    for o in objects:
        bb = o.get("bbox")
        if bb:
            all_x.extend([bb["xmin"], bb["xmax"]])
            all_y.extend([bb["ymin"], bb["ymax"]])
            all_z.extend([bb["zmin"], bb["zmax"]])
        v = o.get("volume_mm3")
        if v is not None and v > 0:
            solid_object_count += 1
            total_volume += float(v)
            if float(v) > largest_vol:
                largest_vol = float(v)
                largest_name = o.get("name", "")
        elif DETAIL_LEVEL == "minimal":
            try:
                ob = doc.getObject(o["name"])
                if ob and hasattr(ob, "Shape") and hasattr(ob.Shape, "isNull") and not ob.Shape.isNull():
                    solid_object_count += 1
            except Exception:
                pass

    document_bbox = None
    if all_x and all_y and all_z:
        document_bbox = {
            "xmin": min(all_x),
            "ymin": min(all_y),
            "zmin": min(all_z),
            "xmax": max(all_x),
            "ymax": max(all_y),
            "zmax": max(all_z),
        }

    largest_solid = None
    if largest_name is not None and largest_vol >= 0:
        largest_solid = {"name": largest_name, "volume_mm3": largest_vol}

    any_shape = False
    any_invalid = False
    any_open = False
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape and hasattr(obj.Shape, "isNull") and not obj.Shape.isNull():
            sh = obj.Shape
            any_shape = True
            try:
                if not sh.isValid():
                    any_invalid = True
            except Exception:
                pass
            try:
                if hasattr(sh, "isClosed") and not sh.isClosed():
                    any_open = True
            except Exception:
                pass

    is_manifold = None
    has_invalid_faces = None
    has_self_intersections = None
    if any_shape:
        has_invalid_faces = any_invalid
        is_manifold = (not any_invalid) and (not any_open)

    geometry_summary = {
        "solid_object_count": solid_object_count,
        "total_volume_mm3": total_volume,
        "document_bbox": document_bbox,
        "largest_solid_by_volume": largest_solid,
        "is_manifold": is_manifold,
        "has_invalid_faces": has_invalid_faces,
        "has_self_intersections": has_self_intersections,
    }

    state = {
        "success": True,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "detail_level": DETAIL_LEVEL,
        "document_name": doc.Name,
        "document_path": __DOC_PATH_STR__,
        "object_count": len(objects),
        "objects": objects,
        "feature_tree": feature_tree,
        "recompute_errors": recompute_errors,
        "recompute_issues": recompute_issues,
        "constraints": constraints,
        "sketches": sketches,
        "geometry_summary": geometry_summary,
        "sketch_constraints_truncated": sketch_constraints_truncated,
        "metadata": {
            "label": doc.Label if hasattr(doc, "Label") else doc.Name,
            "author": doc.LastModifiedBy if hasattr(doc, "LastModifiedBy") else "Unknown",
            "has_errors": len(recompute_errors) > 0,
        },
    }

    print("STATE_JSON_START")
    print(json.dumps(state, indent=2))
    print("STATE_JSON_END")

    App.closeDocument(doc.Name)

except Exception as e:
    import traceback
    print(json.dumps({
        "success": False,
        "error": "State extraction failed: %s" % (e,),
        "traceback": traceback.format_exc(),
    }))
    os._exit(1)
'''


def geometry_summary_from_state(state: Dict[str, Any]) -> Optional["GeometrySummary"]:
    """
    Map ``StateExtractor`` / freecadcmd JSON into the Track 5 ``GeometrySummary`` model.

    Returns ``None`` when ``success`` is false or state is unusable.
    """
    from ai_designer.schemas.execution_feedback import GeometrySummary

    if not state or state.get("success") is False:
        return None

    gs = (
        state.get("geometry_summary")
        if isinstance(state.get("geometry_summary"), dict)
        else {}
    )
    objects = state.get("objects") or []
    oc = int(state.get("object_count", 0))
    if oc == 0 and objects:
        oc = len(objects)

    tv_raw = gs.get("total_volume_mm3")
    tv: Optional[float]
    if tv_raw is None:
        tv = None
    else:
        tv = float(tv_raw)

    bbox_lwh: Optional[Dict[str, float]] = None
    db = gs.get("document_bbox")
    if isinstance(db, dict) and all(
        k in db for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")
    ):
        lx = float(db["xmax"]) - float(db["xmin"])
        wy = float(db["ymax"]) - float(db["ymin"])
        hz = float(db["zmax"]) - float(db["zmin"])
        if lx > 0 and wy > 0 and hz > 0:
            bbox_lwh = {"length": lx, "width": wy, "height": hz}

    if bbox_lwh is None:
        solids = [o for o in objects if isinstance(o.get("bbox"), dict)]
        if solids:
            try:
                xmins = [float(o["bbox"]["xmin"]) for o in solids]
                xmaxs = [float(o["bbox"]["xmax"]) for o in solids]
                ymins = [float(o["bbox"]["ymin"]) for o in solids]
                ymaxs = [float(o["bbox"]["ymax"]) for o in solids]
                zmins = [float(o["bbox"]["zmin"]) for o in solids]
                zmaxs = [float(o["bbox"]["zmax"]) for o in solids]
                lx = max(xmaxs) - min(xmins)
                wy = max(ymaxs) - min(ymins)
                hz = max(zmaxs) - min(zmins)
                if lx > 0 and wy > 0 and hz > 0:
                    dims = sorted([lx, wy, hz], reverse=True)
                    bbox_lwh = {
                        "length": dims[0],
                        "width": dims[1],
                        "height": dims[2],
                    }
            except (KeyError, TypeError, ValueError):
                pass

    return GeometrySummary(
        object_count=oc,
        total_volume_mm3=tv,
        bounding_box=bbox_lwh,
        is_manifold=gs.get("is_manifold"),
        has_invalid_faces=gs.get("has_invalid_faces"),
        has_self_intersections=gs.get("has_self_intersections"),
    )


def _normalize_document_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fill Track 7 keys when absent (older extractors or partial JSON)."""
    if not isinstance(state, dict):
        return state
    if state.get("success") is False and "object_count" not in state:
        return state
    state.setdefault("state_schema_version", STATE_SCHEMA_VERSION)
    state.setdefault("detail_level", DEFAULT_DETAIL_LEVEL)
    state.setdefault("recompute_issues", [])
    state.setdefault("sketches", [])
    state.setdefault("sketch_constraints_truncated", False)
    if "geometry_summary" not in state:
        state["geometry_summary"] = None
    if not state.get("recompute_issues") and state.get("recompute_errors"):
        state["recompute_issues"] = [
            {
                "name": "",
                "label": "",
                "state": -1,
                "message": msg,
            }
            for msg in state["recompute_errors"]
        ]
    return state


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

    def extract_state(
        self,
        doc_path: Path,
        timeout: int = 30,
        detail_level: str = DEFAULT_DETAIL_LEVEL,
    ) -> Dict[str, Any]:
        """
        Extract complete state from FreeCAD document.

        Args:
            doc_path: Path to FreeCAD document (.FCStd file)
            timeout: Extraction timeout in seconds (default: 30)
            detail_level: ``minimal`` (bbox + tree + errors only),
                ``standard`` (default: volume, COM, surface area, topology counts),
                ``full`` (same as standard today; reserved for heavier topology).

        Returns:
            Dictionary with document state (see ``DocumentStatePayload`` in
            ``ai_designer.schemas.document_state``). Legacy keys are preserved.

        Note:
            The orchestration layer (Track 5) should copy ``geometry_summary`` and
            related metrics from executor ``state`` into ``execution_result`` for
            ``ValidatorAgent``; this method only runs extraction.
        """
        if detail_level not in DETAIL_LEVELS:
            detail_level = DEFAULT_DETAIL_LEVEL

        if not doc_path.exists():
            return {
                "success": False,
                "error": f"Document not found: {doc_path}",
            }

        logger.info(
            "Extracting state from: %s (detail_level=%s)", doc_path, detail_level
        )

        extraction_script = self._create_extraction_script(doc_path, detail_level)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(extraction_script)
                script_path = temp_file.name

            try:
                result = subprocess.run(
                    [self.freecad_cmd, "-c", script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                state = self._parse_extraction_output(result.stdout, result.stderr)

                if result.returncode == 0:
                    state["success"] = True
                    state = _normalize_document_state(state)
                    logger.info(
                        "Extracted state: %s objects",
                        state.get("object_count", 0),
                    )
                else:
                    state["success"] = False
                    state["error"] = f"Extraction failed: {result.stderr}"
                    logger.error("State extraction failed: %s", result.stderr)

                return state

            finally:
                try:
                    Path(script_path).unlink()
                except OSError:
                    pass

        except subprocess.TimeoutExpired:
            logger.error("State extraction timeout (%ss)", timeout)
            return {
                "success": False,
                "error": f"Extraction timeout ({timeout}s)",
            }

        except Exception as e:
            logger.error("State extraction error: %s", e)
            return {
                "success": False,
                "error": str(e),
            }

    def _create_extraction_script(
        self, doc_path: Path, detail_level: str = DEFAULT_DETAIL_LEVEL
    ) -> str:
        """Build the freecadcmd script with safe literal injection."""
        if detail_level not in DETAIL_LEVELS:
            detail_level = DEFAULT_DETAIL_LEVEL
        path_str = str(doc_path.resolve())
        # App.openDocument expects a path string; embed as JSON string literal.
        doc_path_py = json.dumps(path_str)
        detail_py = json.dumps(detail_level)
        tpl = _EXTRACTION_SCRIPT_TEMPLATE
        tpl = tpl.replace("__STATE_SCHEMA_INT__", str(STATE_SCHEMA_VERSION))
        tpl = tpl.replace("__DETAIL_LEVEL__", detail_py)
        tpl = tpl.replace("__DOC_PATH__", doc_path_py)
        tpl = tpl.replace("__DOC_PATH_STR__", json.dumps(path_str))
        tpl = tpl.replace(
            "__MAX_SKETCH_CONSTRAINT_ROWS__", str(_MAX_SKETCH_CONSTRAINT_ROWS)
        )
        return tpl

    def _parse_extraction_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse state extraction output."""
        try:
            if "STATE_JSON_START" in stdout and "STATE_JSON_END" in stdout:
                start_idx = stdout.index("STATE_JSON_START") + len("STATE_JSON_START")
                end_idx = stdout.index("STATE_JSON_END")
                json_str = stdout[start_idx:end_idx].strip()

                state = json.loads(json_str)
                return state

            state = json.loads(stdout)
            return state

        except json.JSONDecodeError as e:
            logger.error("Failed to parse extraction output: %s", e)
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "raw_output": stdout[:500],
            }

        except Exception as e:
            logger.error("Output parsing error: %s", e)
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

            for child_name in obj_info.get("children", []):
                if child_name in feature_tree:
                    node["children"].append(build_hierarchy(child_name))

            return node

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
        dimensions: Dict[str, Any] = {
            "total_objects": len(objects),
            "objects_with_bbox": 0,
            "overall_bbox": None,
            "by_type": {},
        }

        all_x: List[float] = []
        all_y: List[float] = []
        all_z: List[float] = []

        for obj in objects:
            obj_type = obj.get("type", "Unknown")

            if obj_type not in dimensions["by_type"]:
                dimensions["by_type"][obj_type] = 0
            dimensions["by_type"][obj_type] += 1

            if "bbox" in obj:
                dimensions["objects_with_bbox"] += 1
                bbox = obj["bbox"]

                all_x.extend([bbox["xmin"], bbox["xmax"]])
                all_y.extend([bbox["ymin"], bbox["ymax"]])
                all_z.extend([bbox["zmin"], bbox["zmax"]])

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
