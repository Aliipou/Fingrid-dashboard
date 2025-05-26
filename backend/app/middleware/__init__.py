# backend/app/middleware/__init__.py
"""
Middleware package for Fingrid Dashboard API
===========================================

Contains middleware for:
- Performance monitoring
- Rate limiting
- Security headers
- Request logging
"""

from .monitoring import PerformanceMonitoringMiddleware
from .rate_limiting import RateLimitMiddleware

__all__ = [
    "PerformanceMonitoringMiddleware",
    "RateLimitMiddleware"
]


# Additional utility middleware
# backend/app/middleware/security.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# backend/app/middleware/cors_custom.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class CustomCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with advanced features"""
    
    def __init__(self, app, allowed_origins: list = None, max_age: int = 3600):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        self.max_age = max_age
        self.allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]
        self.allowed_headers = ["*"]
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response
        
        # Process normal request
        response = await call_next(request)
        self._add_cors_headers(response, origin)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: str = None):
        """Add CORS headers to response"""
        # Check if origin is allowed
        if origin and (self.allowed_origins == ["*"] or origin in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif self.allowed_origins == ["*"]:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        response.headers["Access-Control-Allow-Credentials"] = "true"