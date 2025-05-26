import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from app.core.config import settings
from app.models.energy import PriceData

logger = logging.getLogger(__name__)

class EntsoEClient:
    """Async client for Entso-E Transparency Platform API"""
    
    def __init__(self):
        self.base_url = settings.ENTSOE_BASE_URL
        self.api_key = settings.ENTSOE_API_KEY
        self.client = None
        
        # Finland area code in Entso-E
        self.finland_area_code = "10YFI-1--------U"
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def _make_request(self, params: Dict[str, Any]) -> str:
        """Make authenticated request to Entso-E API"""
        try:
            params["securityToken"] = self.api_key
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"Entso-E HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Entso-E request failed: {str(e)}")
            raise
    
    def _parse_price_xml(self, xml_content: str) -> List[PriceData]:
        """Parse XML response containing price data"""
        try:
            root = ET.fromstring(xml_content)
            
            # Define namespace
            ns = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}
            
            prices = []
            
            # Find all TimeSeries elements
            for timeseries in root.findall('.//ns:TimeSeries', ns):
                # Get the period
                period = timeseries.find('.//ns:Period', ns)
                if period is None:
                    continue
                
                # Get start time
                start_elem = period.find('ns:timeInterval/ns:start', ns)
                if start_elem is None:
                    continue
                
                start_time = datetime.fromisoformat(start_elem.text.replace('Z', '+00:00'))
                
                # Get resolution (usually PT60M for hourly data)
                resolution_elem = period.find('ns:resolution', ns)
                resolution = resolution_elem.text if resolution_elem is not None else "PT60M"
                
                # Calculate time delta based on resolution
                if resolution == "PT60M":
                    time_delta = timedelta(hours=1)
                elif resolution == "PT15M":
                    time_delta = timedelta(minutes=15)
                else:
                    time_delta = timedelta(hours=1)  # Default to hourly
                
                # Get all price points
                for point in period.findall('ns:Point', ns):
                    position_elem = point.find('ns:position', ns)
                    price_elem = point.find('ns:price.amount', ns)
                    
                    if position_elem is not None and price_elem is not None:
                        position = int(position_elem.text)
                        price = float(price_elem.text)
                        
                        # Calculate timestamp (position starts from 1)
                        timestamp = start_time + time_delta * (position - 1)
                        
                        prices.append(PriceData(
                            timestamp=timestamp,
                            price=price,
                            unit="EUR/MWh",
                            area="FI"
                        ))
            
            return sorted(prices, key=lambda x: x.timestamp)
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse Entso-E XML: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing Entso-E price data: {e}")
            raise
    
    async def get_day_ahead_prices(self, date: datetime = None) -> List[PriceData]:
        """Get day-ahead electricity prices for Finland"""
        if date is None:
            # Get tomorrow's prices
            date = datetime.now() + timedelta(days=1)
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        params = {
            "documentType": "A44",  # Price document
            "in_Domain": self.finland_area_code,
            "out_Domain": self.finland_area_code,
            "periodStart": start_date.strftime("%Y%m%d%H%M"),
            "periodEnd": end_date.strftime("%Y%m%d%H%M")
        }
        
        xml_response = await self._make_request(params)
        return self._parse_price_xml(xml_response)
    
    async def get_current_week_prices(self) -> List[PriceData]:
        """Get electricity prices for the current week"""
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=7)
        
        params = {
            "documentType": "A44",
            "in_Domain": self.finland_area_code,
            "out_Domain": self.finland_area_code,
            "periodStart": start_of_week.strftime("%Y%m%d%H%M"),
            "periodEnd": end_of_week.strftime("%Y%m%d%H%M")
        }
        
        xml_response = await self._make_request(params)
        return self._parse_price_xml(xml_response)