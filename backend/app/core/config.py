from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import secrets

class Settings(BaseSettings):
    """Application settings"""

    # API Keys (REQUIRED)
    FINGRID_API_KEY: str
    ENTSOE_API_KEY: str

    # Security (REQUIRED in production)
    SECRET_KEY: str = secrets.token_urlsafe(32)  # Auto-generate if not provided
    REDIS_PASSWORD: Optional[str] = None

    # Database & Cache
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 300  # 5 minutes

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Application
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # API Configuration
    FINGRID_BASE_URL: str = "https://api.fingrid.fi/v1"
    ENTSOE_BASE_URL: str = "https://web-api.tp.entsoe.eu/api"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_redis_url_with_password(self) -> str:
        """Get Redis URL with password if configured"""
        if self.REDIS_PASSWORD:
            # Parse the URL and add password
            if "://" in self.REDIS_URL:
                protocol, rest = self.REDIS_URL.split("://", 1)
                return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
            return self.REDIS_URL
        return self.REDIS_URL

settings = Settings()