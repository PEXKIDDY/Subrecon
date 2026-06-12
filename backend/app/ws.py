"""WebSocket manager for real-time scan progress.

The Celery worker publishes progress events to Redis; the FastAPI process
subscribes and fans them out to connected browser clients. This decouples the
worker (no direct socket access) from the web tier.
"""
from __future__ import annotations

import asyncio
import json

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.config import settings

CHANNEL = "subreco:events"


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, set[WebSocket]] = {}  # scan_id -> sockets

    async def connect(self, scan_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(scan_id, set()).add(ws)

    def disconnect(self, scan_id: int, ws: WebSocket) -> None:
        if scan_id in self.active:
            self.active[scan_id].discard(ws)
            if not self.active[scan_id]:
                del self.active[scan_id]

    async def broadcast(self, scan_id: int, payload: dict) -> None:
        for ws in list(self.active.get(scan_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(scan_id, ws)

    async def redis_listener(self) -> None:
        """Background task: relay Redis pub/sub events to WebSocket clients."""
        redis = aioredis.from_url(settings.broker_url, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                event = json.loads(message["data"])
                await self.broadcast(int(event["scan_id"]), event)
            except Exception:
                continue


manager = ConnectionManager()


def publish_event(scan_id: int, stage: str, message: str, progress: int, **extra) -> None:
    """Synchronous publisher used by the Celery worker."""
    import redis as sync_redis

    client = sync_redis.from_url(settings.broker_url, decode_responses=True)
    payload = {"scan_id": scan_id, "stage": stage, "message": message, "progress": progress, **extra}
    try:
        client.publish(CHANNEL, json.dumps(payload))
    except Exception:
        pass
