import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import json

from app.main import app
from app.models.energy import DatasetType, EnergyData, EnergyDataPoint, PriceData


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_energy_data():
    """Mock energy data."""
    return EnergyData(
        dataset_id=124,
        name="Test Consumption",
        dataset_type=DatasetType.CONSUMPTION_REALTIME,
        data=[
            EnergyDataPoint(timestamp=datetime(2025, 5, 26, i), value=10000.0 + i * 100, unit="MW")
            for i in range(24)
        ],
        last_updated=datetime.utcnow(),
        metadata={"source": "Fingrid Open Data API"}
    )


@pytest.fixture
def mock_price_data():
    """Mock price data."""
    return [
        PriceData(timestamp=datetime(2025, 5, 26, i), price=40.0 + i, unit="EUR/MWh", area="FI")
        for i in range(24)
    ]


class TestExportRoutes:
    """Test export API routes."""

    def test_export_fingrid_csv_success(self, client, mock_energy_data):
        """Test exporting Fingrid data as CSV."""
        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_energy_data):
            response = client.get(
                "/api/v1/export/fingrid/consumption_realtime",
                params={"format": "csv"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            assert "attachment" in response.headers["content-disposition"]
            assert ".csv" in response.headers["content-disposition"]

            # Check CSV content
            content = response.text
            assert "timestamp,value,unit" in content
            assert "MW" in content

    def test_export_fingrid_json_success(self, client, mock_energy_data):
        """Test exporting Fingrid data as JSON."""
        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_energy_data):
            response = client.get(
                "/api/v1/export/fingrid/consumption_realtime",
                params={"format": "json"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            assert "attachment" in response.headers["content-disposition"]
            assert ".json" in response.headers["content-disposition"]

            # Check JSON structure
            data = response.json()
            assert "metadata" in data
            assert "data" in data
            assert len(data["data"]) == 24

    def test_export_fingrid_xml_success(self, client, mock_energy_data):
        """Test exporting Fingrid data as XML."""
        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_energy_data):
            response = client.get(
                "/api/v1/export/fingrid/consumption_realtime",
                params={"format": "xml"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/xml"
            assert "attachment" in response.headers["content-disposition"]
            assert ".xml" in response.headers["content-disposition"]

            # Check XML content
            content = response.text
            assert '<?xml version="1.0" encoding="UTF-8"?>' in content
            assert "<energy_data>" in content
            assert "<metadata>" in content
            assert "<data_points>" in content
            assert "</energy_data>" in content

    def test_export_fingrid_excel_success(self, client, mock_energy_data):
        """Test exporting Fingrid data as Excel."""
        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_energy_data):
            response = client.get(
                "/api/v1/export/fingrid/consumption_realtime",
                params={"format": "excel"}
            )

            assert response.status_code == 200
            assert "spreadsheet" in response.headers["content-type"]
            assert "attachment" in response.headers["content-disposition"]
            assert ".xlsx" in response.headers["content-disposition"]

    def test_export_fingrid_with_date_range(self, client, mock_energy_data):
        """Test exporting Fingrid data with custom date range."""
        start_date = datetime(2025, 5, 26, 0, 0, 0)
        end_date = datetime(2025, 5, 27, 0, 0, 0)

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=mock_energy_data) as mock_get:
            response = client.get(
                "/api/v1/export/fingrid/consumption_realtime",
                params={
                    "format": "csv",
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )

            assert response.status_code == 200
            mock_get.assert_called_once()

    def test_export_fingrid_invalid_format(self, client):
        """Test exporting with invalid format."""
        response = client.get(
            "/api/v1/export/fingrid/consumption_realtime",
            params={"format": "pdf"}
        )

        assert response.status_code == 500  # Export service will raise error

    def test_export_fingrid_no_data(self, client):
        """Test exporting when no data is available."""
        empty_data = EnergyData(
            dataset_id=124,
            name="Test",
            dataset_type=DatasetType.CONSUMPTION_REALTIME,
            data=[],
            last_updated=datetime.utcnow(),
            metadata={}
        )

        with patch('app.services.fingrid_service.fingrid_service.get_consumption_realtime', return_value=empty_data):
            response = client.get(
                "/api/v1/export/fingrid/consumption_realtime",
                params={"format": "csv"}
            )

            assert response.status_code == 404

    def test_export_prices_today_csv(self, client, mock_price_data):
        """Test exporting today's prices as CSV."""
        with patch('app.services.entsoe_service.entsoe_service.get_today_prices', return_value=mock_price_data):
            response = client.get(
                "/api/v1/export/prices/today",
                params={"format": "csv"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"

            # Check CSV content
            content = response.text
            assert "timestamp,price,unit,area" in content
            assert "EUR/MWh" in content
            assert "FI" in content

    def test_export_prices_tomorrow_json(self, client, mock_price_data):
        """Test exporting tomorrow's prices as JSON."""
        with patch('app.services.entsoe_service.entsoe_service.get_tomorrow_prices', return_value=mock_price_data):
            response = client.get(
                "/api/v1/export/prices/tomorrow",
                params={"format": "json"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

            data = response.json()
            assert "data" in data
            assert len(data["data"]) == 24

    def test_export_prices_week_xml(self, client, mock_price_data):
        """Test exporting week prices as XML."""
        with patch('app.services.entsoe_service.entsoe_service.get_day_ahead_prices', return_value=mock_price_data):
            response = client.get(
                "/api/v1/export/prices/week",
                params={"format": "xml"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/xml"

            content = response.text
            assert '<?xml version="1.0" encoding="UTF-8"?>' in content

    def test_export_prices_invalid_range(self, client):
        """Test exporting prices with invalid date range."""
        response = client.get(
            "/api/v1/export/prices/invalid_range",
            params={"format": "csv"}
        )

        assert response.status_code == 400

    def test_export_prices_no_data(self, client):
        """Test exporting prices when no data available."""
        with patch('app.services.entsoe_service.entsoe_service.get_today_prices', return_value=[]):
            response = client.get(
                "/api/v1/export/prices/today",
                params={"format": "csv"}
            )

            assert response.status_code == 404

    def test_export_all_dataset_types(self, client, mock_energy_data):
        """Test exporting all dataset types."""
        dataset_types = [
            DatasetType.CONSUMPTION_REALTIME,
            DatasetType.PRODUCTION_REALTIME,
            DatasetType.WIND_PRODUCTION,
            DatasetType.CONSUMPTION_FORECAST
        ]

        for dataset_type in dataset_types:
            mock_data = EnergyData(
                dataset_id=124,
                name=f"Test {dataset_type.value}",
                dataset_type=dataset_type,
                data=[EnergyDataPoint(timestamp=datetime.utcnow(), value=10000.0, unit="MW")],
                last_updated=datetime.utcnow(),
                metadata={}
            )

            service_methods = {
                DatasetType.CONSUMPTION_REALTIME: 'get_consumption_realtime',
                DatasetType.PRODUCTION_REALTIME: 'get_production_realtime',
                DatasetType.WIND_PRODUCTION: 'get_wind_production',
                DatasetType.CONSUMPTION_FORECAST: 'get_consumption_forecast'
            }

            with patch(f'app.services.fingrid_service.fingrid_service.{service_methods[dataset_type]}', return_value=mock_data):
                response = client.get(
                    f"/api/v1/export/fingrid/{dataset_type.value}",
                    params={"format": "csv"}
                )

                assert response.status_code == 200, f"Failed for {dataset_type.value}"


class TestExportService:
    """Test ExportService class directly."""

    def test_csv_export_format(self):
        """Test CSV export formatting."""
        from app.api.routes.export import export_service

        test_data = [
            {"timestamp": "2025-05-26T00:00:00", "value": 100.0, "unit": "MW"},
            {"timestamp": "2025-05-26T01:00:00", "value": 110.0, "unit": "MW"}
        ]

        result = export_service._export_csv(test_data, "test")

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert "timestamp,value,unit" in content
        assert "2025-05-26T00:00:00,100.0,MW" in content

    def test_json_export_format(self):
        """Test JSON export formatting."""
        from app.api.routes.export import export_service

        test_data = [
            {"timestamp": "2025-05-26T00:00:00", "value": 100.0, "unit": "MW"}
        ]
        metadata = {"name": "Test Dataset", "dataset_id": 124}

        result = export_service._export_json(test_data, metadata, "test")

        assert isinstance(result, bytes)
        content = json.loads(result.decode('utf-8'))
        assert "metadata" in content
        assert "data" in content
        assert content["metadata"]["dataset_name"] == "Test Dataset"
        assert len(content["data"]) == 1

    def test_xml_export_format(self):
        """Test XML export formatting."""
        from app.api.routes.export import export_service

        test_data = [
            {"timestamp": "2025-05-26T00:00:00", "value": 100.0, "unit": "MW"}
        ]

        result = export_service._export_xml(test_data, "test")

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert "<energy_data>" in content
        assert "<metadata>" in content
        assert "<data_points>" in content
        assert "<timestamp>2025-05-26T00:00:00</timestamp>" in content
        assert "<value>100.0</value>" in content
        assert "</energy_data>" in content

    def test_xml_escape_special_characters(self):
        """Test XML export escapes special characters."""
        from app.api.routes.export import export_service

        test_data = [
            {"timestamp": "2025-05-26T00:00:00", "value": "Test & < > Data", "unit": "MW"}
        ]

        result = export_service._export_xml(test_data, "test")
        content = result.decode('utf-8')

        assert "&amp;" in content
        assert "&lt;" in content
        assert "&gt;" in content
        assert "& < >" not in content  # Raw characters should be escaped
