# 🔌 Fingrid Energy Dashboard

<div align="center">

**Real-time Finnish Energy Data Monitoring & Analytics Platform**

[![CI/CD Pipeline](https://github.com/aliipou/fingrid-dashboard/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/aliipou/fingrid-dashboard/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 16+](https://img.shields.io/badge/node-%3E%3D16.0.0-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg?style=flat&logo=React)](https://reactjs.org/)

[🚀 Demo](https://energy-dashboard.example.com) • [📖 Documentation](./docs/API.md) • [🐛 Report Bug](https://github.com/aliipou/fingrid-dashboard/issues) • [✨ Request Feature](https://github.com/aliipou/fingrid-dashboard/issues)

</div>

---

## 🎯 **Overview**

A modern, real-time energy dashboard that visualizes Finnish electricity data from **Fingrid Open Data API** and **ENTSO-E Transparency Platform**. Built with professional-grade architecture featuring microservices, caching, analytics, and production-ready deployment.

### ✨ **Key Features**

🔋 **Real-time Energy Data**
- Electricity consumption monitoring  
- Production data from all sources
- Wind power generation tracking
- 24-hour consumption forecasts

💰 **Electricity Price Analytics**  
- Today's & tomorrow's spot prices
- Historical price trends
- Price statistics & insights

📊 **Advanced Analytics**
- Production vs consumption differential analysis
- Anomaly detection using statistical methods
- Forecast accuracy analysis
- Energy efficiency metrics
- Trend analysis with multiple time periods

📤 **Data Export**
- Multiple formats: CSV, JSON, Excel, XML
- Scheduled exports
- API endpoints for integration

🏗️ **Professional Architecture**
- FastAPI backend with async/await
- React frontend with TypeScript
- Redis caching layer
- Rate limiting & monitoring
- Docker containerization
- Kubernetes ready

---

## 🏃‍♂️ **Quick Start**

### **Option 1: Docker (Recommended)**

```bash
# 1. Clone repository
git clone https://github.com/aliipou/fingrid-dashboard.git
cd fingrid-dashboard

# 2. Setup environment
cp .env.example .env
# Edit .env with your API keys (see Environment Setup below)

# 3. Start with Docker
docker-compose up --build

# 4. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

### **Option 2: Manual Setup**

```bash
# 1. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Frontend setup
cd ../frontend
npm install

# 3. Start development servers
./scripts/dev-start.sh
```

---

## 🔐 **Environment Setup**

### **Get API Keys**

1. **Fingrid API Key** (Free)
   - Visit [Fingrid Open Data](https://data.fingrid.fi/)
   - Register & generate API key

2. **ENTSO-E API Key** (Free)  
   - Visit [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
   - Register & generate security token

### **Configure Environment**

```bash
# Copy example file
cp .env.example .env

# Edit with your keys
FINGRID_API_KEY=your_fingrid_api_key_here
ENTSOE_API_KEY=your_entsoe_api_key_here
```

**Complete `.env` configuration:**
```bash
# API Keys (REQUIRED)
FINGRID_API_KEY=your_fingrid_api_key_here
ENTSOE_API_KEY=your_entsoe_api_key_here

# Database & Cache
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password
CACHE_TTL=300

# Application
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development

# Security & CORS
CORS_ORIGINS=["http://localhost:3000"]
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

---

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React App     │    │   FastAPI       │    │   External      │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   APIs          │
│                 │    │                 │    │                 │
│ • TypeScript    │    │ • Async/Await   │    │ • Fingrid       │
│ • Recharts      │    │ • Pydantic      │    │ • ENTSO-E       │
│ • Modern CSS    │    │ • Type Hints    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┼─────────────────────────────────
                                 │
                    ┌─────────────────┐    ┌─────────────────┐
                    │     Redis       │    │    Monitoring   │
                    │   (Caching)     │    │   & Logging     │
                    │                 │    │                 │
                    │ • Session Store │    │ • Health Checks │
                    │ • Rate Limiting │    │ • Metrics       │
                    │ • Data Cache    │    │ • Error Tracking│
                    └─────────────────┘    └─────────────────┘
```

### **Technology Stack**

**Backend:**
- **FastAPI** - Modern, high-performance Python web framework
- **httpx** - Async HTTP client for external API calls
- **Redis** - In-memory caching and rate limiting
- **Pydantic** - Data validation and serialization
- **Pandas/NumPy** - Advanced data processing and analytics

**Frontend:**
- **React 18** with TypeScript - Modern UI framework
- **Recharts** - Professional data visualization
- **Modern CSS** - Responsive design with glassmorphism effects

**Infrastructure:**
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy and static file serving
- **Kubernetes** - Container orchestration (production)

---

## 📊 **Screenshots**

<div align="center">

### **Main Dashboard**
![Dashboard Overview](./docs/images/dashboard-overview.png)

### **Real-time Charts**  
![Charts](./docs/images/realtime-charts.png)

### **Analytics Dashboard**
![Analytics](./docs/images/analytics-dashboard.png)

</div>

---

## 🚀 **Features Deep Dive**

### **Real-time Data Monitoring**
- **Consumption Tracking**: Live electricity consumption across Finland
- **Production Monitoring**: Total electricity production from all sources  
- **Wind Power Focus**: Dedicated wind energy production tracking
- **Forecast Accuracy**: Compare predictions vs actual consumption

### **Advanced Analytics**
- **Differential Analysis**: Production vs consumption balance tracking
- **Anomaly Detection**: Statistical outlier identification
- **Trend Analysis**: Historical data patterns and forecasting
- **Efficiency Metrics**: Energy system performance indicators

### **Price Intelligence**
- **Spot Prices**: Real-time electricity market prices
- **Price Forecasting**: Tomorrow's day-ahead market prices
- **Historical Analysis**: Price trends and statistical insights
- **Market Indicators**: Peak hours, price volatility metrics

### **Data Export & Integration**
- **Multiple Formats**: CSV, JSON, Excel, XML export options
- **API Access**: RESTful endpoints for system integration
- **Scheduled Exports**: Automated data delivery
- **Custom Queries**: Flexible data filtering and selection

---

## 🔧 **API Documentation**

### **Core Endpoints**

```bash
# Health Check
GET /api/v1/health

# Real-time Data
GET /api/v1/fingrid/consumption/realtime
GET /api/v1/fingrid/production/realtime  
GET /api/v1/fingrid/wind/realtime
GET /api/v1/fingrid/consumption/forecast

# Price Data
GET /api/v1/entsoe/prices/today
GET /api/v1/entsoe/prices/tomorrow

# Analytics
GET /api/v1/analytics/efficiency
GET /api/v1/analytics/anomalies
GET /api/v1/analytics/forecast-accuracy

# Data Export
GET /api/v1/export/fingrid/{dataset_type}
```

**📖 Complete API Documentation**: [docs/API.md](./docs/API.md)

**🔍 Interactive API Explorer**: http://localhost:8000/api/docs

---

## 🐳 **Deployment Options**

### **Development**
```bash
docker-compose up --build
```

### **Production**
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### **Kubernetes**
```bash
kubectl apply -f k8s/
```

### **Cloud Platforms**
- **AWS ECS/EKS** - Amazon Web Services
- **Google Cloud Run/GKE** - Google Cloud Platform  
- **Azure Container Instances** - Microsoft Azure
- **DigitalOcean App Platform** - DigitalOcean

**📖 Detailed Deployment Guide**: [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)

---

## 🧪 **Testing**

```bash
# Run all tests
make test

# Backend tests with coverage
cd backend && pytest --cov=app --cov-report=html

# Frontend tests
cd frontend && npm test -- --coverage

# Linting
make lint

# Code formatting
make format
```

**Test Coverage**: 85%+ maintained across backend and frontend

---

## 📈 **Performance & Monitoring**

### **Performance Features**
- **Redis Caching**: 300-second TTL for real-time data
- **Rate Limiting**: 100 requests/minute per IP
- **Connection Pooling**: Optimized database connections
- **Async Processing**: Non-blocking I/O throughout

### **Monitoring & Observability**
- **Health Checks**: Comprehensive service monitoring
- **Performance Metrics**: Response time tracking
- **Error Logging**: Structured logging with correlation IDs
- **Real-time Dashboards**: System performance visualization

### **Scalability**
- **Horizontal Scaling**: Kubernetes pod autoscaling
- **Load Balancing**: Nginx reverse proxy
- **Database Optimization**: Redis clustering support
- **CDN Ready**: Static asset optimization

---

## 🤝 **Contributing**

We welcome contributions! Please see our [Contributing Guide](./docs/CONTRIBUTING.md) for details.

### **Quick Contributing Steps**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Development Setup**
```bash
# Install development dependencies
make install-dev

# Setup pre-commit hooks
pre-commit install

# Run development server
make dev-start
```

---

## 📝 **License**

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **[Fingrid Oyj](https://www.fingrid.fi/)** - For providing excellent open data APIs
- **[ENTSO-E](https://www.entsoe.eu/)** - For transparent electricity market data
- **Open Source Community** - For the amazing tools and libraries used

---

## 📞 **Support & Contact**

- **📖 Documentation**: [API Docs](./docs/API.md) | [Deployment Guide](./docs/DEPLOYMENT.md)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/aliipou/fingrid-dashboard/issues)
- **💡 Feature Requests**: [GitHub Issues](https://github.com/aliipou/fingrid-dashboard/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/aliipou/fingrid-dashboard/discussions)

---

## 📊 **Project Stats**

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/aliipou/fingrid-dashboard?style=social)
![GitHub forks](https://img.shields.io/github/forks/aliipou/fingrid-dashboard?style=social)
![GitHub issues](https://img.shields.io/github/issues/aliipou/fingrid-dashboard)
![GitHub pull requests](https://img.shields.io/github/issues-pr/aliipou/fingrid-dashboard)

**Built with ❤️ for sustainable energy monitoring**

</div>

---

<div align="center">

### **⭐ Star this project if it helped you!**

</div>
