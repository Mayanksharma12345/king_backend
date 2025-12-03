"""Health check endpoints"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready", "service": "medical-scribe-ai"}


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "service": "medical-scribe-ai"}
