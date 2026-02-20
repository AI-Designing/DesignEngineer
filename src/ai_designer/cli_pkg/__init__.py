"""
FreeCAD CLI package.

This package is the refactored replacement for the monolithic cli.py.
FreeCADCLI is imported from app.py and re-exported here so that existing
callers using 'from ai_designer.cli import FreeCADCLI' continue to work.
"""
# Re-export from app for backward compatibility with any new code targeting
# the cli package.  The legacy cli.py remains as the canonical entry point
# until the full migration is complete.
from ai_designer.cli_pkg.app import FreeCADCLIApp

__all__ = ["FreeCADCLIApp"]
