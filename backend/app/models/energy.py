from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class DatasetType(str, Enum):
    CONSUMPTION_REALTIME = "consumption_realtime"
    PRODUCTION_REALTIME = "production_realtime"
    WIND_PRODUCTION = "wind_production"
    CONSUMPTION_FORECAST = "consumption_forecast"
    PRICE_FORECAST = "price_forecast"

class EnergyDataPoint(BaseModel):
    """Individual energy data point"""
    timestamp: datetime
    value: float
    unit: str = "MW"

class EnergyData(BaseModel):
    """Energy dataset container"""
    dataset_id: int
    name: str
    dataset_type: DatasetType
    data: List[EnergyDataPoint]
    last_updated: datetime
    metadata: Optional[Dict[str, Any]] = None

class DifferentialPoint(BaseModel):
    """Production vs consumption differential point"""
    timestamp: datetime
    production: float
    consumption: float
    differential: float
    status: str = Field(..., description="surplus, deficit, or balanced")
    percentage: float = Field(..., description="Differential as percentage of consumption")

class DifferentialAnalysis(BaseModel):
    """Complete differential analysis"""
    analysis_period: str
    data: List[DifferentialPoint]
    summary: Dict[str, float]
    generated_at: datetime

class PriceData(BaseModel):
    """Electricity price data"""
    timestamp: datetime
    price: float
    unit: str = "EUR/MWh"
    area: str = "FI"

class SystemStatus(BaseModel):
    """System status information"""
    api_status: str
    cache_status: str
    last_data_update: datetime
    active_datasets: List[str]
    uptime_seconds: int