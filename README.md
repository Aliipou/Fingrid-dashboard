# Fingrid Dashboard

Finland's electricity grid data is public and updated in real time via the Fingrid Open Data API. The problem is ergonomics: the raw API requires per-dataset ID knowledge, returns sparse JSON blobs with no analysis layer, and has no caching — so polling every minute from a browser hits rate limits and introduces multi-second latency on every page load. ENTSO-E data (day-ahead prices) is in a different API with XML responses and its own authentication scheme.

This dashboard unifies both data sources behind a single REST backend with Redis caching, serves a React frontend with live charts, and adds an analytics layer (efficiency metrics, production/consumption differential) that neither upstream API provides.

---

## Architecture

```
Browser (React + Recharts)
    |
    | HTTP (JSON)
    v
FastAPI Backend  (:8000)
    |
    |-- /api/v1/fingrid/*   -- FingridService
    |       |                     fetches datasets 124 (consumption), 192 (production),
    |       |                     181 (wind), 165 (forecast) from api.fingrid.fi
    |       |
    |-- /api/v1/entsoe/*   -- EntsoEClient
    |       |                     fetches day-ahead prices from web-api.tp.entsoe.eu
    |       |                     parses XML (area code 10YFI-1--------U for Finland)
    |       |
    |-- /api/v1/analytics/* -- AnalyticsService
    |       |                     merges datasets with pandas, computes efficiency
    |       |                     and production/consumption differential
    |       |
    |-- /api/v1/export/*    -- Excel export via openpyxl
    |
    v
Redis (:6379)
    Realtime datasets: 5-minute TTL
    Forecasts: 30-minute TTL
    Analytics results: 30-minute TTL
    Query cache keyed by (endpoint + sorted params)
```

The backend uses a write-through cache: every upstream API response is pickled into Redis before returning to the client. Subsequent requests for the same dataset within the TTL window never touch Fingrid or ENTSO-E. Rate limit and timeout errors from upstream are propagated as 500s to the frontend.

---

## Key Design Decisions

**Separate TTL per dataset type, not a uniform cache TTL.** Real-time consumption and production data updates every 3 minutes on the Fingrid side, so a 5-minute cache wastes one cycle at most. Day-ahead price forecasts update once per day; caching them for 30 minutes is safe and reduces upstream API calls by 6x. A uniform short TTL would thrash the forecast cache; a uniform long TTL would serve stale real-time data.

**Redis pickle serialization, not JSON.** The cache stores Python objects (Pydantic models, pandas DataFrames for analytics results) serialized with `pickle`. JSON serialization would require a custom encoder for every model field type (datetime, Decimal, nested dataclasses) and re-parsing on read. Pickle is simpler and faster at the cost of being non-portable between Python versions.

**Two separate upstream API clients, not a unified adapter.** Fingrid and ENTSO-E have incompatible auth schemes (API key header vs. query-string token), different base URLs, different response formats (JSON vs. XML), and different error codes. A unified adapter would need conditional logic for all of these. Two thin clients with clear responsibilities are easier to maintain.

**Redis sorted-set rate limiter in middleware, not FastAPI dependency injection.** The `RateLimitMiddleware` intercepts all requests at the ASGI layer before any route handler runs. A DI-based approach would require adding a `Depends(rate_limit)` to every route, which is error-prone. The middleware approach enforces the limit uniformly. Tradeoff: harder to configure different limits per endpoint.

**React with recharts, not a pre-built dashboard library.** Recharts gives direct control over chart composition (AreaChart, BarChart, PieChart, LineChart) and styling without fighting a dashboard framework's opinions about layout. Tradeoff: more component code than a library like Tremor or Grafana.

---

## Tech Stack

| Component | Justification |
|---|---|
| **FastAPI** | Async request handling; avoids blocking the event loop during upstream API calls |
| **httpx (AsyncClient)** | Non-blocking HTTP client for Fingrid and ENTSO-E calls; replaces requests for async compatibility |
| **Redis (redis-py async)** | In-memory cache with per-key TTL; eliminates repeated upstream API calls within polling windows |
| **pandas + numpy** | Analytics layer (merge, resample, efficiency metrics); upstream data arrives as point arrays, not aggregations |
| **lxml** | ENTSO-E API returns XML; lxml parses the Publication_MarketDocument format faster than stdlib xml.etree |
| **openpyxl** | Excel export; standard format for energy analysts who import data into their own tools |
| **React 18 + recharts** | Frontend; recharts provides composable chart primitives without a full dashboard framework |
| **GZipMiddleware** | Compresses responses > 1 KB; time-series payloads with many data points can reach 50-100 KB uncompressed |

---

## Running Locally

```bash
git clone https://github.com/Aliipou/Fingrid-dashboard.git
cd Fingrid-dashboard

# Obtain API keys
# Fingrid: https://data.fingrid.fi/en/instructions
# ENTSO-E: https://transparency.entsoe.eu/usrm/user/createPublicUser

# Create environment file
cat > .env << 'EOF'
FINGRID_API_KEY=your_fingrid_api_key_here
ENTSOE_API_KEY=your_entsoe_security_token_here
EOF

# Start all services (backend, frontend, redis)
docker compose up

# Backend available at: http://localhost:8000
# Frontend available at: http://localhost:3000
# API docs at: http://localhost:8000/api/docs
```

For local development without Docker:

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Redis (required for cache)
docker run -d -p 6379:6379 redis:7-alpine

# Frontend
cd frontend
npm install
npm start
```

Key endpoints:

```
GET /api/v1/fingrid/consumption/realtime    -- Total consumption (dataset 124), 5-min cache
GET /api/v1/fingrid/production/realtime     -- Total production (dataset 192), 5-min cache
GET /api/v1/fingrid/wind                    -- Wind production (dataset 181)
GET /api/v1/fingrid/forecast                -- Consumption forecast (dataset 165), 30-min cache
GET /api/v1/entsoe/prices                   -- Day-ahead electricity prices (XML parsed)
GET /api/v1/analytics/efficiency            -- Production/consumption efficiency metrics
GET /api/v1/export/excel                    -- Download current data as .xlsx
```

---

## Deployment

- **Redis 7+** — required; the backend degrades gracefully if Redis is unavailable (cache misses fall through to upstream), but upstream rate limits will be hit quickly without it
- **Two API keys** — Fingrid Open Data API key and ENTSO-E security token; both are free registrations
- **CORS configuration** — `CORS_ORIGINS` in `app/core/config.py` defaults to `localhost:3000`; update for production frontend domain
- **Production compose** — `docker-compose.prod.yml` is included with Nginx reverse proxy configuration
- **Kubernetes** — `k8s/` directory contains manifests for backend Deployment, Redis StatefulSet, and Ingress

---

## Known Limitations / TODO

- **No WebSocket push.** The frontend polls the backend on a timer. True real-time updates would require SSE or WebSocket; the 5-minute cache TTL means polling more frequently than that provides no benefit anyway.
- **ENTSO-E data is Finland-only.** The area code `10YFI-1--------U` is hardcoded in the ENTSO-E client. Supporting other Nordic countries would require parameterizing this.
- **Pickle cache is not forward-compatible.** Changing a Pydantic model shape invalidates cached entries silently (deserializing an old pickle into a new model shape raises an error that falls back to a cache miss). A cache flush or cache versioning strategy is needed when models change.
- **No authentication.** The API is open. Suitable for an internal dashboard on a private network; not for public deployment without adding an auth layer.
- **Analytics endpoint calls upstream twice per request.** `calculate_efficiency_metrics` fetches consumption and production data in sequence. These calls should be concurrent (`asyncio.gather`).
- **`asyncio-mqtt` is in requirements but unused.** Listed as a dependency; not referenced in any current service.
