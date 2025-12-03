"""
API v1 Router

Main router for API version 1 endpoints.
"""

from fastapi import APIRouter

router = APIRouter()

from .endpoints import health, encounters, transcription, soap, reports, auth

# Include sub-routers
router.include_router(health.router, tags=["Health"])
router.include_router(encounters.router, prefix="/encounters", tags=["Encounters"])
router.include_router(transcription.router, prefix="/transcribe", tags=["Transcription"])
router.include_router(soap.router, prefix="/soap", tags=["SOAP Notes"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
router.include_router(auth.router, tags=["Authentication"])


@router.get("/")
async def api_root():
    """API v1 root endpoint"""
    return {
        "version": "1.0",
        "endpoints": [
            "/health",
            "/transcribe",
            "/soap",
            "/encounters",
            "/reports",
            "/auth"
        ]
    }
