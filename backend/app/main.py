"""SUBRECO FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, auth, export, intel, scans
from app.config import settings
from app.database import init_db
from app.ws import manager


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap tables in dev; production should run Alembic migrations.
    if settings.ENVIRONMENT == "development":
        with contextlib.suppress(Exception):
            init_db()
    listener = asyncio.create_task(manager.redis_listener())
    yield
    listener.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await listener


app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=PREFIX)
app.include_router(scans.router, prefix=PREFIX)
app.include_router(assets.router, prefix=PREFIX)
app.include_router(intel.router, prefix=PREFIX)
app.include_router(export.router, prefix=PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.websocket("/ws/scans/{scan_id}")
async def scan_ws(websocket: WebSocket, scan_id: int):
    await manager.connect(scan_id, websocket)
    try:
        while True:
            # Keep the connection open; client doesn't need to send anything.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(scan_id, websocket)
    except Exception:
        manager.disconnect(scan_id, websocket)
