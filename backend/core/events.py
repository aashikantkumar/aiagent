"""
Redis Pub/Sub event broadcaster.

This module decouples agent execution from WebSocket streaming.

Architecture:
  1. Agent worker publishes events to a Redis channel.
  2. WebSocket endpoint subscribes to that channel and relays to the frontend.
  3. If the user's browser disconnects, the agent keeps running.
     When the user reconnects, they can subscribe again and receive new events.
"""
import json
import asyncio
from typing import AsyncGenerator, Optional, Callable

import redis.asyncio as aioredis

from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

CHANNEL_PREFIX = "agent:events:"

# ── Async Redis singleton ───────────────────────────────────────────────

_async_redis: Optional[aioredis.Redis] = None


async def _get_async_redis() -> aioredis.Redis:
    """Lazy-init an async Redis connection."""
    global _async_redis
    if _async_redis is None:
        _async_redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _async_redis


# ── Publisher ───────────────────────────────────────────────────────────

async def publish_event(session_id: str, event: dict) -> None:
    """Publish an agent event to the session's Redis channel."""
    r = await _get_async_redis()
    channel = f"{CHANNEL_PREFIX}{session_id}"
    payload = json.dumps(event, default=str)
    await r.publish(channel, payload)


# ── Subscriber ──────────────────────────────────────────────────────────

async def subscribe_events(session_id: str) -> AsyncGenerator[dict, None]:
    """
    Subscribe to a session's event channel and yield events as they arrive.

    Usage in a WebSocket handler:
        async for event in subscribe_events(session_id):
            await ws.send_json(event)
    """
    r = await _get_async_redis()
    pubsub = r.pubsub()
    channel = f"{CHANNEL_PREFIX}{session_id}"

    await pubsub.subscribe(channel)
    logger.info("pubsub_subscribe", session_id=session_id, channel=channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield data
                except json.JSONDecodeError:
                    logger.warning("pubsub_bad_json", session_id=session_id)
                    continue
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info("pubsub_unsubscribe", session_id=session_id, channel=channel)
