"""
FastAPI REST API for FreeCAD AI Designer.

Provides endpoints for:
- Design submission and retrieval
- Real-time WebSocket updates
- Health checks and monitoring
"""

from ai_designer.api.app import create_app

__all__ = ["create_app"]
