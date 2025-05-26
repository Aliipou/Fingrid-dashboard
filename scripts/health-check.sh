#!/bin/bash
# Health check script for monitoring

API_URL=${1:-"http://localhost:8000"}

echo "🔍 Checking health of Fingrid Dashboard..."

# Check backend health
HEALTH_RESPONSE=$(curl -s "$API_URL/api/v1/health" 2>/dev/null)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ Backend: Healthy"
else
    echo "❌ Backend: Unhealthy"
    exit 1
fi

# Check if frontend is accessible
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000" 2>/dev/null)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ Frontend: Accessible"
else
    echo "❌ Frontend: Not accessible"
fi

# Check Redis connection
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Connected"
else
    echo "⚠️ Redis: Not connected (may be using remote Redis)"
fi

echo "🎉 Health check complete!"