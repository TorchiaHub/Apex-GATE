from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import api_router
from app.auth.database import init_auth_db
from app.auth.router import router as auth_router
from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.limiter import limiter
from app.proxy.router import router as proxy_router
from app.scheduler import start_scheduler
from app.websocket import ws_status


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    await init_auth_db()

    async with AsyncSessionLocal() as session:
        from app.models.provider import Provider
        from app.seeds.providers import seed_default_models, seed_providers

        result = await session.execute(select(Provider).limit(1))
        if result.scalar_one_or_none() is None:
            await seed_providers(session)

        await seed_default_models(session)

    await start_scheduler()
    yield


app = FastAPI(title="APEX GATE", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Conversation-Id"],
    expose_headers=["X-Conversation-Id"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth_router)
app.include_router(api_router)
app.include_router(proxy_router)


@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket) -> None:
    await ws_status(websocket)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
