# 🚀 Deployment Guide

This guide covers various deployment options for the Fingrid Energy Dashboard, from local development to production-ready deployments.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployments](#cloud-deployments)
- [Environment Configuration](#environment-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)

## ⚡ Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/aliipou/fingrid-dashboard.git
cd fingrid-dashboard

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Option 1: Docker (Recommended)
docker-compose up --build

# Option 2: Manual setup
./scripts/dev-start.sh
```

**Access Points**:
- 🌐 Frontend: http://localhost:3000
- 🔧 Backend API: http://localhost:8000
- 📚 API Docs: http://localhost:8000/api/docs
- 📊 Redis: localhost:6379

## 🐳 Docker Deployment

### Development with Docker

```bash
# Start development environment
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production with Docker

```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d --build

# Or use the deployment script
./scripts/deploy.sh
```

### Docker Configuration

**docker-compose.yml** (Development):
- Frontend with hot reload
- Backend with auto-restart
- Redis for caching
- Volume mounts for development

**docker-compose.prod.yml** (Production):
- Optimized builds
- Health checks
- Security headers
- Nginx reverse proxy
- SSL/TLS termination

## 🏭 Production Deployment

### Prerequisites

- **Server**: Linux (Ubuntu 20.04+ recommended)
- **RAM**: 2GB minimum, 4GB recommended
- **CPU**: 2 cores minimum
- **Storage**: 20GB minimum
- **Docker & Docker Compose** installed

### Step-by-Step Production Setup

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

#### 2. Application Deployment

```bash
# Clone repository
git clone https://github.com/aliipou/fingrid-dashboard.git
cd fingrid-dashboard

# Setup production environment
cp .env.example .env.production
nano .env.production  # Configure with production values

# Deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
```

#### 3. SSL/TLS Setup (Optional)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Production Environment Variables

Create `.env.production`:

```bash
# API Keys (REQUIRED)
FINGRID_API_KEY=your_production_fingrid_key
ENTSOE_API_KEY=your_production_entsoe_key

# Security
SECRET_KEY=your_256_bit_secret_key_here
REDIS_PASSWORD=strong_redis_password

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database & Cache
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
CACHE_TTL=300

# CORS (adjust for your domain)
CORS_ORIGINS=["https://your-domain.com"]

# Rate Limiting
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60

# Frontend
REACT_APP_API_URL=https://your-domain.com
```

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm (optional)

### Deployment Steps

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Or using individual files
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/redis-pvc.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/ingress.yaml
```

### Kubernetes Configuration Files

The following files need to be created in the `k8s/` directory:

**namespace.yaml**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fingrid-dashboard
```

**configmap.yaml**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fingrid-config
  namespace: fingrid-dashboard
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis:6379"
  CACHE_TTL: "300"
```

**secret.yaml**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: fingrid-secrets
  namespace: fingrid-dashboard
type: Opaque
stringData:
  FINGRID_API_KEY: "your_fingrid_api_key"
  ENTSOE_API_KEY: "your_entsoe_api_key"
  SECRET_KEY: "your_secret_key"
  REDIS_PASSWORD: "your_redis_password"
```

### Monitoring Kubernetes Deployment

```bash
# Check pod status
kubectl get pods -n fingrid-dashboard

# View logs
kubectl logs -f deployment/backend -n fingrid-dashboard

# Check services
kubectl get services -n fingrid-dashboard

# Port forward for testing
kubectl port-forward service/backend 8000:8000 -n fingrid-dashboard
```

## ☁️ Cloud Deployments

### AWS Deployment

#### Using AWS ECS

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

docker build -t fingrid-backend ./backend
docker tag fingrid-backend:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/fingrid-backend:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/fingrid-backend:latest

# Deploy using ECS CLI or Console
```

#### Using AWS EKS

```bash
# Create EKS cluster
eksctl create cluster --name fingrid-dashboard --version 1.21

# Deploy to EKS
kubectl apply -f k8s/
```

### Google Cloud Platform

#### Using Google Cloud Run

```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/PROJECT_ID/fingrid-backend ./backend
gcloud run deploy fingrid-backend --image gcr.io/PROJECT_ID/fingrid-backend --platform managed

# Build and deploy frontend
gcloud builds submit --tag gcr.io/PROJECT_ID/fingrid-frontend ./frontend
gcloud run deploy fingrid-frontend --image gcr.io/PROJECT_ID/fingrid-frontend --platform managed
```

#### Using GKE

```bash
# Create GKE cluster
gcloud container clusters create fingrid-dashboard --num-nodes=3

# Deploy to GKE
kubectl apply -f k8s/
```

### Microsoft Azure

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name fingrid-dashboard --location eastus

# Deploy container group
az container create --resource-group fingrid-dashboard --file azure-container-instances.yaml
```

### DigitalOcean

#### Using DigitalOcean App Platform

Create `.do/app.yaml`:

```yaml
name: fingrid-dashboard
services:
- name: backend
  source_dir: /backend
  dockerfile_path: Dockerfile
  http_port: 8000
  environment_slug: python
  envs:
  - key: FINGRID_API_KEY
    value: your_api_key
    type: SECRET
  
- name: frontend
  source_dir: /frontend
  dockerfile_path: Dockerfile
  http_port: 80
  environment_slug: node-js

databases:
- name: redis
  engine: REDIS
  version: "6"
```

## 🔧 Environment Configuration

### Environment Files

**Development (.env)**:
```bash
FINGRID_API_KEY=dev_key
ENTSOE_API_KEY=dev_key
DEBUG=true
LOG_LEVEL=DEBUG
REDIS_URL=redis://localhost:6379
```

**Production (.env.production)**:
```bash
FINGRID_API_KEY=prod_key
ENTSOE_API_KEY=prod_key
DEBUG=false
LOG_LEVEL=INFO
REDIS_URL=redis://:password@redis:6379
SECRET_KEY=production_secret_key
```

**Testing (.env.test)**:
```bash
FINGRID_API_KEY=test_key
ENTSOE_API_KEY=test_key
DEBUG=true
REDIS_URL=redis://localhost:6379/1
```

### Configuration Validation

```bash
# Check configuration
python -c "
from app.core.config import settings
print('Configuration valid!')
print(f'Fingrid API: {bool(settings.FINGRID_API_KEY)}')
print(f'ENTSO-E API: {bool(settings.ENTSOE_API_KEY)}')
"
```

## 📊 Monitoring & Logging

### Health Checks

```bash
# Application health
curl http://localhost:8000/api/v1/health

# Detailed health check
./scripts/health-check.sh
```

### Logging Configuration

**Production Logging**:
```python
# backend/app/core/logging.py
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "default",
            "class": "logging.FileHandler",
            "filename": "/var/log/fingrid-dashboard.log",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default", "file"],
    },
}
```

### Monitoring Setup

**Docker Compose Monitoring**:
```yaml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Log Aggregation

**ELK Stack**:
```yaml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.14.0
    environment:
      - discovery.type=single-node
    
  logstash:
    image: docker.elastic.co/logstash/logstash:7.14.0
    
  kibana:
    image: docker.elastic.co/kibana/kibana:7.14.0
    ports:
      - "5601:5601"
```

## 🔧 Troubleshooting

### Common Issues

#### 1. API Key Issues

**Problem**: API returns 401 Unauthorized

**Solution**:
```bash
# Check API key configuration
echo $FINGRID_API_KEY
echo $ENTSOE_API_KEY

# Test API key manually
curl -H "x-api-key: $FINGRID_API_KEY" "https://api.fingrid.fi/v1/variable/124/events/json?start_time=2025-05-26T00:00:00Z&end_time=2025-05-26T01:00:00Z"
```

#### 2. Redis Connection Issues

**Problem**: Cache service unavailable

**Solution**:
```bash
# Check Redis container
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

#### 3. CORS Issues

**Problem**: Frontend can't access API

**Solution**:
```bash
# Check CORS configuration in .env
CORS_ORIGINS=["http://localhost:3000", "https://your-domain.com"]

# Or temporarily allow all origins (NOT for production)
CORS_ORIGINS=["*"]
```

#### 4. Memory Issues

**Problem**: Application crashes due to memory

**Solution**:
```bash
# Monitor memory usage
docker stats

# Increase container memory limits
# In docker-compose.yml:
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

### Debugging Commands

```bash
# View application logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Execute commands in containers
docker-compose exec backend python -c "from app.main import app; print('Backend OK')"
docker-compose exec frontend npm list

# Check container health
docker-compose exec backend curl http://localhost:8000/api/v1/health

# Database debugging
docker-compose exec redis redis-cli
> KEYS *
> GET fingrid_consumption_realtime_*
```

### Performance Optimization

#### Backend Optimization

```python
# app/core/config.py
class Settings(BaseSettings):
    # Optimize for production
    WORKERS: int = 4  # Number of Uvicorn workers
    MAX_CONNECTIONS: int = 100
    CACHE_TTL: int = 300  # 5 minutes
    REDIS_POOL_SIZE: int = 20
```

#### Frontend Optimization

```json
// package.json
{
  "scripts": {
    "build": "react-scripts build && npm run optimize",
    "optimize": "npx webpack-bundle-analyzer build/static/js/*.js"
  }
}
```

### Security Checklist

- [ ] API keys stored securely (not in code)
- [ ] HTTPS enabled in production
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Security headers enabled
- [ ] Container images updated
- [ ] Secrets management in place
- [ ] Firewall rules configured
- [ ] Backup strategy implemented

### Backup and Recovery

```bash
# Backup Redis data
docker-compose exec redis redis-cli --rdb /data/backup.rdb

# Backup configuration
tar -czf backup_$(date +%Y%m%d).tar.gz .env* docker-compose*.yml k8s/

# Restore Redis data
docker-compose exec redis redis-cli --rdb /data/backup.rdb
docker-compose restart redis
```

---

## 📞 Support

For deployment issues:

1. **Check logs** first using the debugging commands above
2. **Review health checks** to identify failing components  
3. **Consult troubleshooting** section for common issues
4. **Create an issue** on GitHub with deployment details

**Useful Resources**:
- 📚 [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- 🐳 [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- ☸️ [Kubernetes Documentation](https://kubernetes.io/docs/)

---

*Last updated: May 26, 2025 | Version 1.0.0*