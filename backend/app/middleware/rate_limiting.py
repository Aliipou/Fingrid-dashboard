# backend/app/middleware/rate_limiting.py
import time
import asyncio
from typing import Dict, List
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict, deque
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with multiple strategies"""
    
    def __init__(
        self, 
        app,
        requests_per_minute: int = 100,
        requests_per_hour: int = 1000,
        burst_limit: int = 20,
        burst_window: int = 10  # seconds
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.burst_window = burst_window
        
        # Storage for rate limiting data
        self.minute_requests = defaultdict(lambda: deque())
        self.hour_requests = defaultdict(lambda: deque())
        self.burst_requests = defaultdict(lambda: deque())
        
        # Whitelist for internal services
        self.whitelist_ips = {'127.0.0.1', '::1', 'localhost'}
        
        # Different limits for different endpoints
        self.endpoint_limits = {
            '/api/v1/export/': {'requests_per_minute': 10, 'requests_per_hour': 100},
            '/api/v1/analytics/': {'requests_per_minute': 30, 'requests_per_hour': 300},
        }
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Skip rate limiting for whitelisted IPs
        if client_id in self.whitelist_ips:
            return await call_next(request)
        
        # Check rate limits
        try:
            self._check_rate_limits(request, client_id)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "Rate limit exceeded",
                    "detail": e.detail,
                    "retry_after": self._get_retry_after(client_id)
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": str(self._get_remaining_requests(client_id)),
                    "X-RateLimit-Reset": str(self._get_reset_time()),
                    "Retry-After": str(self._get_retry_after(client_id))
                }
            )
        
        # Record request
        self._record_request(client_id)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(self._get_remaining_requests(client_id))
        response.headers["X-RateLimit-Reset"] = str(self._get_reset_time())
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get real IP from headers (for proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host
    
    def _check_rate_limits(self, request: Request, client_id: str):
        """Check all rate limits for the client"""
        current_time = datetime.utcnow()
        endpoint = request.url.path
        
        # Get endpoint-specific limits or use defaults
        limits = self.endpoint_limits.get(endpoint, {
            'requests_per_minute': self.requests_per_minute,
            'requests_per_hour': self.requests_per_hour
        })
        
        # Check burst limit (short-term)
        burst_cutoff = current_time - timedelta(seconds=self.burst_window)
        recent_burst_requests = [
            req_time for req_time in self.burst_requests[client_id]
            if req_time > burst_cutoff
        ]
        
        if len(recent_burst_requests) >= self.burst_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Burst limit exceeded: {self.burst_limit} requests per {self.burst_window} seconds"
            )
        
        # Check minute limit
        minute_cutoff = current_time - timedelta(minutes=1)
        recent_minute_requests = [
            req_time for req_time in self.minute_requests[client_id]
            if req_time > minute_cutoff
        ]
        
        if len(recent_minute_requests) >= limits['requests_per_minute']:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limits['requests_per_minute']} requests per minute"
            )
        
        # Check hour limit
        hour_cutoff = current_time - timedelta(hours=1)
        recent_hour_requests = [
            req_time for req_time in self.hour_requests[client_id]
            if req_time > hour_cutoff
        ]
        
        if len(recent_hour_requests) >= limits['requests_per_hour']:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limits['requests_per_hour']} requests per hour"
            )
    
    def _record_request(self, client_id: str):
        """Record a request for rate limiting"""
        current_time = datetime.utcnow()
        
        # Record in all time windows
        self.burst_requests[client_id].append(current_time)
        self.minute_requests[client_id].append(current_time)
        self.hour_requests[client_id].append(current_time)
        
        # Clean old requests periodically
        self._cleanup_old_requests(client_id)
    
    def _cleanup_old_requests(self, client_id: str):
        """Remove old requests from memory"""
        current_time = datetime.utcnow()
        
        # Clean burst requests
        burst_cutoff = current_time - timedelta(seconds=self.burst_window * 2)
        self.burst_requests[client_id] = deque([
            req_time for req_time in self.burst_requests[client_id]
            if req_time > burst_cutoff
        ])
        
        # Clean minute requests
        minute_cutoff = current_time - timedelta(minutes=2)
        self.minute_requests[client_id] = deque([
            req_time for req_time in self.minute_requests[client_id]
            if req_time > minute_cutoff
        ])
        
        # Clean hour requests
        hour_cutoff = current_time - timedelta(hours=2)
        self.hour_requests[client_id] = deque([
            req_time for req_time in self.hour_requests[client_id]
            if req_time > hour_cutoff
        ])
    
    def _get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for the current minute"""
        current_time = datetime.utcnow()
        minute_cutoff = current_time - timedelta(minutes=1)
        
        recent_requests = len([
            req_time for req_time in self.minute_requests[client_id]
            if req_time > minute_cutoff
        ])
        
        return max(0, self.requests_per_minute - recent_requests)
    
    def _get_reset_time(self) -> int:
        """Get timestamp when rate limit resets"""
        current_time = datetime.utcnow()
        next_minute = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        return int(next_minute.timestamp())
    
    def _get_retry_after(self, client_id: str) -> int:
        """Get seconds to wait before retrying"""
        current_time = datetime.utcnow()
        
        # Find the oldest request in the current minute window
        minute_cutoff = current_time - timedelta(minutes=1)
        recent_requests = [
            req_time for req_time in self.minute_requests[client_id]
            if req_time > minute_cutoff
        ]
        
        if not recent_requests or len(recent_requests) < self.requests_per_minute:
            return 1  # Can retry in 1 second
        
        # Calculate when the oldest request will be outside the window
        oldest_request = min(recent_requests)
        retry_time = oldest_request + timedelta(minutes=1)
        wait_seconds = (retry_time - current_time).total_seconds()
        
        return max(1, int(wait_seconds))
    
    def get_client_stats(self, client_id: str) -> dict:
        """Get rate limiting statistics for a client"""
        current_time = datetime.utcnow()
        
        # Count recent requests
        minute_cutoff = current_time - timedelta(minutes=1)
        hour_cutoff = current_time - timedelta(hours=1)
        burst_cutoff = current_time - timedelta(seconds=self.burst_window)
        
        minute_count = len([
            req_time for req_time in self.minute_requests[client_id]
            if req_time > minute_cutoff
        ])
        
        hour_count = len([
            req_time for req_time in self.hour_requests[client_id]
            if req_time > hour_cutoff
        ])
        
        burst_count = len([
            req_time for req_time in self.burst_requests[client_id]
            if req_time > burst_cutoff
        ])
        
        return {
            "client_id": client_id,
            "requests_last_minute": minute_count,
            "requests_last_hour": hour_count,
            "requests_burst_window": burst_count,
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
            "burst_limit": self.burst_limit,
            "remaining_minute": max(0, self.requests_per_minute - minute_count),
            "remaining_hour": max(0, self.requests_per_hour - hour_count),
            "reset_time": self._get_reset_time(),
            "retry_after": self._get_retry_after(client_id)
        }
    
    def get_global_stats(self) -> dict:
        """Get global rate limiting statistics"""
        current_time = datetime.utcnow()
        minute_cutoff = current_time - timedelta(minutes=1)
        
        total_clients = len(self.minute_requests)
        total_requests_minute = sum(
            len([req for req in requests if req > minute_cutoff])
            for requests in self.minute_requests.values()
        )
        
        # Find top clients by request count
        client_request_counts = {}
        for client_id, requests in self.minute_requests.items():
            recent_count = len([req for req in requests if req > minute_cutoff])
            if recent_count > 0:
                client_request_counts[client_id] = recent_count
        
        top_clients = sorted(
            client_request_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_active_clients": total_clients,
            "total_requests_last_minute": total_requests_minute,
            "top_clients": [
                {"client_id": client_id, "requests": count}
                for client_id, count in top_clients
            ],
            "rate_limit_config": {
                "requests_per_minute": self.requests_per_minute,
                "requests_per_hour": self.requests_per_hour,
                "burst_limit": self.burst_limit,
                "burst_window_seconds": self.burst_window
            }
        }
