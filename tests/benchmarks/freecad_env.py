"""Detect FreeCAD CLI suitable for HeadlessRunner ``-c script.py`` execution."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _version_ok(cmd: str) -> bool:
    try:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def resolve_benchmark_freecad_cli() -> Optional[str]:
    """
    Return a FreeCAD executable that works with ``[cmd, '-c', script.py]``.

    Excludes snap ``freecad`` (typically incompatible with console ``-c`` runs).
    Preference: ``freecadcmd`` / ``FreeCADCmd``, then ``FREECAD_PATH`` if it
    points at an existing file (e.g. AppRun or extracted ``freecadcmd``).

    The generic ``freecad`` GUI binary is intentionally excluded: snap and
    some AppImage builds do not support ``-c script.py`` the way HeadlessRunner
    expects.
    """
    for name in ("freecadcmd", "FreeCADCmd"):
        resolved = shutil.which(name)
        if resolved and _version_ok(resolved):
            return resolved

    env_path = os.getenv("FREECAD_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return str(p)

    return None


def is_freecad_available() -> bool:
    """Backward-compatible name: True if benchmarks can run a real subprocess."""
    return resolve_benchmark_freecad_cli() is not None
