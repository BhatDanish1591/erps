from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


async def check_redis_connection() -> bool:
    """Health-check: verify Redis is reachable."""
    try:
        client = get_redis_client()
        await client.ping()
        return True
    except Exception as exc:
        logger.error("Redis connection failed", error=str(exc))
        return False


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
