"""Unit tests for face detection / selection (Track 8: no mock face fallback)."""

import json
from unittest.mock import Mock

import pytest

from ai_designer.freecad.face_selection_engine import (
    FaceDetectionEngine,
    FaceSelectionError,
    FaceSelector,
    FaceType,
)


def _engine_with_output(output: str) -> FaceDetectionEngine:
    mock_api = Mock()
    mock_api.execute_command.return_value = output
    return FaceDetectionEngine(mock_api)


class TestParseFaceAnalysisResult:
    def test_empty_json_array_returns_empty_no_mock(self):
        eng = _engine_with_output("FACE_ANALYSIS_RESULT: []")
        faces = eng._parse_face_analysis_result(
            "noise\nFACE_ANALYSIS_RESULT: []\n", "Box"
        )
        assert faces == []
        assert not any(f.face_id == "Face1" and f.center == [0, 0, 10] for f in faces)

    def test_invalid_json_raises_parse_error(self):
        eng = _engine_with_output("")
        with pytest.raises(FaceSelectionError) as exc:
            eng._parse_face_analysis_result("FACE_ANALYSIS_RESULT: not-json", "Box")
        assert exc.value.code == "parse_error"
        assert exc.value.object_name == "Box"

    def test_missing_marker_raises(self):
        eng = _engine_with_output("")
        with pytest.raises(FaceSelectionError) as exc:
            eng._parse_face_analysis_result("no marker here", "Part")
        assert exc.value.code == "missing_marker"

    def test_non_list_json_raises_parse_error(self):
        eng = _engine_with_output("")
        with pytest.raises(FaceSelectionError) as exc:
            eng._parse_face_analysis_result(
                'FACE_ANALYSIS_RESULT: {"face_id": "Face1"}', "Box"
            )
        assert exc.value.code == "parse_error"

    def test_invalid_face_type_raises_invalid_face_record(self):
        eng = _engine_with_output("")
        payload = json.dumps(
            [{"face_id": "Face1", "type": "not_a_real_type", "area": 1.0}]
        )
        with pytest.raises(FaceSelectionError) as exc:
            eng._parse_face_analysis_result(f"FACE_ANALYSIS_RESULT: {payload}", "Box")
        assert exc.value.code == "invalid_face_record"

    def test_one_valid_face(self):
        eng = _engine_with_output("")
        payload = json.dumps(
            [
                {
                    "face_id": "Face3",
                    "type": "planar",
                    "area": 250.0,
                    "normal": [0, 0, 1],
                    "center": [1.0, 2.0, 3.0],
                }
            ]
        )
        faces = eng._parse_face_analysis_result(
            f"FACE_ANALYSIS_RESULT: {payload}", "MyPad"
        )
        assert len(faces) == 1
        assert faces[0].face_id == "Face3"
        assert faces[0].object_name == "MyPad"
        assert faces[0].face_type == FaceType.PLANAR
        assert faces[0].center == [1.0, 2.0, 3.0]


class TestDetectAvailableFaces:
    def test_fail_fast_on_second_object_parse_error(self):
        mock_api = Mock()
        good = json.dumps(
            [{"face_id": "Face1", "type": "planar", "area": 100.0, "normal": [0, 0, 1]}]
        )

        def cmd_side_effect(script):
            if "getObject('Good'" in script or 'getObject("Good"' in script:
                return f"FACE_ANALYSIS_RESULT: {good}"
            return "FACE_ANALYSIS_RESULT: {{{invalid"

        mock_api.execute_command.side_effect = cmd_side_effect
        eng = FaceDetectionEngine(mock_api)
        with pytest.raises(FaceSelectionError) as exc:
            eng.detect_available_faces(["Good", "Bad"])
        assert exc.value.code == "parse_error"
        assert exc.value.object_name == "Bad"

    def test_execution_failed_wraps_client_exception(self):
        mock_api = Mock()
        mock_api.execute_command.side_effect = RuntimeError("connection reset")
        eng = FaceDetectionEngine(mock_api)
        with pytest.raises(FaceSelectionError) as exc:
            eng._analyze_object_faces("Any")
        assert exc.value.code == "execution_failed"
        assert exc.value.object_name == "Any"


class TestFaceSelector:
    def test_select_optimal_face_returns_none_when_all_empty(self):
        mock_api = Mock()
        mock_api.execute_command.return_value = "FACE_ANALYSIS_RESULT: []"
        eng = FaceDetectionEngine(mock_api)
        sel = FaceSelector(eng)
        assert sel.select_optimal_face(["A"], "hole", "") is None
