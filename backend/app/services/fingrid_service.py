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
        start_date: datetime = None,
        end_date: datetime = None
    ) -> EnergyData:
        """Get real-time electricity consumption data"""
        if start_date is None:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.utcnow()

        return await self._fetch_dataset(
            self.datasets[DatasetType.CONSUMPTION_REALTIME],
            DatasetType.CONSUMPTION_REALTIME,
            start_date,
            end_date
        )

    async def get_production_realtime(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> EnergyData:
        """Get real-time electricity production data"""
        if start_date is None:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.utcnow()

        return await self._fetch_dataset(
            self.datasets[DatasetType.PRODUCTION_REALTIME],
            DatasetType.PRODUCTION_REALTIME,
            start_date,
            end_date
        )

    async def get_wind_production(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> EnergyData:
        """Get wind power production data"""
        if start_date is None:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.utcnow()

        return await self._fetch_dataset(
            self.datasets[DatasetType.WIND_PRODUCTION],
            DatasetType.WIND_PRODUCTION,
            start_date,
            end_date
        )

    async def get_consumption_forecast(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> EnergyData:
        """Get consumption forecast data"""
        if start_date is None:
            end_date = datetime.utcnow() + timedelta(hours=24)
            start_date = datetime.utcnow()
        if end_date is None:
            end_date = start_date + timedelta(hours=24)

        return await self._fetch_dataset(
            self.datasets[DatasetType.CONSUMPTION_FORECAST],
            DatasetType.CONSUMPTION_FORECAST,
            start_date,
            end_date
        )

    async def get_all_realtime_data(self) -> Dict[str, EnergyData]:
        """Get all realtime data in a single call"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        try:
            consumption = await self.get_consumption_realtime(start_time, end_time)
            production = await self.get_production_realtime(start_time, end_time)
            wind = await self.get_wind_production(start_time, end_time)
            forecast = await self.get_consumption_forecast()

            return {
                "consumption": consumption,
                "production": production,
                "wind": wind,
                "forecast": forecast
            }
        except Exception as e:
            logger.error(f"Error fetching all realtime data: {str(e)}")
            raise

    async def get_differential_analysis(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> DifferentialAnalysis:
        """Get production vs consumption differential analysis"""
        if start_date is None:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.utcnow()

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
