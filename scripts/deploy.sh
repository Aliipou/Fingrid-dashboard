#!/bin/bash
# Production deployment script

set -e

echo "🚀 Starting production deployment..."

# Check prerequisites
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production file not found"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
    exit 1
fi

# Pull latest images
echo "📦 Pulling latest images..."
docker-compose -f docker-compose.prod.yml pull

# Deploy new version
echo "🔄 Deploying new version..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check
echo "🔍 Running health checks..."
./scripts/health-check.sh "https://energy-dashboard.example.com"

echo "✅ Production deployment completed successfully!"