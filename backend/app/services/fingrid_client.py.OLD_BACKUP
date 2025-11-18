# backend/app/services/fingrid_service.py
import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.models.energy import EnergyData, EnergyDataPoint, DatasetType, DifferentialAnalysis, DifferentialPoint
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class FingridService:
    """Service for interacting with Fingrid Open Data API"""
    
    def __init__(self):
        self.base_url = settings.FINGRID_BASE_URL
        self.api_key = settings.FINGRID_API_KEY
        self.timeout = 30.0
        
        # Dataset IDs from Fingrid API
        self.datasets = {
            DatasetType.CONSUMPTION_REALTIME: 124,  # Total consumption
            DatasetType.PRODUCTION_REALTIME: 192,   # Total production
            DatasetType.WIND_PRODUCTION: 181,       # Wind power production
            DatasetType.CONSUMPTION_FORECAST: 165,  # Consumption forecast
        }
        
        # Cache TTL settings
        self.cache_ttl = {
            DatasetType.CONSUMPTION_REALTIME: 300,   # 5 minutes
            DatasetType.PRODUCTION_REALTIME: 300,    # 5 minutes  
            DatasetType.WIND_PRODUCTION: 300,        # 5 minutes
            DatasetType.CONSUMPTION_FORECAST: 1800,  # 30 minutes
        }
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request to Fingrid API with error handling"""
        headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "Fingrid-Dashboard/1.0"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Making request to Fingrid API: {endpoint}")
                response = await client.get(url, headers=headers, params=params or {})
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully retrieved data from {endpoint}")
                    return data
                elif response.status_code == 401:
                    logger.error("Fingrid API authentication failed - check API key")
                    raise Exception("Invalid API key")
                elif response.status_code == 429:
                    logger.warning("Fingrid API rate limit exceeded")
                    raise Exception("Rate limit exceeded")
                elif response.status_code == 404:
                    logger.warning(f"Fingrid API endpoint not found: {endpoint}")
                    raise Exception("Data not found")
                else:
                    logger.error(f"Fingrid API error: {response.status_code} - {response.text}")
                    raise Exception(f"API error: {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout when calling Fingrid API: {endpoint}")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error(f"Request error when calling Fingrid API: {str(e)}")
            raise Exception(f"Request failed: {str(e)}")
    
    async def _fetch_dataset(
        self, 
        dataset_id: int, 
        dataset_type: DatasetType,
        start_date: datetime, 
        end_date: datetime
    ) -> EnergyData:
        """Fetch data for a specific dataset"""
        
        # Create cache key
        cache_key = f"fingrid:{dataset_type.value}:{start_date.isoformat()}:{end_date.isoformat()}"
        
        # Try cache first
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            logger.info(f"Returning cached data for {dataset_type.value}")
            return EnergyData(**cached_data)
        
        # Format dates for API
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        params = {
            "start_time": start_str,
            "end_time": end_str,
            "format": "json"
        }
        
        try:
            # Make API request
            data = await self._make_request(f"/variable/{dataset_id}/events/json", params)
            
            # Parse response
            data_points = []
            for item in data.get("data", []):
                try:
                    timestamp = datetime.fromisoformat(item["start_time"].replace("Z", "+00:00"))
                    value = float(item["value"])
                    
                    data_points.append(EnergyDataPoint(
                        timestamp=timestamp,
                        value=value,
                        unit="MW"
                    ))
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid data point: {item} - {str(e)}")
                    continue
            
            # Create energy data object
            energy_data = EnergyData(
                dataset_id=dataset_id,
                name=data.get("variable", {}).get("name", f"Dataset {dataset_id}"),
                dataset_type=dataset_type,
                data=data_points,
                last_updated=datetime.utcnow(),
                metadata={
                    "source": "Fingrid Open Data API",
                    "dataset_id": dataset_id,
                    "total_points": len(data_points),
                    "date_range": {
                        "start": start_str,
                        "end": end_str
                    }
                }
            )
            
            # Cache the result
            ttl = self.cache_ttl.get(dataset_type, 300)
            await cache_service.set(cache_key, energy_data.dict(), ttl=ttl)
            
            logger.info(f"Retrieved {len(data_points)} data points for {dataset_type.value}")
            return energy_data
            
        except Exception as e:
            logger.error(f"Error fetching {dataset_type.value}: {str(e)}")
            raise Exception(f"Failed to fetch {dataset_type.value}: {str(e)}")
    
    async def get_consumption_realtime(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> EnergyData:
        """Get real-time electricity consumption data"""
        return await self._fetch_dataset(
            self.datasets[DatasetType.CONSUMPTION_REALTIME],
            DatasetType.CONSUMPTION_REALTIME,
            start_date,
            end_date
        )
    
    async def get_production_realtime(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> EnergyData:
        """Get real-time electricity production data"""
        return await self._fetch_dataset(
            self.datasets[DatasetType.PRODUCTION_REALTIME],
            DatasetType.PRODUCTION_REALTIME,
            start_date,
            end_date
        )
    
    async def get_wind_production(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> EnergyData:
        """Get wind power production data"""
        return await self._fetch_dataset(
            self.datasets[DatasetType.WIND_PRODUCTION],
            DatasetType.WIND_PRODUCTION,
            start_date,
            end_date
        )
    
    async def get_consumption_forecast(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> EnergyData:
        """Get consumption forecast data"""
        return await self._fetch_dataset(
            self.datasets[DatasetType.CONSUMPTION_FORECAST],
            DatasetType.CONSUMPTION_FORECAST,
            start_date,
            end_date
        )
    
    async def get_differential_analysis(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> DifferentialAnalysis:
        """Get production vs consumption differential analysis"""
        cache_key = f"fingrid:differential:{start_date.isoformat()}:{end_date.isoformat()}"
        
        # Try cache first
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return DifferentialAnalysis(**cached_data)
        
        try:
            # Get both production and consumption data
            production_data = await self.get_production_realtime(start_date, end_date)
            consumption_data = await self.get_consumption_realtime(start_date, end_date)
            
            if not production_data.data or not consumption_data.data:
                raise Exception("Insufficient data for differential analysis")
            
            # Create lookup dictionary for consumption data
            consumption_lookup = {
                point.timestamp: point.value 
                for point in consumption_data.data
            }
            
            # Calculate differentials
            differential_points = []
            total_surplus = 0
            total_deficit = 0
            balanced_count = 0
            
            for prod_point in production_data.data:
                timestamp = prod_point.timestamp
                production = prod_point.value
                
                # Find corresponding consumption value
                consumption = consumption_lookup.get(timestamp)
                if consumption is None:
                    continue
                
                # Calculate differential
                differential = production - consumption
                percentage = (differential / consumption) * 100 if consumption > 0 else 0
                
                # Determine status
                if abs(differential) <= consumption * 0.01:  # Within 1%
                    status = "balanced"
                    balanced_count += 1
                elif differential > 0:
                    status = "surplus"
                    total_surplus += differential
                else:
                    status = "deficit"
                    total_deficit += abs(differential)
                
                differential_points.append(DifferentialPoint(
                    timestamp=timestamp,
                    production=production,
                    consumption=consumption,
                    differential=differential,
                    status=status,
                    percentage=round(percentage, 2)
                ))
            
            # Calculate summary statistics
            total_points = len(differential_points)
            surplus_hours = len([p for p in differential_points if p.status == "surplus"])
            deficit_hours = len([p for p in differential_points if p.status == "deficit"])
            
            summary = {
                "total_data_points": total_points,
                "surplus_hours": surplus_hours,
                "deficit_hours": deficit_hours,
                "balanced_hours": balanced_count,
                "surplus_percentage": round((surplus_hours / total_points) * 100, 2) if total_points > 0 else 0,
                "deficit_percentage": round((deficit_hours / total_points) * 100, 2) if total_points > 0 else 0,
                "total_surplus_mwh": round(total_surplus, 2),
                "total_deficit_mwh": round(total_deficit, 2),
                "net_balance_mwh": round(total_surplus - total_deficit, 2)
            }
            
            analysis = DifferentialAnalysis(
                analysis_period=f"{start_date.isoformat()} to {end_date.isoformat()}",
                data=differential_points,
                summary=summary,
                generated_at=datetime.utcnow()
            )
            
            # Cache result
            await cache_service.set(cache_key, analysis.dict(), ttl=600)  # 10 minutes
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error calculating differential analysis: {str(e)}")
            raise Exception(f"Differential analysis failed: {str(e)}")
    
    async def get_latest_data(self) -> Dict[str, Any]:
        """Get latest available data points for dashboard"""
        cache_key = "fingrid:latest_data"
        
        # Try cache first
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get data for the last 2 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=2)
            
            # Fetch latest data for each type
            consumption_data = await self.get_consumption_realtime(start_time, end_time)
            production_data = await self.get_production_realtime(start_time, end_time)
            wind_data = await self.get_wind_production(start_time, end_time)
            
            # Get latest values
            latest_data = {
                "timestamp": end_time.isoformat(),
                "consumption": {
                    "value": consumption_data.data[-1].value if consumption_data.data else 0,
                    "unit": "MW",
                    "last_updated": consumption_data.data[-1].timestamp.isoformat() if consumption_data.data else None
                },
                "production": {
                    "value": production_data.data[-1].value if production_data.data else 0,
                    "unit": "MW", 
                    "last_updated": production_data.data[-1].timestamp.isoformat() if production_data.data else None
                },
                "wind_production": {
                    "value": wind_data.data[-1].value if wind_data.data else 0,
                    "unit": "MW",
                    "last_updated": wind_data.data[-1].timestamp.isoformat() if wind_data.data else None
                }
            }
            
            # Calculate additional metrics
            if latest_data["consumption"]["value"] > 0 and latest_data["production"]["value"] > 0:
                production_ratio = (latest_data["production"]["value"] / latest_data["consumption"]["value"]) * 100
                balance = latest_data["production"]["value"] - latest_data["consumption"]["value"]
                
                latest_data["metrics"] = {
                    "production_consumption_ratio": round(production_ratio, 2),
                    "balance_mw": round(balance, 2),
                    "status": "surplus" if balance > 0 else "deficit" if balance < 0 else "balanced",
                    "wind_percentage_of_production": round(
                        (latest_data["wind_production"]["value"] / latest_data["production"]["value"]) * 100, 2
                    ) if latest_data["production"]["value"] > 0 else 0
                }
            
            # Cache for 2 minutes
            await cache_service.set(cache_key, latest_data, ttl=120)
            
            return latest_data
            
        except Exception as e:
            logger.error(f"Error getting latest data: {str(e)}")
            raise Exception(f"Failed to get latest data: {str(e)}")

# Initialize service
fingrid_service = FingridService()


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


# backend/app/services/cache_service.py
import redis.asyncio as redis
import json
import logging
from typing import Any, Optional, Union
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service for energy data"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = settings.REDIS_URL
        self.default_ttl = settings.CACHE_TTL
        self.key_prefix = "fingrid_dashboard:"
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            prefixed_key = self._make_key(key)
            value = await self.redis_client.get(prefixed_key)
            
            if value is not None:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss for key: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        if not self.redis_client:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            json_value = json.dumps(value, default=str)
            
            ttl = ttl or self.default_ttl
            
            await self.redis_client.setex(prefixed_key, ttl, json_value)
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            result = await self.redis_client.delete(prefixed_key)
            logger.debug(f"Deleted cache key: {key}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            result = await self.redis_client.exists(prefixed_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error checking cache existence: {str(e)}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            prefixed_pattern = self._make_key(pattern)
            keys = await self.redis_client.keys(prefixed_pattern)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache keys matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error clearing cache pattern: {str(e)}")
            return 0
    
    async def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            
            # Get keys count for our prefix
            keys = await self.redis_client.keys(f"{self.key_prefix}*")
            
            return {
                "status": "connected",
                "total_keys": len(keys),
                "redis_version": info.get("redis_version", "unknown"),
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def health_check(self) -> dict:
        """Perform health check on cache service"""
        try:
            if not self.redis_client:
                return {"healthy": False, "error": "Not connected to Redis"}
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = {"timestamp": str(datetime.utcnow()), "test": True}
            
            # Test set
            await self.set(test_key, test_value, ttl=10)
            
            # Test get
            retrieved = await self.get(test_key)
            
            # Test delete
            await self.delete(test_key)
            
            if retrieved and retrieved.get("test") is True:
                return {"healthy": True, "message": "All cache operations working"}
            else:
                return {"healthy": False, "error": "Cache operations failed"}
                
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return {"healthy": False, "error": str(e)}

# Initialize cache service
cache_service = CacheService()


# backend/app/services/__init__.py
"""
Services package for Fingrid Dashboard API
==========================================

Contains service classes for:
- Fingrid API integration
- ENTSO-E API integration  
- Caching with Redis
- Data processing and analytics
"""

from .fingrid_service import fingrid_service
from .entsoe_service import entsoe_service
from .cache_service import cache_service

__all__ = [
    "fingrid_service",
    "entsoe_service", 
    "cache_service"
]