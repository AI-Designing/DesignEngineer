import json
import os
import sys

# Add FreeCAD paths
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/lib/")
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/Mod")

try:
    import FreeCAD
    import Part
    import PartDesign
    import Sketcher

    FREECAD_AVAILABLE = True
except ImportError:
    FREECAD_AVAILABLE = False


class StateCache:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.default_state_key = "freecad_state"

    def cache_state(self, state_data, state_key=None):
        """Cache state data in Redis"""
        key = state_key or self.default_state_key

        # Serialize the state data to JSON
        serialized_data = json.dumps(state_data)
        self.redis_client.set(key, serialized_data)

    def retrieve_state(self, state_key=None):
        """Retrieve state data from Redis"""
        key = state_key or self.default_state_key

        data = self.redis_client.get(key)
        if data:
            # Deserialize the JSON data
            return json.loads(data.decode("utf-8") if isinstance(data, bytes) else data)
        return None

    def clear_state(self, state_key=None):
        """Clear state data from Redis"""
        key = state_key or self.default_state_key
        self.redis_client.delete(key)

    def update_state(self, state_data):
        """Update state data in Redis (alias for cache_state)"""
        self.cache_state(state_data)


class FreeCADStateAnalyzer:
    """Analyzes FreeCAD document state and provides detailed status information"""

    def __init__(self, api_client=None):
        self.api_client = api_client

    def analyze_document_state(self, doc_path=None):
        """
        Analyze FreeCAD document state and return comprehensive analysis
        If doc_path is provided, opens that document first
        """
        if FREECAD_AVAILABLE:
            return self._analyze_direct(doc_path)
        else:
            return self._analyze_via_subprocess(doc_path)

    def _analyze_direct(self, doc_path=None):
        """Direct analysis when FreeCAD is available"""
        try:
            if doc_path:
                FreeCAD.open(doc_path)

            doc = FreeCAD.ActiveDocument
            if not doc:
                return {"error": "No active document"}

            results = {
                "Pad Created": self._has_pad(doc),
                "Face Available": bool(self._get_available_faces(doc)),
                "Active Body": self._get_active_body(doc) is not None,
                "Sketch Plane Ready": self._all_sketches_mapped(doc),
                "Constrained Base Sketch": self._all_sketches_constrained(doc),
                "Safe References": self._all_references_safe(doc),
                "No Errors": self._has_no_errors(doc),
            }

            return {
                "status": "success",
                "analysis": results,
                "document": doc.Name,
                "object_count": len(doc.Objects),
                "objects": [
                    {"name": obj.Name, "type": obj.TypeId} for obj in doc.Objects
                ],
            }
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}

    def _analyze_via_subprocess(self, doc_path=None):
        """Analysis via subprocess when FreeCAD not directly available"""
        if not self.api_client:
            return {"error": "No API client available for subprocess analysis"}

        analysis_script = f"""
import sys
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/lib/")
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/Mod")

import FreeCAD
import Part
import PartDesign
import Sketcher
import json

# Open document if path provided
{f'FreeCAD.open("{doc_path}")' if doc_path else ''}

doc = FreeCAD.ActiveDocument
if not doc:
    print("ERROR: No active document")
    sys.exit(1)

# Analysis functions
def has_pad(doc):
    return any(obj.TypeId == 'PartDesign::Pad' for obj in doc.Objects)

def get_available_faces(doc):
    faces = []
    for obj in doc.Objects:
        if hasattr(obj, 'Shape') and obj.Shape:
            if hasattr(obj.Shape, 'Faces'):
                faces.extend(obj.Shape.Faces)
    return faces

def get_active_body(doc):
    for obj in doc.Objects:
        if obj.TypeId == 'PartDesign::Body':
            return obj
    return None

def is_sketch_mapped(sketch):
    if sketch.TypeId != 'Sketcher::SketchObject':
        return True
    return hasattr(sketch, 'MapMode') and sketch.MapMode != 'Deactivated'

def is_sketch_fully_constrained(sketch):
    if sketch.TypeId != 'Sketcher::SketchObject':
        return True
    try:
        return sketch.FullyConstrained
    except:
        return len(sketch.Constraints) > 0

def check_external_references(sketch):
    if sketch.TypeId != 'Sketcher::SketchObject':
        return True
    try:
        return len(sketch.ExternalGeometry) == 0 or all(
            ref for ref in sketch.ExternalGeometry if ref is not None
        )
    except:
        return True

def has_no_errors(doc):
    try:
        doc.recompute()
        return not any(obj.State == 'Invalid' for obj in doc.Objects if hasattr(obj, 'State'))
    except:
        return False

# Perform analysis
results = {{
    "Pad Created": has_pad(doc),
    "Face Available": bool(get_available_faces(doc)),
    "Active Body": get_active_body(doc) is not None,
    "Sketch Plane Ready": all(is_sketch_mapped(obj) for obj in doc.Objects if obj.TypeId == 'Sketcher::SketchObject'),
    "Constrained Base Sketch": all(is_sketch_fully_constrained(obj) for obj in doc.Objects if obj.TypeId == 'Sketcher::SketchObject'),
    "Safe References": all(check_external_references(obj) for obj in doc.Objects if obj.TypeId == 'Sketcher::SketchObject'),
    "No Errors": has_no_errors(doc)
}}

analysis_data = {{
    "status": "success",
    "analysis": results,
    "document": doc.Name,
    "object_count": len(doc.Objects),
    "objects": [{{"name": obj.Name, "type": obj.TypeId}} for obj in doc.Objects]
}}

print("ANALYSIS_RESULT:" + json.dumps(analysis_data))
"""

        result = self.api_client._execute_via_subprocess(analysis_script)

        if result["status"] == "success":
            # Extract analysis result from output
            for line in result["message"].split("\n"):
                if line.startswith("ANALYSIS_RESULT:"):
                    try:
                        return json.loads(line.replace("ANALYSIS_RESULT:", ""))
                    except json.JSONDecodeError:
                        pass

        return {"error": "Failed to analyze document via subprocess"}

    def _has_pad(self, doc):
        """Check if document has any Pad objects"""
        return any(obj.TypeId == "PartDesign::Pad" for obj in doc.Objects)

    def _get_available_faces(self, doc):
        """Get all available faces in the document"""
        faces = []
        for obj in doc.Objects:
            if hasattr(obj, "Shape") and obj.Shape:
                if hasattr(obj.Shape, "Faces"):
                    faces.extend(obj.Shape.Faces)
        return faces

    def _get_active_body(self, doc):
        """Get the active body in the document"""
        for obj in doc.Objects:
            if obj.TypeId == "PartDesign::Body":
                return obj
        return None

    def _all_sketches_mapped(self, doc):
        """Check if all sketches are properly mapped to planes"""
        sketches = [
            obj for obj in doc.Objects if obj.TypeId == "Sketcher::SketchObject"
        ]
        if not sketches:
            return True
        return all(self._is_sketch_mapped(sketch) for sketch in sketches)

    def _is_sketch_mapped(self, sketch):
        """Check if a sketch is mapped to a plane"""
        if sketch.TypeId != "Sketcher::SketchObject":
            return True
        return hasattr(sketch, "MapMode") and sketch.MapMode != "Deactivated"

    def _all_sketches_constrained(self, doc):
        """Check if all sketches are fully constrained"""
        sketches = [
            obj for obj in doc.Objects if obj.TypeId == "Sketcher::SketchObject"
        ]
        if not sketches:
            return True
        return all(self._is_sketch_fully_constrained(sketch) for sketch in sketches)

    def _is_sketch_fully_constrained(self, sketch):
        """Check if a sketch is fully constrained"""
        if sketch.TypeId != "Sketcher::SketchObject":
            return True
        try:
            return sketch.FullyConstrained
        except:
            return len(sketch.Constraints) > 0

    def _all_references_safe(self, doc):
        """Check if all external references are safe"""
        sketches = [
            obj for obj in doc.Objects if obj.TypeId == "Sketcher::SketchObject"
        ]
        if not sketches:
            return True
        return all(self._check_external_references(sketch) for sketch in sketches)

    def _check_external_references(self, sketch):
        """Check if external references are safe"""
        if sketch.TypeId != "Sketcher::SketchObject":
            return True
        try:
            return len(sketch.ExternalGeometry) == 0 or all(
                ref for ref in sketch.ExternalGeometry if ref is not None
            )
        except:
            return True

    def _has_no_errors(self, doc):
        """Check if document has no errors"""
        try:
            doc.recompute()
            return not any(
                obj.State == "Invalid" for obj in doc.Objects if hasattr(obj, "State")
            )
        except:
            return False

    def print_analysis_results(self, analysis_data):
        """Print analysis results in a formatted way"""
        if "error" in analysis_data:
            print(f"❌ Error: {analysis_data['error']}")
            return

        if "analysis" not in analysis_data:
            print("❌ No analysis data available")
            return

        print("\n" + "=" * 50)
        print("🔍 FreeCAD Document Analysis")
        print("=" * 50)

        if "document" in analysis_data:
            print(f"📄 Document: {analysis_data['document']}")
            print(f"📊 Objects: {analysis_data.get('object_count', 0)}")

        print("\n📋 State Analysis:")
        print("-" * 30)

        results = analysis_data["analysis"]
        for key, value in results.items():
            status_icon = "✅" if value else "❌"
            print(f"{key}: {status_icon}")

        if "objects" in analysis_data and analysis_data["objects"]:
            print(f"\n🏗️  Objects in Document:")
            print("-" * 30)
            for obj in analysis_data["objects"]:
                print(f"  • {obj['name']} ({obj['type']})")

        print("=" * 50)
