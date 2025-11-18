from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.routes import fingrid, entsoe, analytics, export
from app.services.cache_service import cache_service
from app.middleware.monitoring import PerformanceMonitoringMiddleware
from app.middleware.rate_limiting import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Fingrid Dashboard API...")
    await cache_service.connect()
    yield
    logger.info("Shutting down Fingrid Dashboard API...")
    await cache_service.disconnect()

# Create FastAPI application
app = FastAPI(
    title="Fingrid Energy Dashboard API",
    description="Real-time Finnish energy data dashboard API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(fingrid.router, prefix="/api/v1/fingrid", tags=["Fingrid"])
app.include_router(entsoe.router, prefix="/api/v1/entsoe", tags=["Entso-E"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Export"])

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "fingrid-dashboard-api",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Fingrid Energy Dashboard API",
        "docs": "/api/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )