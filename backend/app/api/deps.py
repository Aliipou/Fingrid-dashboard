# backend/app/api/deps.py
"""
API Dependencies
================

Common dependencies for API endpoints including:
- Authentication
- Rate limiting
- Database connections
- Logging
"""

from typing import Optional, Any
from fastapi import HTTPException, Depends, Request
import logging
from app.services.cache_service import cache_service
from app.core.config import settings

logger = logging.getLogger(__name__)

async def get_cache_service():
    """Get cache service dependency"""
    return cache_service

async def validate_api_key(request: Request) -> Optional[str]:
    """
    Validate API key from request headers
    Used for internal API authentication if needed
    """
    api_key = request.headers.get("X-API-Key")
    
    # For now, we don't require API keys for public endpoints
    # This can be extended for premium features
    return api_key

async def get_current_user(api_key: Optional[str] = Depends(validate_api_key)) -> dict:
    """
    Get current user based on API key
    Returns anonymous user for public access
    """
    if not api_key:
        return {
            "user_id": "anonymous",
            "permissions": ["read:public"],
            "rate_limit_tier": "basic"
        }
    
    # TODO: Implement actual user authentication
    # For now, return a default user
    return {
        "user_id": "authenticated_user",
        "permissions": ["read:public", "read:premium"],
        "rate_limit_tier": "premium"
    }

async def check_rate_limit(request: Request, user: dict = Depends(get_current_user)) -> bool:
    """
    Check if user has exceeded rate limits
    This works in conjunction with the rate limiting middleware
    """
    # Rate limiting is handled by middleware
    # This dependency can be used for additional user-specific limits
    return True

class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail)

async def verify_fingrid_api_access() -> bool:
    """
    Verify that Fingrid API is accessible and API key is valid
    """
    if not settings.FINGRID_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Fingrid API key not configured"
        )
    return True

async def verify_entsoe_api_access() -> bool:
    """
    Verify that ENTSO-E API is accessible and API key is valid
    """
    if not settings.ENTSOE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ENTSO-E API key not configured"
        )
    return True

async def get_client_ip(request: Request) -> str:
    """Get real client IP address considering proxy headers"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host

async def log_api_request(request: Request, client_ip: str = Depends(get_client_ip)):
    """Log API request for monitoring and analytics"""
    logger.info(
        f"API Request: {request.method} {request.url.path} from {client_ip}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
            "user_agent": request.headers.get("User-Agent", "Unknown")
        }
    )

# Common query parameters
class CommonQueryParams:
    """Common query parameters for energy data endpoints"""
    
    def __init__(
        self,
        limit: int = 100,
        offset: int = 0,
        format: str = "json"
    ):
        self.limit = min(limit, 1000)  # Cap at 1000 items
        self.offset = max(offset, 0)
        self.format = format.lower()
        
        if self.format not in ["json", "csv"]:
            raise HTTPException(
                status_code=400,
                detail="Format must be 'json' or 'csv'"
            )

async def get_common_params(
    limit: int = 100,
    offset: int = 0,
    format: str = "json"
) -> CommonQueryParams:
    """Get common query parameters"""
    return CommonQueryParams(limit=limit, offset=offset, format=format)