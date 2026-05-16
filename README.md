<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&amp;color=gradient&amp;customColorList=4,10,18&amp;height=180&amp;section=header&amp;text=Fingrid%20Energy%20Dashboard&amp;fontSize=36&amp;fontColor=fff&amp;animation=twinkling&amp;fontAlignY=38" />

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&amp;logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&amp;logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&amp;logo=react)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

**Real-time Finnish electricity market monitoring powered by Fingrid Open Data API.**

</div>

## Overview

Finland's electricity market data is public and updated in real time. This dashboard makes it actually usable: live grid frequency, production by source, consumption forecasts, CO2 intensity, and cross-border flows — all in one place.

## Features

**Live Grid Data**
Electricity production by source (nuclear, hydro, wind, solar, gas), real-time consumption, and grid frequency. Data updates every minute.

**CO2 Intensity Tracking**
Grams of CO2 per kWh, computed from the current production mix. Useful for scheduling energy-intensive tasks when the grid is cleanest.

**Cross-Border Flows**
Import and export with Sweden, Norway, Estonia, and Russia. Shows when Finland is a net exporter or importer.

**Historical Analysis**
Time-series charts with configurable lookback. Compare today to last week, last month, or same day last year.

## Quick Start

```bash
git clone https://github.com/Aliipou/Fingrid-dashboard.git
cd Fingrid-dashboard

# Backend
cd backend && pip install -r requirements.txt
export FINGRID_API_KEY=your-key  # Get from data.fingrid.fi
uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

Dashboard at `http://localhost:5173`

## Data Sources

All data from [Fingrid Open Data API](https://data.fingrid.fi/) — free to use with registration.

## License

MIT

## Architecture

```
Fingrid-dashboard/
├── backend/           # FastAPI service
│   └── app/
│       ├── api/       # Route handlers
│       ├── services/  # Fingrid & ENTSO-E API clients, caching logic
│       ├── models/    # Pydantic schemas
│       └── core/      # Config, Redis client
├── frontend/          # React + Vite SPA
│   └── src/           # Components, hooks, charts
├── k8s/               # Kubernetes manifests
└── docker-compose.yml # Local dev stack
```

**Request flow:** React frontend polls the FastAPI backend every 60 seconds. The backend checks Redis for a cached response (TTL configurable); on a cache miss it fetches from the Fingrid and ENTSO-E REST APIs, caches the result, and returns it. This keeps the external API call rate well within free-tier limits.
