# 🔐 Environment Setup Guide

## 📋 Step-by-Step Setup

### 1. Create Environment File
```bash
# Copy the example file
cp .env.example .env

# Edit with your actual API keys
nano .env  # or use your preferred editor
```

### 2. Get Required API Keys

#### 🇫🇮 Fingrid API Key
1. Go to [Fingrid Open Data](https://data.fingrid.fi/)
2. Register for a free account
3. Navigate to API section
4. Generate your API key
5. Copy the key

#### 🇪🇺 ENTSO-E API Key  
1. Go to [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
2. Register for an account
3. Go to Account Settings > Web API
4. Generate Security Token
5. Copy the token

### 3. Configure .env File

Replace the placeholder values in your `.env` file:

```bash
# API Keys (REQUIRED - Get from respective platforms)
FINGRID_API_KEY=your_actual_fingrid_api_key_here
ENTSOE_API_KEY=your_actual_entsoe_api_key_here

# Database & Cache
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password_here
CACHE_TTL=300

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

### 4. Verify Configuration

```bash
# Test your API keys
curl -H "x-api-key: YOUR_FINGRID_KEY" \
  "https://api.fingrid.fi/v1/variable/124/events/json?start_time=2025-05-26T00:00:00Z&end_time=2025-05-26T01:00:00Z"

# Should return JSON data if key is valid
```

## 🚨 Important Security Notes

- **NEVER commit .env files to Git**
- **Use different keys for development/production**
- **Keep API keys secure and private**
- **Regenerate keys if compromised**

## 🐳 Docker Environment

For Docker deployment, create `.env.docker`:

```bash
# API Keys
FINGRID_API_KEY=your_fingrid_key
ENTSOE_API_KEY=your_entsoe_key

# Redis with Docker
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=secure_password_123

# Docker-specific settings
ENVIRONMENT=production
DEBUG=false
REACT_APP_API_URL=http://localhost:8000
```