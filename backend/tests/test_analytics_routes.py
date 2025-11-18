import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.models.energy import DatasetType, EnergyData, EnergyDataPoint


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_consumption_data():
    """Mock consumption data."""
    return EnergyData(
        dataset_id=124,
        name="Consumption",
        dataset_type=DatasetType.CONSUMPTION_REALTIME,
        data=[
            EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8000.0 + i * 100, unit="MW")
            for i in range(24)
        ],
        last_updated=datetime.utcnow(),
        metadata={}
    )


@pytest.fixture
def mock_production_data():
    """Mock production data."""
    return EnergyData(
        dataset_id=192,
        name="Production",
        dataset_type=DatasetType.PRODUCTION_REALTIME,
        data=[
            EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8500.0 + i * 120, unit="MW")
            for i in range(24)
        ],
        last_updated=datetime.utcnow(),
        metadata={}
    )


@pytest.fixture
def mock_forecast_data():
    """Mock forecast data."""
    return EnergyData(
        dataset_id=165,
        name="Forecast",
        dataset_type=DatasetType.CONSUMPTION_FORECAST,
        data=[
            EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=8100.0 + i * 95, unit="MW")
            for i in range(24)
        ],
        last_updated=datetime.utcnow(),
        metadata={}
    )


class TestAnalyticsRoutes:
    """Test analytics API routes."""

    def test_get_efficiency_metrics_success(self, client, mock_consumption_data, mock_production_data):
        """Test getting efficiency metrics successfully."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption_data):
            with patch('app.services.fingrid_service.fingrid_service.get_production_realtime', return_value=mock_production_data):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        response = client.get(
                            "/api/v1/analytics/efficiency",
                            params={
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat()
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()

                        assert "period" in data
                        assert "totals" in data
                        assert "efficiency" in data
                        assert "peaks" in data
                        assert "variability" in data

                        # Check period info
                        assert data["period"]["start"] == start_date.isoformat()
                        assert data["period"]["end"] == end_date.isoformat()

                        # Check totals
                        assert "consumption_mwh" in data["totals"]
                        assert "production_mwh" in data["totals"]
                        assert "net_balance_mwh" in data["totals"]

                        # Check efficiency metrics
                        assert "production_consumption_ratio" in data["efficiency"]
                        assert "surplus_hours" in data["efficiency"]
                        assert "deficit_hours" in data["efficiency"]

    def test_get_efficiency_metrics_cached(self, client):
        """Test getting efficiency metrics from cache."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        cached_result = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "totals": {"consumption_mwh": 200000, "production_mwh": 210000},
            "efficiency": {"production_consumption_ratio": 105}
        }

        with patch('app.services.cache_service.cache_service.get', return_value=cached_result):
            response = client.get(
                "/api/v1/analytics/efficiency",
                params={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data == cached_result

    def test_detect_anomalies_success(self, client, mock_consumption_data):
        """Test anomaly detection successfully."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption_data):
            with patch('app.services.cache_service.cache_service.get', return_value=None):
                with patch('app.services.cache_service.cache_service.set', return_value=True):
                    response = client.get(
                        "/api/v1/analytics/anomalies",
                        params={
                            "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "threshold": 2.0
                        }
                    )

                    assert response.status_code == 200
                    data = response.json()

                    assert "dataset_type" in data
                    assert "analysis_period" in data
                    assert "parameters" in data
                    assert "anomalies" in data
                    assert "summary" in data

                    # Check parameters
                    assert data["parameters"]["threshold_standard_deviations"] == 2.0
                    assert "mean_value" in data["parameters"]
                    assert "standard_deviation" in data["parameters"]

                    # Check summary
                    assert "total_data_points" in data["summary"]
                    assert "anomalies_detected" in data["summary"]
                    assert "anomaly_percentage" in data["summary"]

    def test_detect_anomalies_custom_threshold(self, client, mock_consumption_data):
        """Test anomaly detection with custom threshold."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption_data):
            with patch('app.services.cache_service.cache_service.get', return_value=None):
                with patch('app.services.cache_service.cache_service.set', return_value=True):
                    response = client.get(
                        "/api/v1/analytics/anomalies",
                        params={
                            "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "threshold": 3.0
                        }
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["parameters"]["threshold_standard_deviations"] == 3.0

    def test_forecast_accuracy_analysis_success(self, client, mock_forecast_data, mock_consumption_data):
        """Test forecast accuracy analysis successfully."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_forecast', return_value=mock_forecast_data):
            with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption_data):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        response = client.get(
                            "/api/v1/analytics/forecast-accuracy",
                            params={
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat()
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()

                        assert "analysis_period" in data
                        assert "accuracy_metrics" in data
                        assert "time_analysis" in data
                        assert "distribution" in data

                        # Check accuracy metrics
                        metrics = data["accuracy_metrics"]
                        assert "mean_absolute_error_mw" in metrics
                        assert "mean_absolute_percentage_error" in metrics
                        assert "root_mean_square_error_mw" in metrics
                        assert "forecast_bias_mw" in metrics
                        assert "bias_direction" in metrics

                        # Check time analysis
                        assert "best_forecast_hour" in data["time_analysis"]
                        assert "worst_forecast_hour" in data["time_analysis"]

    def test_analyze_trends_success(self, client, mock_consumption_data):
        """Test trend analysis successfully."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption_data):
            response = client.get(
                "/api/v1/analytics/trends",
                params={
                    "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period": "hourly"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert "dataset_type" in data
            assert "period" in data
            assert "analysis_period" in data
            assert "trend_analysis" in data
            assert "summary_statistics" in data
            assert "moving_averages" in data

            # Check trend analysis
            trend = data["trend_analysis"]
            assert "slope_per_period" in trend
            assert "trend_direction" in trend
            assert "correlation_coefficient" in trend
            assert "trend_strength" in trend

            # Check summary statistics
            stats = data["summary_statistics"]
            assert "mean" in stats
            assert "median" in stats
            assert "std_deviation" in stats
            assert "min_value" in stats
            assert "max_value" in stats

    def test_analyze_trends_different_periods(self, client, mock_consumption_data):
        """Test trend analysis with different aggregation periods."""
        start_date = datetime(2025, 5, 1)
        end_date = datetime(2025, 5, 31)

        periods = ["hourly", "daily", "weekly"]

        for period in periods:
            with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption_data):
                response = client.get(
                    "/api/v1/analytics/trends",
                    params={
                        "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "period": period
                    }
                )

                assert response.status_code == 200, f"Failed for period: {period}"
                data = response.json()
                assert data["period"] == period

    def test_analyze_trends_invalid_period(self, client, mock_consumption_data):
        """Test trend analysis with invalid period."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_consumption_data):
            response = client.get(
                "/api/v1/analytics/trends",
                params={
                    "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period": "invalid"
                }
            )

            assert response.status_code == 400

    def test_analytics_no_data(self, client):
        """Test analytics endpoints with no data."""
        empty_data = EnergyData(
            dataset_id=124,
            name="Empty",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=empty_data):
            # Test anomaly detection
            response = client.get(
                "/api/v1/analytics/anomalies",
                params={
                    "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )
            assert response.status_code == 404

            # Test trends
            response = client.get(
                "/api/v1/analytics/trends",
                params={
                    "dataset_type": DatasetType.CONSUMPTION_REALTIME.value,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period": "daily"
                }
            )
            assert response.status_code == 404

    def test_efficiency_metrics_insufficient_data(self, client):
        """Test efficiency metrics with insufficient data."""
        empty_data = EnergyData(
            dataset_id=124,
            name="Empty",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 27)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=empty_data):
            with patch('app.services.fingrid_service.fingrid_service.get_production_realtime', return_value=empty_data):
                response = client.get(
                    "/api/v1/analytics/efficiency",
                    params={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    }
                )

                assert response.status_code == 404
