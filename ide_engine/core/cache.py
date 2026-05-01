"""
Redis async cache singleton.

All cache operations use redis.asyncio (bundled in the redis package >= 4.2).
Keys are namespaced under ``ide-agent:``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_NAMESPACE: str = "ide-agent"
_cache_instance: "RedisCache | None" = None


def get_cache() -> "RedisCache":
    """Return the module-level singleton.  Creates it on first call."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


class RedisCache:
    """Thin async wrapper around redis.asyncio with namespaced keys and TTL helpers."""

    def __init__(self, url: str | None = None) -> None:
        redis_url = url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._client: aioredis.Redis = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis cache initialised: %s", redis_url.split("@")[-1])

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get(self, key: str) -> str | None:
        """Retrieve a string value, or None if absent / expired."""
        try:
            return await self._client.get(self._ns(key))
        except aioredis.RedisError as exc:
            logger.error("Cache GET failed for key '%s': %s", key, exc)
            return None

    async def set(self, key: str, value: str, ttl: int = 0) -> bool:
        """
        Store a string value.

        Args:
            key: Cache key (will be namespaced automatically).
            value: String value to store.
            ttl: Time-to-live in seconds; 0 means no expiry.
        """
        try:
            if ttl > 0:
                await self._client.setex(self._ns(key), ttl, value)
            else:
                await self._client.set(self._ns(key), value)
            return True
        except aioredis.RedisError as exc:
            logger.error("Cache SET failed for key '%s': %s", key, exc)
            return False

    async def delete(self, key: str) -> int:
        """Delete a key.  Returns number of keys deleted (0 or 1)."""
        try:
            return await self._client.delete(self._ns(key))
        except aioredis.RedisError as exc:
            logger.error("Cache DELETE failed for key '%s': %s", key, exc)
            return 0

    async def exists(self, key: str) -> bool:
        """Return True if the key exists in Redis."""
        try:
            result = await self._client.exists(self._ns(key))
            return bool(result)
        except aioredis.RedisError:
            return False

    async def ping(self) -> bool:
        """Health-check the Redis connection."""
        try:
            return await self._client.ping()
        except aioredis.RedisError:
            return False

    async def close(self) -> None:
        """Close the connection pool gracefully."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ns(key: str) -> str:
        """Add the global namespace prefix to avoid key collisions."""
        return f"{_NAMESPACE}:{key}"
