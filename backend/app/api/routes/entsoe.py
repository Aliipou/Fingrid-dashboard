from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime, timedelta
import logging

from app.services.entsoe_service import entsoe_service
from app.services.cache_service import cache_service
from app.models.energy import PriceData

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/prices/tomorrow", response_model=List[PriceData])
async def get_tomorrow_prices():
    """Get tomorrow's day-ahead electricity prices for Finland"""
    try:
        prices = await entsoe_service.get_tomorrow_prices()

        if not prices:
            raise HTTPException(
                status_code=404,
                detail="Tomorrow's prices not yet available"
            )

        logger.info(f"Fetched tomorrow's prices: {len(prices)} hourly points")
        return prices

    except Exception as e:
        logger.error(f"Failed to fetch tomorrow's prices: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch electricity price forecast"
        )

@router.get("/prices/today", response_model=List[PriceData])
async def get_today_prices():
    """Get today's electricity prices for Finland"""
    try:
        prices = await entsoe_service.get_today_prices()

        if not prices:
            raise HTTPException(status_code=404, detail="Today's prices not available")

        return prices

    except Exception as e:
        logger.error(f"Failed to fetch today's prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch today's electricity prices")

@router.get("/prices/week", response_model=List[PriceData])
async def get_week_prices():
    """Get current week's electricity prices for Finland"""
    try:
        # Get a week's worth of prices (7 days from today)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today + timedelta(days=6)

        # Use price statistics endpoint to get weekly data
        stats = await entsoe_service.get_price_statistics(today, end_date)

        # For now, we'll fetch each day individually and combine
        all_prices = []
        current_date = today

        while current_date <= end_date:
            try:
                daily_prices = await entsoe_service.get_day_ahead_prices(current_date)
                all_prices.extend(daily_prices)
            except Exception as e:
                logger.warning(f"Failed to get prices for {current_date.date()}: {str(e)}")

            current_date += timedelta(days=1)

        return all_prices

    except Exception as e:
        logger.error(f"Failed to fetch weekly prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch weekly electricity prices")