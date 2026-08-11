"""Dashboard analytics endpoint (requires authentication)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import User
from app.modules.analytics.schemas import AnalyticsOverview
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Aggregate dashboard stats for the signed-in user",
)
async def overview(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AnalyticsOverview:
    return await AnalyticsService(db, user).overview()
