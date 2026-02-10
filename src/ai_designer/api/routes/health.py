"""
Health check endpoints for monitoring and orchestration.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "freecad-ai-designer",
        "version": "0.1.0",
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for Kubernetes/orchestration.
    
    Verifies that all critical dependencies are available:
    - Redis connection
    - LLM provider access (optional, can degrade gracefully)
    - FreeCAD availability
    
    Returns:
        Readiness status with component checks
    """
    checks = {
        "redis": "unknown",  # TODO: Add actual Redis health check
        "llm": "unknown",    # TODO: Add LLM provider ping
        "freecad": "unknown", # TODO: Add FreeCAD availability check
    }
    
    # For now, return ready (implement actual checks in deps.py)
    overall_status = "ready"
    
    return {
        "status": overall_status,
        "service": "freecad-ai-designer",
        "version": "0.1.0",
        "checks": checks,
    }
