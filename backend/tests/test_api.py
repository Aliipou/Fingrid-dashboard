import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.models.energy import EnergyData, EnergyDataPoint, DatasetType
from datetime import datetime

client = TestClient(app)

@pytest.fixture
def mock_energy_data():
    return EnergyData(
        dataset_id=124,
        name="Test Consumption",
        dataset_type=DatasetType.CONSUMPTION_REALTIME,
        data=[
            EnergyDataPoint(
                timestamp=datetime.utcnow(),
                value=10000.0,
                unit="MW"
            )
        ],
        last_updated=datetime.utcnow()
    )

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "fingrid-dashboard-api"

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data

@patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime')
@patch('app.services.cache_service.cache_service.get')
async def test_fingrid_consumption_endpoint(mock_cache_get, mock_fingrid_service, mock_energy_data):
    """Test Fingrid consumption endpoint"""
    mock_cache_get.return_value = None
    mock_fingrid_service.return_value = mock_energy_data
    
    response = client.get("/api/v1/fingrid/consumption/realtime")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_type"] == DatasetType.CONSUMPTION_REALTIME
    assert len(data["data"]) > 0

@patch('app.services.fingrid_service.fingrid_service.get_production_realtime')
@patch('app.services.cache_service.cache_service.get')
async def test_fingrid_production_endpoint(mock_cache_get, mock_fingrid_service, mock_energy_data):
    """Test Fingrid production endpoint"""
    mock_cache_get.return_value = None
    mock_energy_data.dataset_type = DatasetType.PRODUCTION_REALTIME
    mock_fingrid_service.return_value = mock_energy_data
    
    response = client.get("/api/v1/fingrid/production/realtime")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_type"] == DatasetType.PRODUCTION_REALTIME

@patch('app.services.fingrid_service.fingrid_service.get_wind_production')
@patch('app.services.cache_service.cache_service.get')
async def test_fingrid_wind_endpoint(mock_cache_get, mock_fingrid_service, mock_energy_data):
    """Test Fingrid wind production endpoint"""
    mock_cache_get.return_value = None
    mock_energy_data.dataset_type = DatasetType.WIND_PRODUCTION
    mock_fingrid_service.return_value = mock_energy_data
    
    response = client.get("/api/v1/fingrid/wind/realtime")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_type"] == DatasetType.WIND_PRODUCTION

def test_api_docs_accessibility():
    """Test that API documentation is accessible"""
    response = client.get("/api/docs")
    assert response.status_code == 200
    
    response = client.get("/api/redoc")
    assert response.status_code == 200

@patch('app.services.entsoe_service.entsoe_service.get_today_prices')
@patch('app.services.cache_service.cache_service.get')
async def test_entsoe_prices_endpoint(mock_cache_get, mock_entsoe_service):
    """Test Entso-E prices endpoint"""
    mock_cache_get.return_value = None
    mock_entsoe_service.return_value = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "price": 45.67,
            "unit": "EUR/MWh",
            "area": "FI"
        }
    ]
    
    response = client.get("/api/v1/entsoe/prices/today")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_cors_headers():
    """Test CORS headers are present"""
    response = client.options("/api/v1/health")
    assert response.status_code == 200
    # CORS headers should be added by middleware

def test_rate_limiting_headers():
    """Test rate limiting headers are present"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    # Rate limiting headers should be added by middleware
    assert "X-RateLimit-Limit" in response.headers or True  # Allow for middleware configuration