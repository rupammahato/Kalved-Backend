from datetime import timedelta, datetime

from app.cache.cache_service import redis_cache


class PresenceService:
    ONLINE_KEY_PREFIX = "presence:user:"
    TTL_SECONDS = 60  # refresh every 60s

    @staticmethod
    async def set_online(user_id: int):
        key = f"{PresenceService.ONLINE_KEY_PREFIX}{user_id}"
        await redis_cache.set(key, "1", ttl=PresenceService.TTL_SECONDS)

    @staticmethod
    async def set_offline(user_id: int):
        key = f"{PresenceService.ONLINE_KEY_PREFIX}{user_id}"
        await redis_cache.delete(key)

    @staticmethod
    async def is_online(user_id: int) -> bool:
        key = f"{PresenceService.ONLINE_KEY_PREFIX}{user_id}"
        val = await redis_cache.get(key)
        return bool(val)
