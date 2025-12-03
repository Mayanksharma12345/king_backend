"""Analytics and reporting endpoints"""

from fastapi import APIRouter, Depends
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.analytics import ReportRequest, ReportType
from src.services.reporting_service import ReportingService

router = APIRouter()


@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db)
):
    """Generate analytics report"""
    
    service = ReportingService(db)
    report = await service.generate_report(request, user_id="current_user")
    
    return report


@router.get("/dashboard")
async def get_dashboard_metrics(
    db: Session = Depends(get_db)
):
    """Get real-time dashboard metrics"""
    
    service = ReportingService(db)
    metrics = await service.get_dashboard_metrics()
    
    return metrics
