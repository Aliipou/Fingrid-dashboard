import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import httpx

from app.services.fingrid_client import FingridService
from app.models.energy import DatasetType, EnergyData
from app.core.config import settings

@pytest.fixture
def fingrid_service():
    """Create FingridService instance for testing."""
    return FingridService()

@pytest.fixture
def mock_api_response():
    """Mock API response data."""
    return {
        "data": [
            {
                "start_time": "2025-05-26T10:00:00Z",
                "value": 10000.0
            },
            {
                "start_time": "2025-05-26T11:00:00Z", 
                "value": 10500.0
            }
        ],
        "variable": {
            "name": "Test Dataset",
            "id": 124
        }
    }

class TestFingridService:
    """Test FingridService functionality."""
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, fingrid_service, mock_api_response):
        """Test successful API request."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_response
            mock_get.return_value = mock_response
            
            result = await fingrid_service._make_request("/test/endpoint")
            
            assert result == mock_api_response
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_auth_error(self, fingrid_service):
        """Test API request with authentication error."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception, match="Invalid API key"):
                await fingrid_service._make_request("/test/endpoint")

    @pytest.mark.asyncio
    async def test_make_request_rate_limit(self, fingrid_service):
        """Test API request with rate limit error."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception, match="Rate limit exceeded"):
                await fingrid_service._make_request("/test/endpoint")

    @pytest.mark.asyncio
    async def test_make_request_timeout(self, fingrid_service):
        """Test API request timeout."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(Exception, match="Request timeout"):
                await fingrid_service._make_request("/test/endpoint")

    @pytest.mark.asyncio
    async def test_fetch_dataset_success(self, fingrid_service, mock_api_response):
        """Test successful dataset fetch."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        with patch.object(fingrid_service, '_make_request') as mock_request:
            with patch('app.services.cache_service.cache_service.get') as mock_cache_get:
                with patch('app.services.cache_service.cache_service.set') as mock_cache_set:
                    mock_cache_get.return_value = None
                    mock_request.return_value = mock_api_response
                    mock_cache_set.return_value = True
                    
                    result = await fingrid_service._fetch_dataset(
                        124, 
                        DatasetType.CONSUMPTION_REALTIME,
                        start_date,
                        end_date
                    )
                    
                    assert isinstance(result, EnergyData)
                    assert result.dataset_id == 124
                    assert result.dataset_type == DatasetType.CONSUMPTION_REALTIME
                    assert len(result.data) == 2
                    assert result.data[0].value == 10000.0
                    assert result.data[1].value == 10500.0

    @pytest.mark.asyncio 
    async def test_fetch_dataset_cached(self, fingrid_service):
        """Test dataset fetch from cache."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        cached_data = {
            "dataset_id": 124,
            "name": "Cached Dataset",
            "dataset_type": "consumption_realtime",
            "data": [
                {
                    "timestamp": start_date.isoformat(),
                    "value": 9500.0,
                    "unit": "MW"
                }
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        with patch('app.services.cache_service.cache_service.get') as mock_cache_get:
            mock_cache_get.return_value = cached_data
            
            result = await fingrid_service._fetch_dataset(
                124,
                DatasetType.CONSUMPTION_REALTIME, 
                start_date,
                end_date
            )
            
            assert isinstance(result, EnergyData)
            assert result.dataset_id == 124
            assert result.name == "Cached Dataset"

    @pytest.mark.asyncio
    async def test_get_consumption_realtime(self, fingrid_service, mock_api_response):
        """Test get consumption realtime data."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        with patch.object(fingrid_service, '_fetch_dataset') as mock_fetch:
            mock_energy_data = MagicMock()
            mock_energy_data.dataset_type = DatasetType.CONSUMPTION_REALTIME
            mock_fetch.return_value = mock_energy_data
            
            result = await fingrid_service.get_consumption_realtime(start_date, end_date)
            
            mock_fetch.assert_called_once_with(
                124,  # consumption dataset ID
                DatasetType.CONSUMPTION_REALTIME,
                start_date,
                end_date
            )
            assert result == mock_energy_data

    @pytest.mark.asyncio
    async def test_get_production_realtime(self, fingrid_service):
        """Test get production realtime data."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        with patch.object(fingrid_service, '_fetch_dataset') as mock_fetch:
            mock_energy_data = MagicMock()
            mock_energy_data.dataset_type = DatasetType.PRODUCTION_REALTIME
            mock_fetch.return_value = mock_energy_data
            
            result = await fingrid_service.get_production_realtime(start_date, end_date)
            
            mock_fetch.assert_called_once_with(
                192,  # production dataset ID
                DatasetType.PRODUCTION_REALTIME,
                start_date,
                end_date
            )
            assert result == mock_energy_data

    @pytest.mark.asyncio
    async def test_get_wind_production(self, fingrid_service):
        """Test get wind production data."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        with patch.object(fingrid_service, '_fetch_dataset') as mock_fetch:
            mock_energy_data = MagicMock()
            mock_energy_data.dataset_type = DatasetType.WIND_PRODUCTION
            mock_fetch.return_value = mock_energy_data
            
            result = await fingrid_service.get_wind_production(start_date, end_date)
            
            mock_fetch.assert_called_once_with(
                181,  # wind dataset ID
                DatasetType.WIND_PRODUCTION,
                start_date,
                end_date
            )
            assert result == mock_energy_data

    @pytest.mark.asyncio
    async def test_get_consumption_forecast(self, fingrid_service):
        """Test get consumption forecast data."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow() + timedelta(hours=23)
        
        with patch.object(fingrid_service, '_fetch_dataset') as mock_fetch:
            mock_energy_data = MagicMock()
            mock_energy_data.dataset_type = DatasetType.CONSUMPTION_FORECAST
            mock_fetch.return_value = mock_energy_data
            
            result = await fingrid_service.get_consumption_forecast(start_date, end_date)
            
            mock_fetch.assert_called_once_with(
                165,  # forecast dataset ID
                DatasetType.CONSUMPTION_FORECAST,
                start_date,
                end_date
            )
            assert result == mock_energy_data

    @pytest.mark.asyncio
    async def test_get_latest_data(self, fingrid_service):
        """Test get latest data functionality."""
        with patch.object(fingrid_service, 'get_consumption_realtime') as mock_consumption:
            with patch.object(fingrid_service, 'get_production_realtime') as mock_production:
                with patch.object(fingrid_service, 'get_wind_production') as mock_wind:
                    with patch('app.services.cache_service.cache_service.get') as mock_cache_get:
                        with patch('app.services.cache_service.cache_service.set') as mock_cache_set:
                            
                            # Setup mock data
                            mock_cache_get.return_value = None
                            mock_cache_set.return_value = True
                            
                            mock_consumption_data = MagicMock()
                            mock_consumption_data.data = [MagicMock(value=10000.0, timestamp=datetime.utcnow())]
                            mock_consumption.return_value = mock_consumption_data
                            
                            mock_production_data = MagicMock()
                            mock_production_data.data = [MagicMock(value=11000.0, timestamp=datetime.utcnow())]
                            mock_production.return_value = mock_production_data
                            
                            mock_wind_data = MagicMock()
                            mock_wind_data.data = [MagicMock(value=2000.0, timestamp=datetime.utcnow())]
                            mock_wind.return_value = mock_wind_data
                            
                            result = await fingrid_service.get_latest_data()
                            
                            assert "consumption" in result
                            assert "production" in result
                            assert "wind_production" in result
                            assert "metrics" in result
                            assert result["consumption"]["value"] == 10000.0
                            assert result["production"]["value"] == 11000.0
                            assert result["wind_production"]["value"] == 2000.0

class TestErrorHandling:
    """Test error handling in FingridService."""
    
    @pytest.mark.asyncio
    async def test_invalid_data_point_handling(self, fingrid_service):
        """Test handling of invalid data points."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        # Mock API response with invalid data
        invalid_response = {
            "data": [
                {"start_time": "invalid_timestamp", "value": "invalid_value"},
                {"start_time": "2025-05-26T10:00:00Z", "value": 10000.0},
                {"missing_fields": True}
            ],
            "variable": {"name": "Test Dataset", "id": 124}
        }
        
        with patch.object(fingrid_service, '_make_request') as mock_request:
            with patch('app.services.cache_service.cache_service.get') as mock_cache_get:
                with patch('app.services.cache_service.cache_service.set') as mock_cache_set:
                    mock_cache_get.return_value = None
                    mock_request.return_value = invalid_response
                    mock_cache_set.return_value = True
                    
                    result = await fingrid_service._fetch_dataset(
                        124,
                        DatasetType.CONSUMPTION_REALTIME,
                        start_date,
                        end_date
                    )
                    
                    # Should only have 1 valid data point
                    assert len(result.data) == 1
                    assert result.data[0].value == 10000.0

    @pytest.mark.asyncio
    async def test_network_error_handling(self, fingrid_service):
        """Test network error handling."""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Network error")
            
            with pytest.raises(Exception, match="Request failed"):
                await fingrid_service._make_request("/test/endpoint")

class TestConfigAndSetup:
    """Test service configuration and setup."""
    
    def test_dataset_configuration(self, fingrid_service):
        """Test that datasets are properly configured."""
        assert DatasetType.CONSUMPTION_REALTIME in fingrid_service.datasets
        assert DatasetType.PRODUCTION_REALTIME in fingrid_service.datasets
        assert DatasetType.WIND_PRODUCTION in fingrid_service.datasets
        assert DatasetType.CONSUMPTION_FORECAST in fingrid_service.datasets
        
        # Check dataset IDs are correct
        assert fingrid_service.datasets[DatasetType.CONSUMPTION_REALTIME] == 124
        assert fingrid_service.datasets[DatasetType.PRODUCTION_REALTIME] == 192
        assert fingrid_service.datasets[DatasetType.WIND_PRODUCTION] == 181
        assert fingrid_service.datasets[DatasetType.CONSUMPTION_FORECAST] == 165

    def test_cache_ttl_configuration(self, fingrid_service):
        """Test cache TTL configuration."""
        assert DatasetType.CONSUMPTION_REALTIME in fingrid_service.cache_ttl
        assert DatasetType.PRODUCTION_REALTIME in fingrid_service.cache_ttl
        assert DatasetType.WIND_PRODUCTION in fingrid_service.cache_ttl
        assert DatasetType.CONSUMPTION_FORECAST in fingrid_service.cache_ttl
        
        # Forecast should have longer cache time
        assert (fingrid_service.cache_ttl[DatasetType.CONSUMPTION_FORECAST] > 
                fingrid_service.cache_ttl[DatasetType.CONSUMPTION_REALTIME])

    def test_service_initialization(self, fingrid_service):
        """Test service initialization."""
        assert fingrid_service.base_url == settings.FINGRID_BASE_URL
        assert fingrid_service.api_key == settings.FINGRID_API_KEY
        assert fingrid_service.timeout == 30.0