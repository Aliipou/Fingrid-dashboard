from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    FINGRID_API_KEY: str
    ENTSOE_API_KEY: str
    
    # Database & Cache
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 300  # 5 minutes
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Application
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    FINGRID_BASE_URL: str = "https://api.fingrid.fi/v1"
    ENTSOE_BASE_URL: str = "https://web-api.tp.entsoe.eu/api"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()