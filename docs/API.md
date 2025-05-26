# 📚 Fingrid Energy Dashboard API Documentation

## 🎯 Overview

The Fingrid Energy Dashboard API provides real-time access to Finnish energy data from **Fingrid Open Data** and **ENTSO-E Transparency Platform**. Built with FastAPI, it follows RESTful principles and provides comprehensive energy monitoring capabilities.

**🔗 Base URL**: `http://localhost:8000/api/v1`  
**📖 Interactive Docs**: `http://localhost:8000/api/docs`  
**🔄 OpenAPI Spec**: `http://localhost:8000/openapi.json`

## 🔐 Authentication

Currently, the API is **publicly accessible** for basic energy data. API keys may be required for premium analytics features in future versions.

## ⚡ Rate Limiting

- **Basic Tier**: 100 requests per minute
- **Burst Limit**: 20 requests per 10 seconds  
- **Hourly Limit**: 1,000 requests per hour

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1640995200
Retry-After: 30
```

## 🏥 Health & Status

### GET `/health`
Check API service health and status.

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "service": "fingrid-dashboard-api", 
  "version": "1.0.0"
}
```

## ⚡ Fingrid Energy Data

### Real-time Consumption
#### GET `/fingrid/consumption/realtime`
Get real-time electricity consumption data for Finland.

**Response**: `200 OK`
```json
{
  "dataset_id": 124,
  "name": "Electricity consumption - real time data",
  "dataset_type": "consumption_realtime",
  "data": [
    {
      "timestamp": "2025-05-26T10:30:00Z",
      "value": 10500.0,
      "unit": "MW"
    }
  ],
  "last_updated": "2025-05-26T10:35:00Z",
  "metadata": {
    "source": "Fingrid Open Data API",
    "total_points": 288
  }
}
```

### Real-time Production  
#### GET `/fingrid/production/realtime`
Get real-time electricity production data for Finland.

### Wind Power Production
#### GET `/fingrid/wind/realtime`  
Get real-time wind power production data.

### Consumption Forecast
#### GET `/fingrid/consumption/forecast`
Get 24-hour electricity consumption forecast.

### Production vs Consumption Analysis
#### GET `/fingrid/differential`
Get detailed production vs consumption differential analysis.

**Response**: `200 OK`
```json
{
  "analysis_period": "24 hours",
  "data": [
    {
      "timestamp": "2025-05-26T10:00:00Z",
      "production": 11200.0,
      "consumption": 10800.0,
      "differential": 400.0,
      "status": "surplus",
      "percentage": 3.7
    }
  ],
  "summary": {
    "average_differential_mw": 250.5,
    "total_surplus_mwh": 1500.0,
    "total_deficit_mwh": 800.0,
    "surplus_periods": 15,
    "deficit_periods": 8,
    "balanced_periods": 1
  },
  "generated_at": "2025-05-26T10:35:00Z"
}
```

### Comprehensive Dashboard Data
#### GET `/fingrid/dashboard`
Get all dashboard data in a single optimized request.

**Response**: `200 OK`
```json
{
  "consumption_realtime": { /* EnergyData object */ },
  "production_realtime": { /* EnergyData object */ },
  "wind_production": { /* EnergyData object */ },
  "consumption_forecast": { /* EnergyData object */ },
  "last_updated": "2025-05-26T10:35:00Z",
  "status": "success"
}
```

## 💰 ENTSO-E Electricity Prices

### Today's Prices
#### GET `/entsoe/prices/today`
Get today's day-ahead electricity prices for Finland.

### Tomorrow's Prices
#### GET `/entsoe/prices/tomorrow`  
Get tomorrow's day-ahead electricity prices.

**Response**: `200 OK`
```json
[
  {
    "timestamp": "2025-05-27T00:00:00Z",
    "price": 45.67,
    "unit": "EUR/MWh", 
    "area": "FI"
  },
  {
    "timestamp": "2025-05-27T01:00:00Z",
    "price": 42.15,
    "unit": "EUR/MWh",
    "area": "FI"
  }
]
```

### Weekly Prices
#### GET `/entsoe/prices/week`
Get current week's electricity prices.

## 📊 Advanced Analytics

### Energy Efficiency Analysis
#### GET `/analytics/efficiency`
Calculate comprehensive energy efficiency metrics.

**Query Parameters**:
- `start_date` *(required)*: ISO 8601 datetime
- `end_date` *(required)*: ISO 8601 datetime

**Example**: `/analytics/efficiency?start_date=2025-05-26T00:00:00Z&end_date=2025-05-27T00:00:00Z`

**Response**: `200 OK`
```json
{
  "period": {
    "start": "2025-05-26T00:00:00Z",
    "end": "2025-05-27T00:00:00Z",
    "duration_hours": 24
  },
  "totals": {
    "consumption_mwh": 252000.0,
    "production_mwh": 258000.0,
    "net_balance_mwh": 6000.0
  },
  "efficiency": {
    "production_consumption_ratio": 102.38,
    "surplus_hours": 18,
    "deficit_hours": 6,
    "balanced_hours": 0
  },
  "peaks": {
    "consumption_peak_mw": 11800.0,
    "consumption_peak_time": "2025-05-26T18:00:00Z",
    "production_peak_mw": 12200.0,
    "production_peak_time": "2025-05-26T14:00:00Z"
  },
  "variability": {
    "consumption_coefficient_variation": 8.5,
    "production_coefficient_variation": 12.3
  }
}
```

### Anomaly Detection
#### GET `/analytics/anomalies`
Detect statistical anomalies in energy data.

**Query Parameters**:
- `dataset_type` *(required)*: `consumption_realtime`, `production_realtime`, `wind_production`
- `start_date` *(required)*: ISO 8601 datetime  
- `end_date` *(required)*: ISO 8601 datetime
- `threshold` *(optional)*: Standard deviation threshold (default: 2.0)

### Forecast Accuracy Analysis
#### GET `/analytics/forecast-accuracy`
Analyze accuracy of consumption forecasts vs actual data.

**Query Parameters**:
- `start_date` *(required)*: ISO 8601 datetime
- `end_date` *(required)*: ISO 8601 datetime

### Trend Analysis
#### GET `/analytics/trends`
Analyze trends in energy data over time.

**Query Parameters**:
- `dataset_type` *(required)*: Dataset type to analyze
- `start_date` *(required)*: ISO 8601 datetime
- `end_date` *(required)*: ISO 8601 datetime  
- `period` *(optional)*: Aggregation period (`hourly`, `daily`, `weekly`)

## 📤 Data Export

### Export Energy Data
#### GET `/export/fingrid/{dataset_type}`
Export Fingrid data in various formats.

**Path Parameters**:
- `dataset_type`: `consumption_realtime`, `production_realtime`, `wind_production`, `consumption_forecast`

**Query Parameters**:
- `start_date` *(required)*: ISO 8601 datetime
- `end_date` *(required)*: ISO 8601 datetime
- `format` *(required)*: Export format (`csv`, `json`, `excel`, `xml`)

**Example**: `/export/fingrid/consumption_realtime?start_date=2025-05-26T00:00:00Z&end_date=2025-05-27T00:00:00Z&format=csv`

## ❌ Error Responses

The API uses standard HTTP status codes with detailed error information:

**Status Codes**:
- `200` - OK  
- `400` - Bad Request
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
- `503` - Service Unavailable

**Error Response Format**:
```json
{
  "detail": "Detailed error description",
  "error_code": "SPECIFIC_ERROR_CODE", 
  "timestamp": "2025-05-26T10:30:00Z",
  "request_id": "req_12345"
}
```

**Common Error Examples**:

**Validation Error (422)**:
```json
{
  "detail": [
    {
      "loc": ["query", "start_date"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Rate Limit Error (429)**:
```json
{
  "error": "Rate limit exceeded",
  "detail": "100 requests per minute limit exceeded", 
  "retry_after": 42
}
```

## 📡 Data Sources & Updates

### Data Sources
- **Fingrid Open Data API**: Real-time production, consumption, and forecasts
- **ENTSO-E Transparency Platform**: Day-ahead electricity market prices

### Update Frequencies  
- **Real-time data**: ~3 minutes
- **Forecasts**: Every hour
- **Day-ahead prices**: Daily at 13:00 CET
- **Analytics**: On-demand with 30-minute cache

### Data Coverage
- **Geographic**: Finland (FI bidding zone)
- **Historical**: Up to 3 years of historical data
- **Real-time**: Last 7 days continuously updated
- **Forecast**: Next 24-48 hours

## 💻 SDK Examples

### Python Example
```python
import httpx
import asyncio
from datetime import datetime, timedelta

class FingridClient:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        
    async def get_current_consumption(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/fingrid/consumption/realtime")
            data = response.json()
            return data['data'][-1]['value']  # Latest value
    
    async def get_dashboard_data(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/fingrid/dashboard")
            return response.json()

# Usage
async def main():
    client = FingridClient()
    consumption = await client.get_current_consumption()
    print(f"Current consumption: {consumption} MW")

asyncio.run(main())
```

### JavaScript/TypeScript Example
```typescript
interface EnergyData {
  dataset_id: number;
  name: string;
  dataset_type: string;
  data: Array<{
    timestamp: string;
    value: number;
    unit: string;
  }>;
  last_updated: string;
}

class FingridAPI {
  constructor(private baseUrl = '/api/v1') {}
  
  async getCurrentConsumption(): Promise<number> {
    const response = await fetch(`${this.baseUrl}/fingrid/consumption/realtime`);
    const data: EnergyData = await response.json();
    return data.data[data.data.length - 1].value;
  }
  
  async getDashboardData() {
    const response = await fetch(`${this.baseUrl}/fingrid/dashboard`);
    return response.json();
  }
  
  async getTomorrowPrices() {
    const response = await fetch(`${this.baseUrl}/entsoe/prices/tomorrow`);
    return response.json();
  }
}

// Usage
const api = new FingridAPI();
api.getCurrentConsumption().then(consumption => {
  console.log(`Current consumption: ${consumption} MW`);
});
```

### cURL Examples
```bash
# Get current consumption
curl "http://localhost:8000/api/v1/fingrid/consumption/realtime"

# Get efficiency analysis
curl "http://localhost:8000/api/v1/analytics/efficiency?start_date=2025-05-26T00:00:00Z&end_date=2025-05-27T00:00:00Z"

# Export data as CSV
curl "http://localhost:8000/api/v1/export/fingrid/consumption_realtime?start_date=2025-05-26T00:00:00Z&end_date=2025-05-27T00:00:00Z&format=csv" \
  -H "Accept: text/csv" \
  -o consumption_data.csv
```

## 🔮 Future Features

### Planned Enhancements
- **WebSocket Support**: Real-time data streaming
- **Webhooks**: Event-driven notifications  
- **GraphQL API**: Flexible data querying
- **Machine Learning**: Predictive analytics
- **Mobile SDKs**: Native iOS/Android libraries

### API Versioning
- Current version: `v1`
- Deprecation policy: 12 months notice
- Version in URL path: `/api/v1/`, `/api/v2/`

---

## 🆘 Support

**Documentation**: [GitHub Repository](https://github.com/aliipou/fingrid-dashboard)  
**Issues**: [GitHub Issues](https://github.com/aliipou/fingrid-dashboard/issues)  
**API Status**: [Status Page](http://localhost:8000/api/v1/health)

---

*Last updated: May 26, 2025 | Version 1.0.0*