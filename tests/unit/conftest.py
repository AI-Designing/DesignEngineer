"""
Unit-test-only hooks: isolate FreeCAD env and resolver singleton.

Project .env may set FREECAD_PATH after ``env -u``; that breaks path resolver
tests that expect tmp paths. Integration tests under ``tests/integration/`` do
not load this conftest.
"""

import pytest


@pytest.fixture(autouse=True)
def _isolate_freecad_path_resolution(monkeypatch):
    monkeypatch.delenv("FREECAD_PATH", raising=False)
    monkeypatch.delenv("FREECADCMD_PATH", raising=False)
    from ai_designer.freecad import path_resolver

    path_resolver._resolver = None
    yield
    path_resolver._resolver = None
