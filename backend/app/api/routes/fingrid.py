from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta

from app.services.fingrid_client import FingridClient
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
    cache_key = generate_cache_key("consumption_realtime")
    
    # Try cache first
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        logger.info("Returning cached consumption data")
        return cached_data
    
    # Fetch from API
    try:
        async with FingridClient() as client:
            data = await client.get_realtime_consumption()
            await cache_service.set(cache_key, data, ttl=300)  # 5 min cache
            logger.info(f"Fetched consumption data: {len(data.data)} points")
            return data
    except Exception as e:
        logger.error(f"Failed to fetch consumption data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch consumption data")

@router.get("/production/realtime", response_model=EnergyData)
async def get_realtime_production():
    """Get real-time electricity production data"""
    cache_key = generate_cache_key("production_realtime")
    
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        logger.info("Returning cached production data")
        return cached_data
    
    try:
        async with FingridClient() as client:
            data = await client.get_realtime_production()
            await cache_service.set(cache_key, data, ttl=300)
            logger.info(f"Fetched production data: {len(data.data)} points")
            return data
    except Exception as e:
        logger.error(f"Failed to fetch production data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch production data")

@router.get("/wind/realtime", response_model=EnergyData)
async def get_wind_production():
    """Get real-time wind power production data"""
    cache_key = generate_cache_key("wind_realtime")
    
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        async with FingridClient() as client:
            data = await client.get_wind_production()
            await cache_service.set(cache_key, data, ttl=300)
            return data
    except Exception as e:
        logger.error(f"Failed to fetch wind data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wind power data")

@router.get("/consumption/forecast", response_model=EnergyData)
async def get_consumption_forecast():
    """Get 24-hour electricity consumption forecast"""
    cache_key = generate_cache_key("consumption_forecast")
    
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        async with FingridClient() as client:
            data = await client.get_consumption_forecast()
            await cache_service.set(cache_key, data, ttl=600)  # 10 min cache for forecast
            return data
    except Exception as e:
        logger.error(f"Failed to fetch forecast data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch consumption forecast")

@router.get("/differential", response_model=DifferentialAnalysis)
async def get_production_consumption_differential():
    """Calculate and return production vs consumption differential analysis"""
    cache_key = generate_cache_key("differential_analysis")
    
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        async with FingridClient() as client:
            # Get both production and consumption data
            results = await client.get_all_realtime_data()
            
            if not results.get("production") or not results.get("consumption"):
                raise HTTPException(status_code=500, detail="Missing production or consumption data")
            
            production_data = results["production"]
            consumption_data = results["consumption"]
            
            # Align timestamps and calculate differentials
            differential_points = []
            
            # Create timestamp-indexed dictionaries for efficient lookup
            prod_dict = {point.timestamp: point.value for point in production_data.data}
            cons_dict = {point.timestamp: point.value for point in consumption_data.data}
            
            # Find common timestamps
            common_timestamps = set(prod_dict.keys()) & set(cons_dict.keys())
            
            total_surplus = 0
            total_deficit = 0
            balanced_count = 0
            
            for timestamp in sorted(common_timestamps):
                production = prod_dict[timestamp]
                consumption = cons_dict[timestamp]
                differential = production - consumption
                
                # Determine status
                if abs(differential) < (consumption * 0.02):  # Within 2%
                    status = "balanced"
                    balanced_count += 1
                elif differential > 0:
                    status = "surplus"
                    total_surplus += differential
                else:
                    status = "deficit"
                    total_deficit += abs(differential)
                
                percentage = (differential / consumption * 100) if consumption > 0 else 0
                
                differential_points.append(DifferentialPoint(
                    timestamp=timestamp,
                    production=production,
                    consumption=consumption,
                    differential=differential,
                    status=status,
                    percentage=percentage
                ))
            
            # Calculate summary statistics
            total_points = len(differential_points)
            avg_differential = sum(p.differential for p in differential_points) / total_points if total_points > 0 else 0
            
            summary = {
                "average_differential_mw": round(avg_differential, 2),
                "total_surplus_mwh": round(total_surplus, 2),
                "total_deficit_mwh": round(total_deficit, 2),
                "balanced_periods": balanced_count,
                "surplus_periods": sum(1 for p in differential_points if p.status == "surplus"),
                "deficit_periods": sum(1 for p in differential_points if p.status == "deficit"),
                "analysis_period_hours": 24
            }
            
            analysis = DifferentialAnalysis(
                analysis_period="24 hours",
                data=differential_points,
                summary=summary,
                generated_at=datetime.utcnow()
            )
            
            await cache_service.set(cache_key, analysis, ttl=300)
            return analysis
            
    except Exception as e:
        logger.error(f"Failed to calculate differential analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate differential analysis")

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data():
    """Get all dashboard data in a single request"""
    cache_key = generate_cache_key("dashboard_all")
    
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        logger.info("Returning cached dashboard data")
        return cached_data
    
    try:
        async with FingridClient() as client:
            results = await client.get_all_realtime_data()
            
            dashboard_data = {
                "consumption_realtime": results.get("consumption"),
                "production_realtime": results.get("production"),
                "wind_production": results.get("wind"),
                "consumption_forecast": results.get("forecast"),
                "last_updated": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            await cache_service.set(cache_key, dashboard_data, ttl=300)
            return dashboard_data
            
    except Exception as e:
        logger.error(f"Failed to fetch dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")