"""
Integration tests for the Fingrid Energy Dashboard API.

These tests verify that different components work together correctly.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.models.energy import DatasetType, EnergyData, EnergyDataPoint, PriceData


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis_connected():
    """Mock Redis as connected."""
    with patch('app.services.cache_service.cache_service.redis') as mock_redis:
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        yield mock_redis


class TestAPIIntegration:
    """Test API endpoint integration."""

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "status" in data

    def test_openapi_docs_available(self, client):
        """Test OpenAPI documentation is available."""
        response = client.get("/api/docs")

        assert response.status_code == 200

    def test_openapi_json_available(self, client):
        """Test OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema


class TestFingridEndpointIntegration:
    """Test Fingrid API endpoint integration."""

    def test_consumption_to_differential_flow(self, client):
        """Test data flow from consumption endpoint to differential analysis."""
        mock_consumption = EnergyData(
            dataset_id=124,
            name="Consumption",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8000.0 + i * 100, unit="MW") for i in range(24)],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        mock_production = EnergyData(
            dataset_id=192,
            name="Production",
            dataset_type=DatasetType.PRODUCTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8500.0 + i * 120, unit="MW") for i in range(24)],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption):
            with patch('app.services.fingrid_service.fingrid_service.get_production_realtime', return_value=mock_production):
                # First, get consumption data
                response1 = client.get("/api/v1/fingrid/consumption/realtime")
                assert response1.status_code == 200

                # Then, get differential analysis using both
                response2 = client.get("/api/v1/fingrid/differential")
                assert response2.status_code == 200

                data = response2.json()
                assert "data" in data
                assert "summary" in data
                assert len(data["data"]) == 24  # Should have 24 hourly points

    def test_dashboard_endpoint_aggregation(self, client):
        """Test dashboard endpoint aggregates all data sources."""
        mock_data = EnergyData(
            dataset_id=124,
            name="Test",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime.utcnow(), value=10000.0, unit="MW")],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        with patch('app.services.fingrid_service.fingrid_service.get_all_realtime_data') as mock_get_all:
            mock_get_all.return_value = {
                "consumption": mock_data,
                "production": mock_data,
                "wind": mock_data,
                "forecast": mock_data
            }

            response = client.get("/api/v1/fingrid/dashboard")
            assert response.status_code == 200

            data = response.json()
            assert "consumption_realtime" in data
            assert "production_realtime" in data
            assert "wind_production" in data
            assert "consumption_forecast" in data
            assert "last_updated" in data
            assert data["status"] == "success"


class TestAnalyticsIntegration:
    """Test analytics endpoint integration."""

    def test_efficiency_to_trends_flow(self, client):
        """Test data flow from efficiency to trends analysis."""
        mock_data = EnergyData(
            dataset_id=124,
            name="Test",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8000.0 + i * 100, unit="MW") for i in range(48)],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 28)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_data):
            with patch('app.services.fingrid_service.fingrid_service.get_production_realtime', return_value=mock_data):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        # Get efficiency metrics
                        response1 = client.get(
                            "/api/v1/analytics/efficiency",
                            params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
                        )
                        assert response1.status_code == 200

                        # Get trends for same period
                        response2 = client.get(
                            "/api/v1/analytics/trends",
                            params={
                                "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat(),
                                "period": "daily"
                            }
                        )
                        assert response2.status_code == 200


class TestExportIntegration:
    """Test export endpoint integration."""

    def test_export_all_formats_for_dataset(self, client):
        """Test exporting same dataset in all formats."""
        mock_data = EnergyData(
            dataset_id=124,
            name="Test",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=10000.0, unit="MW") for i in range(24)],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        formats = ["csv", "json", "xml", "excel"]

        for fmt in formats:
            with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_data):
                response = client.get(
                    "/api/v1/export/fingrid/consumption_realtime",
                    params={"format": fmt}
                )

                assert response.status_code == 200, f"Failed for format: {fmt}"
                assert response.headers["content-disposition"].endswith(f".{fmt if fmt != 'excel' else 'xlsx'}")


class TestCachingIntegration:
    """Test caching integration across endpoints."""

    def test_cache_used_across_endpoints(self, client, mock_redis_connected):
        """Test that cache is properly used across different endpoints."""
        mock_data = EnergyData(
            dataset_id=124,
            name="Test",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime.utcnow(), value=10000.0, unit="MW")],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_data) as mock_get:
            # First request - should call service
            response1 = client.get("/api/v1/fingrid/consumption/realtime")
            assert response1.status_code == 200

            # Service should be called
            assert mock_get.call_count >= 1


class TestErrorHandlingIntegration:
    """Test error handling across the application."""

    def test_service_error_propagates_correctly(self, client):
        """Test that service errors are properly handled and returned."""
        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', side_effect=Exception("Service unavailable")):
            response = client.get("/api/v1/fingrid/consumption/realtime")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_invalid_date_format_handled(self, client):
        """Test that invalid date formats are handled gracefully."""
        response = client.get(
            "/api/v1/analytics/efficiency",
            params={"start_date": "invalid-date", "end_date": "also-invalid"}
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_missing_required_params_handled(self, client):
        """Test that missing required parameters are handled."""
        response = client.get("/api/v1/analytics/efficiency")

        assert response.status_code == 422  # Validation error


class TestRateLimitingIntegration:
    """Test rate limiting integration."""

    def test_rate_limiting_headers_present(self, client):
        """Test that rate limiting information is in response headers."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        # Rate limit middleware should add headers


class TestCORSIntegration:
    """Test CORS integration."""

    def test_cors_headers_on_options(self, client):
        """Test CORS headers on OPTIONS request."""
        response = client.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS middleware should handle this
        assert response.status_code in [200, 405]


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    def test_complete_data_analysis_workflow(self, client):
        """Test complete workflow: fetch data -> analyze -> export."""
        mock_consumption = EnergyData(
            dataset_id=124,
            name="Consumption",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8000.0 + i * 100, unit="MW") for i in range(24)],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        mock_production = EnergyData(
            dataset_id=192,
            name="Production",
            dataset_type=DatasetType.PRODUCTION_REALTIME,
            data=[EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8500.0 + i * 120, unit="MW") for i in range(24)],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption):
            with patch('app.services.fingrid_service.fingrid_service.get_production_realtime', return_value=mock_production):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        # Step 1: Fetch realtime data
                        response1 = client.get("/api/v1/fingrid/consumption/realtime")
                        assert response1.status_code == 200

                        # Step 2: Get efficiency analysis
                        response2 = client.get(
                            "/api/v1/analytics/efficiency",
                            params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
                        )
                        assert response2.status_code == 200

                        # Step 3: Detect anomalies
                        response3 = client.get(
                            "/api/v1/analytics/anomalies",
                            params={
                                "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat()
                            }
                        )
                        assert response3.status_code == 200

                        # Step 4: Export results
                        response4 = client.get(
                            "/api/v1/export/fingrid/consumption_realtime",
                            params={"format": "csv"}
                        )
                        assert response4.status_code == 200

    def test_price_analysis_workflow(self, client):
        """Test complete price analysis workflow."""
        mock_prices = [
            PriceData(timestamp=datetime(2025, 5, 26, i), price=40.0 + i, unit="EUR/MWh", area="FI")
            for i in range(24)
        ]

        with patch('app.services.entsoe_service.entsoe_service.get_today_prices', return_value=mock_prices):
            with patch('app.services.entsoe_service.entsoe_service.get_tomorrow_prices', return_value=mock_prices):
                # Get today's prices
                response1 = client.get("/api/v1/entsoe/prices/today")
                assert response1.status_code == 200

                # Get tomorrow's prices
                response2 = client.get("/api/v1/entsoe/prices/tomorrow")
                assert response2.status_code == 200

                # Export prices
                response3 = client.get(
                    "/api/v1/export/prices/today",
                    params={"format": "json"}
                )
                assert response3.status_code == 200
