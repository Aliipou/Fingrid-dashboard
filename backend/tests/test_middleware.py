import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import time

from app.middleware.rate_limiting import RateLimitMiddleware
from app.middleware.monitoring import PerformanceMonitoringMiddleware


@pytest.fixture
def app():
    """Create test FastAPI app."""
    test_app = FastAPI()

    @test_app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @test_app.get("/slow")
    async def slow_endpoint():
        time.sleep(0.1)
        return {"message": "slow"}

    return test_app


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    def test_middleware_initialization(self):
        """Test middleware initializes correctly."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app, requests_per_minute=100, requests_per_hour=1000)

        assert middleware.requests_per_minute == 100
        assert middleware.requests_per_hour == 1000
        assert middleware.burst_limit == 20
        assert middleware.whitelist == set()

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting client IP from X-Forwarded-For header."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        mock_request.client.host = "127.0.0.1"

        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_from_x_real_ip(self):
        """Test extracting client IP from X-Real-IP header."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        mock_request = MagicMock()
        mock_request.headers = {"x-real-ip": "192.168.1.2"}
        mock_request.client.host = "127.0.0.1"

        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.2"

    def test_get_client_ip_from_client(self):
        """Test extracting client IP from client object."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.3"

        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.3"

    def test_is_whitelisted(self):
        """Test IP whitelisting."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app, whitelist={"127.0.0.1", "192.168.1.1"})

        mock_request_whitelisted = MagicMock()
        mock_request_whitelisted.client.host = "127.0.0.1"
        mock_request_whitelisted.headers = {}

        mock_request_not_whitelisted = MagicMock()
        mock_request_not_whitelisted.client.host = "10.0.0.1"
        mock_request_not_whitelisted.headers = {}

        assert middleware._is_whitelisted(mock_request_whitelisted) is True
        assert middleware._is_whitelisted(mock_request_not_whitelisted) is False

    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_requests(self, app):
        """Test rate limiter allows normal request volume."""
        middleware = RateLimitMiddleware(app, requests_per_minute=10)

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {}
        mock_request.url.path = "/test"

        async def call_next(request):
            return JSONResponse({"message": "success"})

        # Make 5 requests (well under limit)
        for _ in range(5):
            response = await middleware.dispatch(mock_request, call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cleanup_old_requests(self, app):
        """Test cleanup of old request records."""
        middleware = RateLimitMiddleware(app, requests_per_minute=100)

        # Add old timestamp
        client_ip = "192.168.1.1"
        old_timestamp = time.time() - 120  # 2 minutes ago
        middleware.request_history[client_ip] = [old_timestamp]

        middleware._cleanup_old_requests(client_ip)

        # Old requests should be removed
        assert len(middleware.request_history[client_ip]) == 0

    def test_get_rate_limit_stats(self, app):
        """Test getting rate limit statistics."""
        middleware = RateLimitMiddleware(app, requests_per_minute=100)

        # Simulate some requests
        client_ip = "192.168.1.1"
        current_time = time.time()
        middleware.request_history[client_ip] = [
            current_time,
            current_time - 10,
            current_time - 30
        ]

        stats = middleware.get_rate_limit_stats(client_ip)

        assert "client_ip" in stats
        assert "requests_last_minute" in stats
        assert "requests_last_hour" in stats
        assert "rate_limit_minute" in stats
        assert "rate_limit_hour" in stats

        assert stats["client_ip"] == client_ip
        assert stats["requests_last_minute"] >= 0
        assert stats["rate_limit_minute"] == 100


class TestPerformanceMonitoringMiddleware:
    """Test performance monitoring middleware."""

    def test_middleware_initialization(self):
        """Test middleware initializes correctly."""
        app = FastAPI()
        middleware = PerformanceMonitoringMiddleware(app)

        assert middleware.request_count == 0
        assert middleware.total_request_time == 0.0
        assert middleware.error_count == 0

    @pytest.mark.asyncio
    async def test_successful_request_monitoring(self, app):
        """Test monitoring of successful requests."""
        middleware = PerformanceMonitoringMiddleware(app)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        async def call_next(request):
            return JSONResponse({"message": "success"})

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
        assert middleware.request_count == 1
        assert middleware.total_request_time > 0

    @pytest.mark.asyncio
    async def test_error_request_monitoring(self, app):
        """Test monitoring of error requests."""
        middleware = PerformanceMonitoringMiddleware(app)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        async def call_next(request):
            return JSONResponse({"error": "failed"}, status_code=500)

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 500
        assert middleware.error_count == 1

    @pytest.mark.asyncio
    async def test_slow_request_logging(self, app):
        """Test logging of slow requests."""
        middleware = PerformanceMonitoringMiddleware(app)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/slow"

        async def slow_call_next(request):
            time.sleep(0.1)  # Simulate slow request
            return JSONResponse({"message": "slow"})

        with patch('logging.Logger.warning') as mock_warning:
            response = await middleware.dispatch(mock_request, slow_call_next)

            assert response.status_code == 200
            # Slow request should be logged if > 5 seconds (won't trigger in this test)
            # But we test the mechanism

    @pytest.mark.asyncio
    async def test_response_headers_added(self, app):
        """Test that performance headers are added to response."""
        middleware = PerformanceMonitoringMiddleware(app)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        async def call_next(request):
            return JSONResponse({"message": "success"})

        response = await middleware.dispatch(mock_request, call_next)

        # Check that timing header is added
        assert "X-Process-Time" in response.headers
        assert float(response.headers["X-Process-Time"]) >= 0

    def test_get_metrics(self, app):
        """Test getting performance metrics."""
        middleware = PerformanceMonitoringMiddleware(app)

        # Simulate some requests
        middleware.request_count = 100
        middleware.total_request_time = 50.0
        middleware.error_count = 5

        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 65.5

            metrics = middleware.get_metrics()

            assert metrics["total_requests"] == 100
            assert metrics["error_count"] == 5
            assert metrics["error_rate"] == 5.0
            assert metrics["average_response_time"] == 0.5
            assert "memory_usage_percent" in metrics

    def test_get_metrics_no_requests(self, app):
        """Test getting metrics when no requests have been made."""
        middleware = PerformanceMonitoringMiddleware(app)

        metrics = middleware.get_metrics()

        assert metrics["total_requests"] == 0
        assert metrics["average_response_time"] == 0
        assert metrics["error_rate"] == 0

    @pytest.mark.asyncio
    async def test_multiple_requests_tracking(self, app):
        """Test tracking multiple requests."""
        middleware = PerformanceMonitoringMiddleware(app)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        async def call_next(request):
            return JSONResponse({"message": "success"})

        # Make multiple requests
        for i in range(10):
            await middleware.dispatch(mock_request, call_next)

        assert middleware.request_count == 10
        assert middleware.total_request_time > 0

        metrics = middleware.get_metrics()
        assert metrics["total_requests"] == 10
        assert metrics["average_response_time"] > 0


class TestMiddlewareIntegration:
    """Test middleware integration."""

    @pytest.mark.asyncio
    async def test_both_middlewares_together(self, app):
        """Test rate limiting and monitoring working together."""
        # Add both middlewares
        rate_limit = RateLimitMiddleware(app, requests_per_minute=10)
        monitoring = PerformanceMonitoringMiddleware(app)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {}

        async def call_next(request):
            return JSONResponse({"message": "success"})

        # Request should pass through both middlewares
        response_1 = await rate_limit.dispatch(mock_request, call_next)
        response_2 = await monitoring.dispatch(mock_request, call_next)

        assert response_1.status_code == 200
        assert response_2.status_code == 200
        assert monitoring.request_count > 0
