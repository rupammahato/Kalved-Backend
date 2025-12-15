from typing import Optional, Any
import logging
from redis import asyncio as aioredis
from app.core.config import settings
import json

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        if not self.redis:
            try:
                self.redis = aioredis.from_url(
                    self.redis_url, 
                    encoding="utf-8", 
                    decode_responses=True
                )
                logger.info("Connected to Redis cache.")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")

    async def get(self, key: str) -> Optional[str]:
        if not self.redis:
            await self.connect()
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        if not self.redis:
            await self.connect()
        try:
            # If value is dict/list, json dump it? 
            # The caller usually handles serialization based on my snippet earlier, 
            # but standardizing here is okay. 
            # However, looking at AppointmentService.get_available_slots, 
            # it expects `await redis_cache.get(cache_key)` to return the string JSON, 
            # and it does `json.loads(cached)`. 
            # So `set` should take a string or I make sure caller passes string.
            # AppointmentService passes "1" or json.dumps(result). So it passes string.
            await self.redis.set(key, value, ex=ttl)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")

    async def delete_pattern(self, pattern: str):
        if not self.redis:
            await self.connect()
        try:
            # This is expensive in production used heavily, but okay for MVP/appointment windows
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete_pattern error for {pattern}: {e}")

    async def close(self):
        if self.redis:
            await self.redis.close()

# Singleton instance
redis_cache = RedisCache()
