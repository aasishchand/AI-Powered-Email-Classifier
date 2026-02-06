"""Dashboard metrics and trends endpoints."""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.cache import cache_result
from app.models.metrics import DashboardMetrics, EmailTrend
from app.services.analytics_service import get_dashboard_metrics_for_user, get_email_trends_for_user

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetrics)
@cache_result(ttl=300)
async def get_dashboard_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get aggregated dashboard metrics for the current user."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    return get_dashboard_metrics_for_user(
        user_email=current_user["email"],
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/trends", response_model=List[EmailTrend])
@cache_result(ttl=600)
async def get_email_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Get daily email volume trends for time series visualization."""
    return get_email_trends_for_user(
        user_email=current_user["email"],
        days=days,
    )


@router.get("/heatmap")
async def get_email_heatmap(
    current_user: dict = Depends(get_current_user),
):
    """Get email volume heatmap data (hour vs day of week). Mock data."""
    return {
        "data": [
            {"day": d, "hour": h, "volume": (d + h) * 2}
            for d in range(1, 8)
            for h in range(0, 24)
        ]
    }
