# backend/app/middleware/monitoring.py
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance and health metrics"""
    
    def __init__(self, app, max_requests_per_minute: int = 1000):
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        self.request_counts = defaultdict(lambda: deque())
        self.response_times = deque(maxlen=1000)  # Store last 1000 response times
        self.error_counts = defaultdict(int)
        self.start_time = time.time()
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Record request start time
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host
        
        # Log request
        logger.info(f"Incoming request: {request.method} {request.url.path} from {client_ip}")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Store metrics
            self._record_metrics(request, response, process_time, client_ip)
            
            # Add performance headers
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            response.headers["X-Request-ID"] = str(id(request))
            
            return response
            
        except Exception as e:
            # Record error
            process_time = time.time() - start_time
            self.error_counts["500"] += 1
            
            logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
            
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": str(id(request))},
                headers={"X-Process-Time": str(round(process_time, 4))}
            )
    
    def _record_metrics(self, request: Request, response: Response, process_time: float, client_ip: str):
        """Record performance and usage metrics"""
        # Record response time
        self.response_times.append(process_time)
        
        # Record request count per IP
        current_time = datetime.utcnow()
        self.request_counts[client_ip].append(current_time)
        
        # Clean old requests (older than 1 minute)
        cutoff_time = current_time - timedelta(minutes=1)
        while (self.request_counts[client_ip] and 
               self.request_counts[client_ip][0] < cutoff_time):
            self.request_counts[client_ip].popleft()
        
        # Record status code
        status_code = str(response.status_code)
        if status_code.startswith(('4', '5')):
            self.error_counts[status_code] += 1
        
        # Log slow requests
        if process_time > 5.0:  # 5 seconds threshold
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {process_time:.2f}s from {client_ip}"
            )
    
    def get_metrics(self) -> dict:
        """Get current performance metrics"""
        uptime = time.time() - self.start_time
        
        # Calculate average response time
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        # Calculate current request rates
        total_requests = sum(len(requests) for requests in self.request_counts.values())
        
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests_last_minute": total_requests,
            "average_response_time": round(avg_response_time, 4),
            "max_response_time": round(max(self.response_times), 4) if self.response_times else 0,
            "min_response_time": round(min(self.response_times), 4) if self.response_times else 0,
            "error_counts": dict(self.error_counts),
            "active_ips": len(self.request_counts),
            "memory_metrics": self._get_memory_metrics()
        }
    
    def _get_memory_metrics(self) -> dict:
        """Get memory usage metrics"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "cpu_percent": round(process.cpu_percent(), 2)
            }
        except ImportError:
            return {"error": "psutil not available"}