import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional
import logging
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Async Redis cache service"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.default_ttl = settings.CACHE_TTL
        self.key_prefix = "fingrid_dashboard:"

    async def connect(self):
        """Connect to Redis"""
        try:
            # Use URL with password if configured
            redis_url = settings.get_redis_url_with_password()

            self.redis = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            await self.redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {str(e)}")
            self.redis = None

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key"""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None

        try:
            prefixed_key = self._make_key(key)
            value = await self.redis.get(prefixed_key)

            if value is not None:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss for key: {key}")
                return None

        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        if not self.redis:
            return False

        try:
            prefixed_key = self._make_key(key)
            json_value = json.dumps(value, default=str)

            ttl = ttl or self.default_ttl

            await self.redis.setex(prefixed_key, ttl, json_value)
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis:
            return False

        try:
            prefixed_key = self._make_key(key)
            result = await self.redis.delete(prefixed_key)
            logger.debug(f"Deleted cache key: {key}")
            return bool(result)

        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis:
            return False

        try:
            prefixed_key = self._make_key(key)
            result = await self.redis.exists(prefixed_key)
            return bool(result)

        except Exception as e:
            logger.error(f"Error checking cache existence: {str(e)}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis:
            return 0

        try:
            prefixed_pattern = self._make_key(pattern)
            keys = await self.redis.keys(prefixed_pattern)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Cleared {deleted} cache keys matching pattern: {pattern}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Error clearing cache pattern: {str(e)}")
            return 0

    async def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.redis:
            return {"status": "disconnected"}

        try:
            info = await self.redis.info()

            # Get keys count for our prefix
            keys = await self.redis.keys(f"{self.key_prefix}*")

            return {
                "status": "connected",
                "total_keys": len(keys),
                "redis_version": info.get("redis_version", "unknown"),
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> dict:
        """Perform health check on cache service"""
        try:
            if not self.redis:
                return {"healthy": False, "error": "Not connected to Redis"}

            # Test basic operations
            test_key = "health_check_test"
            test_value = {"timestamp": str(datetime.utcnow()), "test": True}

            # Test set
            await self.set(test_key, test_value, ttl=10)

            # Test get
            retrieved = await self.get(test_key)

            # Test delete
            await self.delete(test_key)

            if retrieved and retrieved.get("test") is True:
                return {"healthy": True, "message": "All cache operations working"}
            else:
                return {"healthy": False, "error": "Cache operations failed"}

        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return {"healthy": False, "error": str(e)}

# Global cache service instance
cache_service = CacheService()