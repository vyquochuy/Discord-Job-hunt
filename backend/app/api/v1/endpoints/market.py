from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.market import MarketAnalyticsResponse
from app.services.analytics.market_analytics import get_market_analytics

router = APIRouter()


@router.get("/analytics", response_model=MarketAnalyticsResponse)
async def market_analytics(db: AsyncSession = Depends(get_db)):
    return await get_market_analytics(db)
