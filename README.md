# 🔌 Fingrid Energy Dashboard

A modern, real-time energy data dashboard for Finland using Fingrid Open Data API and Entso-E Transparency Platform.

[![CI/CD](https://github.com/aliipou/fingrid-dashboard/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/aliipou/fingrid-dashboard/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Redis (optional, for caching)
- API keys from [Fingrid](https://data.fingrid.fi/) and [Entso-E](https://transparency.entsoe.eu/)

### 1-Minute Setup
```bash
# Clone repository
git clone https://github.com/aliipou/fingrid-dashboard.git
cd fingrid-dashboard

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start with Docker (recommended)
docker-compose up --build

# OR start manually
./scripts/dev-start.sh