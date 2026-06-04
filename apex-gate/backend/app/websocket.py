from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.api_key import ApiKey
from app.models.exhaustion_state import ExhaustionState
from app.models.provider import Provider

_WS_CLOSE_UNAUTHORIZED = 4001


async def ws_status(websocket: WebSocket) -> None:
    # --- Authentication via query param token ---
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(code=_WS_CLOSE_UNAUTHORIZED)
        return
    try:
        from app.auth.service import verify_access_token

        payload = await verify_access_token(token)
        if not payload.get("sub"):
            await websocket.accept()
            await websocket.close(code=_WS_CLOSE_UNAUTHORIZED)
            return
    except Exception:
        await websocket.accept()
        await websocket.close(code=_WS_CLOSE_UNAUTHORIZED)
        return
    # --- end authentication ---

    await websocket.accept()
    try:
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    now = datetime.now(timezone.utc)
                    result = await db.execute(
                        select(Provider, ApiKey, ExhaustionState)
                        .join(ApiKey, ApiKey.provider_id == Provider.id, isouter=True)
                        .join(ExhaustionState, ExhaustionState.api_key_id == ApiKey.id, isouter=True)
                        .where(Provider.is_active == True)  # noqa: E712
                        .order_by(Provider.sort_order)
                    )

                    provider_map: dict[str, dict] = {}
                    for prov, ak, ex in result.all():
                        slug = prov.slug
                        if slug not in provider_map:
                            provider_map[slug] = {
                                "provider": prov.name,
                                "slug": slug,
                                "total_keys": 0,
                                "active_keys": 0,
                                "exhausted_keys": 0,
                                "disabled_keys": 0,
                            }
                        if ak is None:
                            continue
                        provider_map[slug]["total_keys"] += 1
                        if not ak.is_enabled:
                            provider_map[slug]["disabled_keys"] += 1
                        elif ex and ex.exhausted_until and ex.exhausted_until > now:
                            provider_map[slug]["exhausted_keys"] += 1
                        else:
                            provider_map[slug]["active_keys"] += 1

                    payload = {
                        "ts": now.isoformat(),
                        "providers": list(provider_map.values()),
                    }
                    await websocket.send_text(json.dumps(payload))
            except Exception:
                pass  # transient DB error — retry next cycle
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
