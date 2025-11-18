from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta

from app.services.fingrid_service import fingrid_service
from app.services.cache_service import cache_service
from app.models.energy import EnergyData, DifferentialAnalysis, DifferentialPoint

logger = logging.getLogger(__name__)
router = APIRouter()

def generate_cache_key(endpoint: str, params: Dict[str, Any] = None) -> str:
    """Generate cache key for endpoint"""
    if params:
        param_str = "_".join(f"{k}_{v}" for k, v in sorted(params.items()))
        return f"fingrid_{endpoint}_{param_str}"
    return f"fingrid_{endpoint}"

@router.get("/consumption/realtime", response_model=EnergyData)
async def get_realtime_consumption():
    """Get real-time electricity consumption data"""
    try:
        data = await fingrid_service.get_consumption_realtime()
        logger.info(f"Fetched consumption data: {len(data.data)} points")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch consumption data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch consumption data")

@router.get("/production/realtime", response_model=EnergyData)
async def get_realtime_production():
    """Get real-time electricity production data"""
    try:
        data = await fingrid_service.get_production_realtime()
        logger.info(f"Fetched production data: {len(data.data)} points")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch production data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch production data")

@router.get("/wind/realtime", response_model=EnergyData)
async def get_wind_production():
    """Get real-time wind power production data"""
    try:
        data = await fingrid_service.get_wind_production()
        return data
    except Exception as e:
        logger.error(f"Failed to fetch wind data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wind power data")

@router.get("/consumption/forecast", response_model=EnergyData)
async def get_consumption_forecast():
    """Get 24-hour electricity consumption forecast"""
    try:
        data = await fingrid_service.get_consumption_forecast()
        return data
    except Exception as e:
        logger.error(f"Failed to fetch forecast data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch consumption forecast")

@router.get("/differential", response_model=DifferentialAnalysis)
async def get_production_consumption_differential():
    """Calculate and return production vs consumption differential analysis"""
    try:
        analysis = await fingrid_service.get_differential_analysis()
        return analysis
    except Exception as e:
        logger.error(f"Failed to calculate differential analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate differential analysis")

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data():
    """Get all dashboard data in a single request"""
    try:
        results = await fingrid_service.get_all_realtime_data()

        dashboard_data = {
            "consumption_realtime": results.get("consumption"),
            "production_realtime": results.get("production"),
            "wind_production": results.get("wind"),
            "consumption_forecast": results.get("forecast"),
            "last_updated": datetime.utcnow().isoformat(),
            "status": "success"
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"Failed to fetch dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")