import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from app.services.entsoe_service import EntsoeService, entsoe_service
from app.models.energy import PriceData
from app.core.config import settings


@pytest.fixture
def entsoe_service_instance():
    """Create EntsoeService instance for testing."""
    return EntsoeService()


@pytest.fixture
def mock_price_xml():
    """Mock XML response from ENTSO-E API."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0">
    <TimeSeries>
        <Period>
            <timeInterval>
                <start>2025-05-26T00:00:00Z</start>
                <end>2025-05-27T00:00:00Z</end>
            </timeInterval>
            <resolution>PT60M</resolution>
            <Point>
                <position>1</position>
                <price.amount>45.50</price.amount>
            </Point>
            <Point>
                <position>2</position>
                <price.amount>42.30</price.amount>
            </Point>
            <Point>
                <position>3</position>
                <price.amount>38.90</price.amount>
            </Point>
        </Period>
    </TimeSeries>
</Publication_MarketDocument>'''


class TestEntsoeService:
    """Test EntsoeService functionality."""

    @pytest.mark.asyncio
    async def test_make_request_success(self, entsoe_service_instance, mock_price_xml):
        """Test successful API request."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_price_xml

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await entsoe_service_instance._make_request({"documentType": "A44"})

            assert result == mock_price_xml
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_authentication_error(self, entsoe_service_instance):
        """Test API request with authentication error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with pytest.raises(Exception, match="Invalid API key"):
                await entsoe_service_instance._make_request({"documentType": "A44"})

    @pytest.mark.asyncio
    async def test_make_request_rate_limit(self, entsoe_service_instance):
        """Test API request with rate limit error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Too many requests"

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with pytest.raises(Exception, match="Rate limit exceeded"):
                await entsoe_service_instance._make_request({"documentType": "A44"})

    def test_parse_price_xml_success(self, entsoe_service_instance, mock_price_xml):
        """Test successful XML parsing."""
        result = entsoe_service_instance._parse_price_xml(mock_price_xml)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(price, PriceData) for price in result)

        # Check first price point
        assert result[0].price == 45.50
        assert result[0].unit == "EUR/MWh"
        assert result[0].area == "FI"

        # Check prices are sorted by timestamp
        assert result[0].timestamp <= result[1].timestamp <= result[2].timestamp

    def test_parse_price_xml_invalid(self, entsoe_service_instance):
        """Test XML parsing with invalid XML."""
        invalid_xml = "This is not XML"

        with pytest.raises(Exception, match="Failed to parse XML response"):
            entsoe_service_instance._parse_price_xml(invalid_xml)

    @pytest.mark.asyncio
    async def test_get_day_ahead_prices_success(self, entsoe_service_instance, mock_price_xml):
        """Test getting day-ahead prices successfully."""
        test_date = datetime(2025, 5, 26)

        with patch.object(entsoe_service_instance, '_make_request', return_value=mock_price_xml):
            with patch('app.services.cache_service.cache_service.get', return_value=None):
                with patch('app.services.cache_service.cache_service.set', return_value=True):
                    result = await entsoe_service_instance.get_day_ahead_prices(test_date)

                    assert isinstance(result, list)
                    assert len(result) == 3
                    assert all(isinstance(price, PriceData) for price in result)

    @pytest.mark.asyncio
    async def test_get_day_ahead_prices_cached(self, entsoe_service_instance):
        """Test getting day-ahead prices from cache."""
        test_date = datetime(2025, 5, 26)
        cached_data = [
            {"timestamp": "2025-05-26T00:00:00+00:00", "price": 45.50, "unit": "EUR/MWh", "area": "FI"},
            {"timestamp": "2025-05-26T01:00:00+00:00", "price": 42.30, "unit": "EUR/MWh", "area": "FI"}
        ]

        with patch('app.services.cache_service.cache_service.get', return_value=cached_data):
            result = await entsoe_service_instance.get_day_ahead_prices(test_date)

            assert isinstance(result, list)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_tomorrow_prices(self, entsoe_service_instance, mock_price_xml):
        """Test getting tomorrow's prices."""
        with patch.object(entsoe_service_instance, 'get_day_ahead_prices', return_value=[]) as mock_get:
            await entsoe_service_instance.get_tomorrow_prices()

            mock_get.assert_called_once()
            call_args = mock_get.call_args[0][0]
            expected_date = datetime.utcnow() + timedelta(days=1)

            # Check date is tomorrow (allow 1 second tolerance)
            assert abs((call_args - expected_date).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_get_today_prices(self, entsoe_service_instance, mock_price_xml):
        """Test getting today's prices."""
        with patch.object(entsoe_service_instance, 'get_day_ahead_prices', return_value=[]) as mock_get:
            await entsoe_service_instance.get_today_prices()

            mock_get.assert_called_once()
            call_args = mock_get.call_args[0][0]
            expected_date = datetime.utcnow()

            # Check date is today (allow 1 second tolerance)
            assert abs((call_args - expected_date).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_get_price_statistics_success(self, entsoe_service_instance):
        """Test getting price statistics."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 28)

        mock_prices = [
            PriceData(timestamp=datetime(2025, 5, 26, i), price=40.0 + i, unit="EUR/MWh", area="FI")
            for i in range(24)
        ]

        with patch.object(entsoe_service_instance, 'get_day_ahead_prices', return_value=mock_prices):
            with patch('app.services.cache_service.cache_service.get', return_value=None):
                with patch('app.services.cache_service.cache_service.set', return_value=True):
                    result = await entsoe_service_instance.get_price_statistics(start_date, end_date)

                    assert "period" in result
                    assert "price_statistics" in result
                    assert "price_ranges" in result
                    assert "hourly_averages" in result

                    assert result["period"]["start"] == start_date.isoformat()
                    assert result["period"]["end"] == end_date.isoformat()

                    stats = result["price_statistics"]
                    assert "average" in stats
                    assert "median" in stats
                    assert "minimum" in stats
                    assert "maximum" in stats

    @pytest.mark.asyncio
    async def test_get_price_statistics_no_data(self, entsoe_service_instance):
        """Test getting price statistics with no data."""
        start_date = datetime(2025, 5, 26)
        end_date = datetime(2025, 5, 28)

        with patch.object(entsoe_service_instance, 'get_day_ahead_prices', return_value=[]):
            with patch('app.services.cache_service.cache_service.get', return_value=None):
                with pytest.raises(Exception, match="No price data available"):
                    await entsoe_service_instance.get_price_statistics(start_date, end_date)

    def test_service_initialization(self):
        """Test service is properly initialized."""
        assert entsoe_service is not None
        assert isinstance(entsoe_service, EntsoeService)
        assert entsoe_service.base_url == settings.ENTSOE_BASE_URL
        assert entsoe_service.api_key == settings.ENTSOE_API_KEY
        assert entsoe_service.finland_code == "10YFI-1--------U"

    @pytest.mark.asyncio
    async def test_request_adds_security_token(self, entsoe_service_instance):
        """Test that security token is added to request params."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<xml></xml>"

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            test_params = {"documentType": "A44"}
            await entsoe_service_instance._make_request(test_params)

            # Check that security token was added
            call_params = mock_get.call_args[1]["params"]
            assert "securityToken" in call_params
            assert call_params["securityToken"] == settings.ENTSOE_API_KEY
