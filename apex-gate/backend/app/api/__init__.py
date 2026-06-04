"""REST API routers for APEX GATE."""

from fastapi import APIRouter

from app.api import (
    admin,
    conversations,
    keys,
    logs,
    models_api,
    providers,
    stats,
    virtual_keys,
)

api_router = APIRouter()
api_router.include_router(keys.router)
api_router.include_router(virtual_keys.router)
api_router.include_router(providers.router)
api_router.include_router(models_api.router)
api_router.include_router(logs.router)
api_router.include_router(stats.router)
api_router.include_router(admin.router)
api_router.include_router(conversations.router)

__all__ = ["api_router"]
