from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime, timedelta
import logging

from app.services.entsoe_client import EntsoEClient
from app.services.cache_service import cache_service
from app.models.energy import PriceData

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/prices/tomorrow", response_model=List[PriceData])
async def get_tomorrow_prices():
    """Get tomorrow's day-ahead electricity prices for Finland"""
    cache_key = "entsoe_prices_tomorrow"
    
    # Try cache first (longer cache for price data as it's published once daily)
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        logger.info("Returning cached tomorrow price data")
        return cached_data
    
    try:
        async with EntsoEClient() as client:
            tomorrow = datetime.now() + timedelta(days=1)
            prices = await client.get_day_ahead_prices(tomorrow)
            
            if not prices:
                raise HTTPException(
                    status_code=404, 
                    detail="Tomorrow's prices not yet available"
                )
            
            # Cache for 6 hours (prices usually published around 13:00 CET)
            await cache_service.set(cache_key, prices, ttl=21600)
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
    cache_key = "entsoe_prices_today"
    
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        async with EntsoEClient() as client:
            today = datetime.now()
            prices = await client.get_day_ahead_prices(today)
            
            if not prices:
                raise HTTPException(status_code=404, detail="Today's prices not available")
            
            await cache_service.set(cache_key, prices, ttl=3600)  # 1 hour cache
            return prices
            
    except Exception as e:
        logger.error(f"Failed to fetch today's prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch today's electricity prices")

@router.get("/prices/week", response_model=List[PriceData])
async def get_week_prices():
    """Get current week's electricity prices for Finland"""
    cache_key = "entsoe_prices_week"
    
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        async with EntsoEClient() as client:
            prices = await client.get_current_week_prices()
            await cache_service.set(cache_key, prices, ttl=7200)  # 2 hour cache
            return prices
            
    except Exception as e:
        logger.error(f"Failed to fetch weekly prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch weekly electricity prices")