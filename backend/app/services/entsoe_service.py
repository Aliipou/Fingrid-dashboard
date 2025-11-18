# backend/app/services/entsoe_service.py
import httpx
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.models.energy import PriceData
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class EntsoeService:
    """Service for interacting with ENTSO-E Transparency Platform API"""

    def __init__(self):
        self.base_url = settings.ENTSOE_BASE_URL
        self.api_key = settings.ENTSOE_API_KEY
        self.timeout = 30.0

        # Finland bidding zone code
        self.finland_code = "10YFI-1--------U"

        # Document types for different data
        self.document_types = {
            "day_ahead_prices": "A44",
            "load_forecast": "A65",
            "generation_forecast": "A71"
        }

    async def _make_request(self, params: Dict[str, Any]) -> str:
        """Make HTTP request to ENTSO-E API and return XML response"""
        headers = {
            "Accept": "application/xml",
            "User-Agent": "Fingrid-Dashboard/1.0"
        }

        # Add security token to params
        params["securityToken"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info("Making request to ENTSO-E API")
                response = await client.get(self.base_url, headers=headers, params=params)

                if response.status_code == 200:
                    logger.info("Successfully retrieved data from ENTSO-E API")
                    return response.text
                elif response.status_code == 401:
                    logger.error("ENTSO-E API authentication failed")
                    raise Exception("Invalid API key")
                elif response.status_code == 400:
                    logger.error(f"ENTSO-E API bad request: {response.text}")
                    raise Exception("Bad request to ENTSO-E API")
                elif response.status_code == 429:
                    logger.warning("ENTSO-E API rate limit exceeded")
                    raise Exception("Rate limit exceeded")
                else:
                    logger.error(f"ENTSO-E API error: {response.status_code} - {response.text}")
                    raise Exception(f"API error: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Timeout when calling ENTSO-E API")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error(f"Request error when calling ENTSO-E API: {str(e)}")
            raise Exception(f"Request failed: {str(e)}")

    def _parse_price_xml(self, xml_content: str) -> List[PriceData]:
        """Parse XML response containing price data"""
        try:
            root = ET.fromstring(xml_content)

            # Define namespace
            ns = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0'}

            price_data = []

            # Find all time series
            time_series_list = root.findall('.//ns:TimeSeries', ns)

            for time_series in time_series_list:
                # Get period
                period = time_series.find('.//ns:Period', ns)
                if period is None:
                    continue

                # Get start time
                start_time_elem = period.find('ns:timeInterval/ns:start', ns)
                if start_time_elem is None:
                    continue

                start_time_str = start_time_elem.text
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))

                # Get resolution (usually PT60M for hourly data)
                resolution_elem = period.find('ns:resolution', ns)
                resolution = resolution_elem.text if resolution_elem is not None else "PT60M"

                # Parse resolution to get minutes
                if resolution == "PT60M":
                    interval_minutes = 60
                elif resolution == "PT15M":
                    interval_minutes = 15
                else:
                    interval_minutes = 60  # Default to hourly

                # Get all price points
                points = period.findall('ns:Point', ns)

                for point in points:
                    position_elem = point.find('ns:position', ns)
                    price_elem = point.find('ns:price.amount', ns)

                    if position_elem is not None and price_elem is not None:
                        position = int(position_elem.text)
                        price = float(price_elem.text)

                        # Calculate timestamp for this point
                        point_time = start_time + timedelta(minutes=(position - 1) * interval_minutes)

                        price_data.append(PriceData(
                            timestamp=point_time,
                            price=price,
                            unit="EUR/MWh",
                            area="FI"
                        ))

            # Sort by timestamp
            price_data.sort(key=lambda x: x.timestamp)

            logger.info(f"Parsed {len(price_data)} price data points from ENTSO-E XML")
            return price_data

        except ET.ParseError as e:
            logger.error(f"Error parsing ENTSO-E XML response: {str(e)}")
            raise Exception(f"Failed to parse XML response: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing ENTSO-E price data: {str(e)}")
            raise Exception(f"Failed to process price data: {str(e)}")

    async def get_day_ahead_prices(self, date: datetime) -> List[PriceData]:
        """Get day-ahead electricity prices for specified date"""
        cache_key = f"entsoe:prices:{date.strftime('%Y%m%d')}"

        # Try cache first
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            logger.info(f"Returning cached price data for {date.date()}")
            return [PriceData(**item) for item in cached_data]

        # Format date for API (ENTSO-E expects YYYYMMDDHHMM format)
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        params = {
            "documentType": self.document_types["day_ahead_prices"],
            "in_Domain": self.finland_code,
            "out_Domain": self.finland_code,
            "periodStart": start_date.strftime("%Y%m%d%H%M"),
            "periodEnd": end_date.strftime("%Y%m%d%H%M")
        }

        try:
            xml_response = await self._make_request(params)
            price_data = self._parse_price_xml(xml_response)

            # Cache for 6 hours (prices don't change once published)
            price_data_dict = [price.dict() for price in price_data]
            await cache_service.set(cache_key, price_data_dict, ttl=21600)

            return price_data

        except Exception as e:
            logger.error(f"Error fetching day-ahead prices: {str(e)}")
            raise Exception(f"Failed to fetch prices: {str(e)}")

    async def get_tomorrow_prices(self) -> List[PriceData]:
        """Get tomorrow's day-ahead prices"""
        tomorrow = datetime.utcnow() + timedelta(days=1)
        return await self.get_day_ahead_prices(tomorrow)

    async def get_today_prices(self) -> List[PriceData]:
        """Get today's day-ahead prices"""
        today = datetime.utcnow()
        return await self.get_day_ahead_prices(today)

    async def get_price_statistics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get price statistics for a date range"""
        cache_key = f"entsoe:price_stats:{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"

        # Try cache first
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return cached_data

        try:
            all_prices = []
            current_date = start_date

            # Fetch prices for each day in range
            while current_date <= end_date:
                try:
                    daily_prices = await self.get_day_ahead_prices(current_date)
                    all_prices.extend(daily_prices)
                except Exception as e:
                    logger.warning(f"Failed to get prices for {current_date.date()}: {str(e)}")

                current_date += timedelta(days=1)

            if not all_prices:
                raise Exception("No price data available for the specified period")

            # Calculate statistics
            prices = [p.price for p in all_prices]

            statistics = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "total_hours": len(all_prices)
                },
                "price_statistics": {
                    "average": round(sum(prices) / len(prices), 2),
                    "median": round(sorted(prices)[len(prices) // 2], 2),
                    "minimum": round(min(prices), 2),
                    "maximum": round(max(prices), 2),
                    "standard_deviation": round((sum((p - sum(prices) / len(prices)) ** 2 for p in prices) / len(prices)) ** 0.5, 2)
                },
                "price_ranges": {
                    "negative_hours": len([p for p in prices if p < 0]),
                    "low_price_hours": len([p for p in prices if 0 <= p < 20]),
                    "medium_price_hours": len([p for p in prices if 20 <= p < 60]),
                    "high_price_hours": len([p for p in prices if p >= 60])
                },
                "hourly_averages": {},
                "generated_at": datetime.utcnow().isoformat()
            }

            # Calculate hourly averages
            hourly_data = {}
            for price_point in all_prices:
                hour = price_point.timestamp.hour
                if hour not in hourly_data:
                    hourly_data[hour] = []
                hourly_data[hour].append(price_point.price)

            for hour, hour_prices in hourly_data.items():
                statistics["hourly_averages"][str(hour)] = round(sum(hour_prices) / len(hour_prices), 2)

            # Cache for 1 hour
            await cache_service.set(cache_key, statistics, ttl=3600)

            return statistics

        except Exception as e:
            logger.error(f"Error calculating price statistics: {str(e)}")
            raise Exception(f"Failed to calculate statistics: {str(e)}")

# Initialize service
entsoe_service = EntsoeService()
