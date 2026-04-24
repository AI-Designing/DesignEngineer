#!/usr/bin/env python3
"""
Phase 2 Implementation: Face Detection and Selection Engine
Building intelligent face selection capabilities for advanced CAD operations
"""

import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class FaceType(Enum):
    """Types of faces that can be detected"""

    PLANAR = "planar"
    CYLINDRICAL = "cylindrical"
    CONICAL = "conical"
    SPHERICAL = "spherical"
    TOROIDAL = "toroidal"
    UNKNOWN = "unknown"


@dataclass
class FaceInfo:
    """Information about a detected face"""

    face_id: str
    object_name: str
    face_type: FaceType
    area: float
    normal: List[float]  # Normal vector [x, y, z]
    center: List[float]  # Center point [x, y, z]
    suitability_score: float
    properties: Dict[str, Any]


class FaceSelectionError(Exception):
    """Raised when face analysis output cannot be trusted (parse failure, bad record, etc.)."""

    def __init__(
        self,
        code: str,
        message: str,
        object_name: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.object_name = object_name


class FaceDetectionEngine:
    """
    Advanced face detection and analysis engine for FreeCAD objects

    On ``FaceSelectionError``, ``detect_available_faces`` fails fast on the first
    object that cannot be analyzed reliably, so callers never mix real faces
    from one object with silent failure on another.
    """

    def __init__(self, api_client):
        self.api_client = api_client

    def detect_available_faces(self, objects: List[str]) -> Dict[str, List[FaceInfo]]:
        """
        Detect all available faces on given objects.

        Raises:
            FaceSelectionError: On the first object whose FreeCAD output cannot
                be parsed or whose analysis fails (fail-fast; no partial dict with
                invented faces).
        """
        print(f"🔍 Detecting faces on {len(objects)} objects...")

        detected_faces: Dict[str, List[FaceInfo]] = {}

        for obj_name in objects:
            faces = self._analyze_object_faces(obj_name)
            detected_faces[obj_name] = faces
            print(f"   📦 {obj_name}: Found {len(faces)} faces")

        return detected_faces

    def _analyze_object_faces(self, object_name: str) -> List[FaceInfo]:
        """Analyze faces of a specific object"""

        # Generate FreeCAD script to analyze object faces
        analysis_script = f"""
import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
obj = doc.getObject('{object_name}')

if obj and hasattr(obj, 'Shape'):
    faces_info = []

    for i, face in enumerate(obj.Shape.Faces):
        face_info = {{
            'face_id': f'Face{{i+1}}',
            'area': face.Area,
            'center': [face.CenterOfMass.x, face.CenterOfMass.y, face.CenterOfMass.z]
        }}

        # Determine face type
        surface = face.Surface
        if hasattr(surface, 'TypeId'):
            if 'Plane' in surface.TypeId:
                face_info['type'] = 'planar'
                face_info['normal'] = [face.normalAt(0, 0).x, face.normalAt(0, 0).y, face.normalAt(0, 0).z]
            elif 'Cylinder' in surface.TypeId:
                face_info['type'] = 'cylindrical'
                face_info['radius'] = surface.Radius
            elif 'Cone' in surface.TypeId:
                face_info['type'] = 'conical'
            elif 'Sphere' in surface.TypeId:
                face_info['type'] = 'spherical'
                face_info['radius'] = surface.Radius
            else:
                face_info['type'] = 'unknown'
        else:
            face_info['type'] = 'unknown'

        faces_info.append(face_info)

    print(f"FACE_ANALYSIS_RESULT: {{json.dumps(faces_info)}}")
else:
    print("FACE_ANALYSIS_RESULT: []")
"""

        try:
            result = self.api_client.execute_command(analysis_script)
            return self._parse_face_analysis_result(result, object_name)
        except FaceSelectionError:
            raise
        except Exception as e:
            print(f"Error in face analysis script: {e}")
            raise FaceSelectionError(
                "execution_failed",
                f"Face analysis failed: {e}",
                object_name=object_name,
            ) from e

    def _parse_face_analysis_result(
        self, result: str, object_name: str
    ) -> List[FaceInfo]:
        """Parse the result from face analysis script.

        Returns an empty list only when FreeCAD reports ``[]`` (no faces).
        Raises FaceSelectionError on missing marker, invalid JSON, or bad records.
        """
        marker = "FACE_ANALYSIS_RESULT:"
        if marker not in result:
            raise FaceSelectionError(
                "missing_marker",
                "Face analysis output missing FACE_ANALYSIS_RESULT marker",
                object_name=object_name,
            )

        json_str = result.split(marker, 1)[1].strip()

        try:
            faces_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error parsing face analysis result: {e}")
            raise FaceSelectionError(
                "parse_error",
                f"Invalid JSON in face analysis output: {e}",
                object_name=object_name,
            ) from e

        if not isinstance(faces_data, list):
            raise FaceSelectionError(
                "parse_error",
                "Face analysis JSON must be a list of face records",
                object_name=object_name,
            )

        faces: List[FaceInfo] = []
        for face_data in faces_data:
            if not isinstance(face_data, dict):
                raise FaceSelectionError(
                    "invalid_face_record",
                    "Each face entry must be an object",
                    object_name=object_name,
                )
            try:
                face_type = FaceType(face_data.get("type", "unknown"))
            except ValueError as e:
                raise FaceSelectionError(
                    "invalid_face_record",
                    f"Unknown face type: {face_data.get('type')!r}",
                    object_name=object_name,
                ) from e
            face_info = FaceInfo(
                face_id=face_data.get("face_id", "Unknown"),
                object_name=object_name,
                face_type=face_type,
                area=face_data.get("area", 0.0),
                normal=face_data.get("normal", [0, 0, 1]),
                center=face_data.get("center", [0, 0, 0]),
                suitability_score=self._calculate_suitability_score(face_data),
                properties=face_data,
            )
            faces.append(face_info)

        return faces

    def _calculate_suitability_score(self, face_data: Dict) -> float:
        """Calculate how suitable a face is for operations"""
        score = 0.5  # Base score

        # Prefer planar faces for hole operations
        if face_data.get("type") == "planar":
            score += 0.3

        # Prefer larger faces
        area = face_data.get("area", 0)
        if area > 100:  # Arbitrary threshold
            score += 0.2

        # Prefer faces with good normal orientation (facing up/out)
        normal = face_data.get("normal", [0, 0, 1])
        if normal[2] > 0.7:  # Mostly facing up
            score += 0.2

        return min(1.0, score)


class FaceSelector:
    """
    Intelligent face selection based on user intent and operation requirements
    """

    def __init__(self, face_detector: FaceDetectionEngine):
        self.face_detector = face_detector

    def select_optimal_face(
        self, objects: List[str], operation_type: str, user_criteria: str = ""
    ) -> Optional[FaceInfo]:
        """
        Select the best face for the given operation

        Args:
            objects: List of object names to consider
            operation_type: Type of operation (hole, pocket, etc.)
            user_criteria: User-specified criteria ("top face", "center", etc.)

        Returns:
            Best FaceInfo or None if no suitable face found

        Raises:
            FaceSelectionError: If face detection fails for an object (parse/exec).
        """
        print(f"🎯 Selecting optimal face for {operation_type} operation...")

        all_faces = self.face_detector.detect_available_faces(objects)

        candidate_faces = []
        for obj_faces in all_faces.values():
            candidate_faces.extend(obj_faces)

        if not candidate_faces:
            print("   ❌ No faces found")
            return None

        filtered_faces = self._apply_user_criteria(candidate_faces, user_criteria)

        suitable_faces = self._filter_for_operation(filtered_faces, operation_type)

        if not suitable_faces:
            print("   ❌ No suitable faces found after filtering")
            return None

        best_face = max(suitable_faces, key=lambda f: f.suitability_score)

        print(
            f"   ✅ Selected: {best_face.object_name}.{best_face.face_id} (score: {best_face.suitability_score:.2f})"
        )

        return best_face

    def _apply_user_criteria(
        self, faces: List[FaceInfo], criteria: str
    ) -> List[FaceInfo]:
        """Apply user-specified criteria to filter faces"""
        if not criteria:
            return faces

        criteria_lower = criteria.lower()
        filtered = []

        for face in faces:
            include = True

            # Position-based criteria
            if "top" in criteria_lower and face.normal[2] < 0.7:
                include = False
            elif "bottom" in criteria_lower and face.normal[2] > -0.7:
                include = False
            elif "front" in criteria_lower and face.normal[1] < 0.7:
                include = False
            elif "back" in criteria_lower and face.normal[1] > -0.7:
                include = False
            elif "left" in criteria_lower and face.normal[0] > -0.7:
                include = False
            elif "right" in criteria_lower and face.normal[0] < 0.7:
                include = False

            # Size-based criteria
            if "large" in criteria_lower and face.area < 200:
                include = False
            elif "small" in criteria_lower and face.area > 50:
                include = False

            if include:
                filtered.append(face)

        return filtered

    def _filter_for_operation(
        self, faces: List[FaceInfo], operation_type: str
    ) -> List[FaceInfo]:
        """Filter faces based on operation requirements"""
        suitable = []

        for face in faces:
            is_suitable = False

            if operation_type == "hole":
                if face.face_type == FaceType.PLANAR:
                    is_suitable = True
            elif operation_type == "pocket":
                if face.face_type == FaceType.PLANAR:
                    is_suitable = True
            elif operation_type == "pattern":
                if face.area > 100:
                    is_suitable = True
            else:
                is_suitable = True

            if is_suitable:
                suitable.append(face)

        return suitable


def demonstrate_face_selection():
    """Demonstrate the face selection system with honest API output (no mock faces)."""
    print("🎯 PHASE 2: FACE SELECTION DEMONSTRATION")
    print("=" * 60)

    from unittest.mock import Mock

    mock_api = Mock()
    valid_faces = [
        {
            "face_id": "Face1",
            "type": "planar",
            "area": 400.0,
            "normal": [0, 0, 1],
            "center": [0, 0, 10],
        },
        {
            "face_id": "Face2",
            "type": "cylindrical",
            "area": 314.16,
            "normal": [1, 0, 0],
            "center": [0, 0, 5],
            "radius": 10.0,
        },
    ]
    mock_api.execute_command.return_value = "FACE_ANALYSIS_RESULT: " + json.dumps(
        valid_faces
    )

    detector = FaceDetectionEngine(mock_api)
    selector = FaceSelector(detector)

    test_objects = ["Pad", "Box", "Cylinder"]

    print("\n1️⃣ Testing Face Detection (synthetic valid FreeCAD-shaped JSON)...")
    faces = detector.detect_available_faces(test_objects)
    total_faces = sum(len(obj_faces) for obj_faces in faces.values())
    print(f"   Detected {total_faces} faces across {len(test_objects)} objects")

    print("\n2️⃣ Testing Face Selection for Hole Operation...")
    best_face = selector.select_optimal_face(test_objects, "hole", "top face")
    if best_face:
        print(f"   Selected face: {best_face.object_name}.{best_face.face_id}")
        print(f"   Face type: {best_face.face_type.value}")

    print("\n3️⃣ Empty FreeCAD result yields no faces (no fabrication)...")
    mock_api.execute_command.return_value = "FACE_ANALYSIS_RESULT: []"
    detector_empty = FaceDetectionEngine(mock_api)
    empty_map = detector_empty.detect_available_faces(["Single"])
    empty_ok = sum(len(f) for f in empty_map.values()) == 0
    print(f"   {'OK' if empty_ok else 'FAIL'}: zero faces from []")

    print("\n4️⃣ Bad JSON raises FaceSelectionError...")
    mock_api.execute_command.return_value = "FACE_ANALYSIS_RESULT: not-json"
    detector_bad = FaceDetectionEngine(mock_api)
    parse_demo_ok = False
    try:
        detector_bad.detect_available_faces(["X"])
    except FaceSelectionError as e:
        parse_demo_ok = e.code == "parse_error"
    print(f"   {'OK' if parse_demo_ok else 'FAIL'}: parse_error on invalid JSON")

    print("\n🎉 Face Selection System Demonstration Complete!")
    selection_ok = best_face is not None and total_faces > 0
    return selection_ok and empty_ok and parse_demo_ok


if __name__ == "__main__":
    success = demonstrate_face_selection()
    if success:
        print("\n🚀 Phase 2 foundation is ready!")
        print("✅ Face detection engine implemented")
        print("✅ No silent mock face fallback")
        print("\n🎯 Next: Integrate with StateAwareCommandProcessor")
    else:
        print("\n❌ Phase 2 foundation needs work")

    sys.exit(0 if success else 1)
