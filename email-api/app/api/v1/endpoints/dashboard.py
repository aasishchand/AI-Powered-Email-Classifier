"""Dashboard metrics and trends endpoints — queries real synced email data."""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.metrics import DashboardMetrics, EmailTrend
from app.services.analytics_service import (
    get_dashboard_metrics,
    get_email_trends,
    get_email_heatmap,
)

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetrics)
async def dashboard_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated dashboard metrics for the current user (real data)."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    return await get_dashboard_metrics(db, current_user["id"], start_date, end_date)


@router.get("/trends", response_model=List[EmailTrend])
async def dashboard_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily email volume trends for time series visualization (real data)."""
    return await get_email_trends(db, current_user["id"], days)


@router.get("/heatmap")
async def dashboard_heatmap(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get email volume heatmap data (hour vs day of week) from real data."""
    data = await get_email_heatmap(db, current_user["id"])
    return {"data": data}
