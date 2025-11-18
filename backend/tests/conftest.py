import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Generator, Any

# Set test environment variables before importing app
os.environ["FINGRID_API_KEY"] = "test_fingrid_api_key_12345"
os.environ["ENTSOE_API_KEY"] = "test_entsoe_api_key_67890"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ENVIRONMENT"] = "testing"

from fastapi.testclient import TestClient
from app.main import app
from app.models.energy import (
    EnergyData, 
    EnergyDataPoint, 
    DatasetType, 
    PriceData,
    DifferentialPoint,
    DifferentialAnalysis
)
from app.services.cache_service import cache_service

# Configure pytest for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_cache_service():
    """Mock cache service for testing."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    return mock

@pytest.fixture
def sample_timestamps():
    """Generate sample timestamps for testing."""
    base_time = datetime.utcnow()
    return [base_time + timedelta(hours=i) for i in range(24)]

@pytest.fixture
def sample_consumption_data(sample_timestamps):
    """Create sample consumption data for testing."""
    data_points = [
        EnergyDataPoint(
            timestamp=ts,
            value=10000.0 + (i * 100),  # Varying consumption
            unit="MW"
        )
        for i, ts in enumerate(sample_timestamps)
    ]
    
    return EnergyData(
        dataset_id=124,
        name="Electricity consumption - real time data",
        dataset_type=DatasetType.CONSUMPTION_REALTIME,
        data=data_points,
        last_updated=datetime.utcnow(),
        metadata={
            "source": "Fingrid Open Data API",
            "total_points": len(data_points)
        }
    )

@pytest.fixture
def sample_production_data(sample_timestamps):
    """Create sample production data for testing."""
    data_points = [
        EnergyDataPoint(
            timestamp=ts,
            value=11000.0 + (i * 150),  # Varying production
            unit="MW"
        )
        for i, ts in enumerate(sample_timestamps)
    ]
    
    return EnergyData(
        dataset_id=192,
        name="Electricity production - real time data",
        dataset_type=DatasetType.PRODUCTION_REALTIME,
        data=data_points,
        last_updated=datetime.utcnow(),
        metadata={
            "source": "Fingrid Open Data API",
            "total_points": len(data_points)
        }
    )

@pytest.fixture
def sample_wind_data(sample_timestamps):
    """Create sample wind production data for testing."""
    data_points = [
        EnergyDataPoint(
            timestamp=ts,
            value=2000.0 + (i * 50),  # Varying wind production
            unit="MW"
        )
        for i, ts in enumerate(sample_timestamps)
    ]
    
    return EnergyData(
        dataset_id=181,
        name="Wind power production",
        dataset_type=DatasetType.WIND_PRODUCTION,
        data=data_points,
        last_updated=datetime.utcnow(),
        metadata={
            "source": "Fingrid Open Data API",
            "total_points": len(data_points)
        }
    )

@pytest.fixture
def sample_forecast_data(sample_timestamps):
    """Create sample forecast data for testing."""
    data_points = [
        EnergyDataPoint(
            timestamp=ts,
            value=10200.0 + (i * 80),  # Varying forecast
            unit="MW"
        )
        for i, ts in enumerate(sample_timestamps)
    ]
    
    return EnergyData(
        dataset_id=165,
        name="Electricity consumption forecast",
        dataset_type=DatasetType.CONSUMPTION_FORECAST,
        data=data_points,
        last_updated=datetime.utcnow(),
        metadata={
            "source": "Fingrid Open Data API",
            "total_points": len(data_points)
        }
    )

@pytest.fixture
def sample_price_data(sample_timestamps):
    """Create sample price data for testing."""
    return [
        PriceData(
            timestamp=ts,
            price=45.67 + (i * 2.5),  # Varying prices
            unit="EUR/MWh",
            area="FI"
        )
        for i, ts in enumerate(sample_timestamps)
    ]

@pytest.fixture
def sample_differential_analysis(sample_consumption_data, sample_production_data):
    """Create sample differential analysis for testing."""
    differential_points = []
    
    for i, (cons_point, prod_point) in enumerate(zip(
        sample_consumption_data.data, 
        sample_production_data.data
    )):
        differential = prod_point.value - cons_point.value
        percentage = (differential / cons_point.value) * 100
        
        status = "surplus" if differential > 0 else "deficit" if differential < 0 else "balanced"
        
        differential_points.append(DifferentialPoint(
            timestamp=cons_point.timestamp,
            production=prod_point.value,
            consumption=cons_point.value,
            differential=differential,
            status=status,
            percentage=percentage
        ))
    
    summary = {
        "average_differential_mw": 1000.0,
        "total_surplus_mwh": 15000.0,
        "total_deficit_mwh": 5000.0,
        "surplus_periods": 18,
        "deficit_periods": 6,
        "balanced_periods": 0
    }
    
    return DifferentialAnalysis(
        analysis_period="24 hours",
        data=differential_points,
        summary=summary,
        generated_at=datetime.utcnow()
    )

@pytest.fixture(autouse=True)
def mock_external_apis(monkeypatch):
    """Mock external API calls to avoid real HTTP requests during testing."""
    
    # Mock Fingrid API calls
    async def mock_fingrid_request(*args, **kwargs):
        return {"data": [{"start_time": datetime.utcnow().isoformat(), "value": 10000}]}
    
    # Mock ENTSO-E API calls
    async def mock_entsoe_request(*args, **kwargs):
        return '<xml>mock response</xml>'
    
    monkeypatch.setattr("app.services.fingrid_client.FingridClient._make_request", mock_fingrid_request)
    monkeypatch.setattr("app.services.entsoe_client.EntsoEClient._make_request", mock_entsoe_request)

@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = 0
    return mock

@pytest.fixture
def test_settings():
    """Test settings configuration."""
    return {
        "FINGRID_API_KEY": "test_fingrid_key",
        "ENTSOE_API_KEY": "test_entsoe_key",
        "REDIS_URL": "redis://localhost:6379",
        "CACHE_TTL": 300,
        "DEBUG": True,
        "LOG_LEVEL": "INFO"
    }

# Utility functions for tests
def create_mock_response(status_code: int = 200, json_data: Any = None):
    """Create a mock HTTP response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    mock_response.text = str(json_data) if json_data else ""
    return mock_response

def assert_energy_data_structure(data: dict):
    """Assert that data follows EnergyData structure."""
    required_fields = ["dataset_id", "name", "dataset_type", "data", "last_updated"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    assert isinstance(data["data"], list), "Data field should be a list"
    if data["data"]:
        data_point = data["data"][0]
        point_fields = ["timestamp", "value", "unit"]
        for field in point_fields:
            assert field in data_point, f"Missing data point field: {field}"

def assert_price_data_structure(data: list):
    """Assert that data follows PriceData structure."""
    assert isinstance(data, list), "Price data should be a list"
    if data:
        price_point = data[0]
        required_fields = ["timestamp", "price", "unit", "area"]
        for field in required_fields:
            assert field in price_point, f"Missing price point field: {field}"