from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import sha256_hash
from app.database import get_session
from app.models.virtual_key import VirtualKey
from app.proxy.manager import proxy_manager
from app.proxy import memory as memory_service
from app.proxy.protocols import format_response, normalize_request

router = APIRouter(tags=["proxy"])


async def _resolve_virtual_key(authorization: str | None, db: AsyncSession) -> VirtualKey:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization.removeprefix("Bearer ").strip()
    key_hash = sha256_hash(token)
    vk = await db.scalar(
        select(VirtualKey).where(
            VirtualKey.key_hash == key_hash,
            VirtualKey.is_enabled == True,  # noqa: E712
        )
    )
    if not vk:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled virtual key",
        )
    return vk


async def _stream_chunks(chunks: object) -> AsyncGenerator[str, None]:
    async for chunk in chunks:  # type: ignore[attr-defined]
        if hasattr(chunk, "model_dump"):
            data = json.dumps(chunk.model_dump())
        else:
            data = json.dumps(chunk)
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/v1/chat/completions", response_model=None)
@router.post("/openai/v1/chat/completions", response_model=None)
async def openai_chat_completions(
    request: Request,
    authorization: str | None = Header(default=None),
    x_conversation_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse | JSONResponse:
    vk = await _resolve_virtual_key(authorization, db)

    if await proxy_manager.is_budget_exceeded(vk, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "budget_exceeded", "message": "Daily token budget exceeded"},
        )

    body = await request.json()
    normalized = normalize_request(body, "openai")
    messages: list[dict] = normalized.get("messages", [])
    stream: bool = bool(body.get("stream", False))
    model: str = str(body.get("model", "auto"))
    if model == "auto" and vk.model_preference:
        model = vk.model_preference

    decision = memory_service.resolve(vk, x_conversation_id)
    result, actual_model, conversation_id = await proxy_manager.call_with_router(
        messages=messages,
        virtual_key=vk,
        model_request=model,
        db=db,
        protocol="openai",
        conversation_id=decision.conversation_id,
        memory_active=decision.active,
        stream=stream,
    )

    if stream:
        stream_headers = {"X-Virtual-Key": vk.key_prefix}
        if conversation_id:
            stream_headers["X-Conversation-Id"] = conversation_id
        return StreamingResponse(
            _stream_chunks(result),
            media_type="text/event-stream",
            headers=stream_headers,
        )

    provider_slug = actual_model.split("/")[0] if "/" in actual_model else "unknown"
    headers = {
        "X-Model-Used": actual_model,
        "X-Provider-Used": provider_slug,
        "X-Virtual-Key": vk.key_prefix,
    }
    if conversation_id:
        headers["X-Conversation-Id"] = conversation_id
    return JSONResponse(
        content=format_response(result, "openai"),
        headers=headers,
    )


@router.post("/anthropic/v1/messages", response_model=None)
async def anthropic_messages(
    request: Request,
    authorization: str | None = Header(default=None),
    x_conversation_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    vk = await _resolve_virtual_key(authorization, db)

    if await proxy_manager.is_budget_exceeded(vk, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "budget_exceeded", "message": "Daily token budget exceeded"},
        )

    body = await request.json()
    if body.get("stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "streaming_unsupported",
                "message": "Streaming is not supported on the Anthropic-compatible endpoint",
            },
        )
    model: str = str(body.get("model", "auto"))
    if model == "auto" and vk.model_preference:
        model = vk.model_preference
    normalized = normalize_request(body, "anthropic")
    messages: list[dict] = normalized.get("messages", [])

    decision = memory_service.resolve(vk, x_conversation_id)
    result, actual_model, conversation_id = await proxy_manager.call_with_router(
        messages=messages,
        virtual_key=vk,
        model_request=model,
        db=db,
        protocol="anthropic",
        conversation_id=decision.conversation_id,
        memory_active=decision.active,
    )

    provider_slug = actual_model.split("/")[0] if "/" in actual_model else "unknown"
    headers = {
        "X-Model-Used": actual_model,
        "X-Provider-Used": provider_slug,
        "X-Virtual-Key": vk.key_prefix,
    }
    if conversation_id:
        headers["X-Conversation-Id"] = conversation_id
    return JSONResponse(
        content=format_response(result, "anthropic"),
        headers=headers,
    )


@router.post("/gemini/v1/generateContent", response_model=None)
async def gemini_generate_content(
    request: Request,
    authorization: str | None = Header(default=None),
    x_conversation_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    vk = await _resolve_virtual_key(authorization, db)

    if await proxy_manager.is_budget_exceeded(vk, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "budget_exceeded", "message": "Daily token budget exceeded"},
        )

    body = await request.json()
    if body.get("stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "streaming_unsupported",
                "message": "Streaming is not supported on the Gemini-compatible endpoint",
            },
        )
    model: str = str(body.get("model", "auto"))
    if model == "auto" and vk.model_preference:
        model = vk.model_preference
    normalized = normalize_request(body, "gemini")
    messages: list[dict] = normalized.get("messages", [])

    decision = memory_service.resolve(vk, x_conversation_id)
    result, actual_model, conversation_id = await proxy_manager.call_with_router(
        messages=messages,
        virtual_key=vk,
        model_request=model,
        db=db,
        protocol="gemini",
        conversation_id=decision.conversation_id,
        memory_active=decision.active,
    )

    provider_slug = actual_model.split("/")[0] if "/" in actual_model else "unknown"
    headers = {
        "X-Model-Used": actual_model,
        "X-Provider-Used": provider_slug,
        "X-Virtual-Key": vk.key_prefix,
    }
    if conversation_id:
        headers["X-Conversation-Id"] = conversation_id
    return JSONResponse(
        content=format_response(result, "gemini"),
        headers=headers,
    )


@router.post("/ollama/api/chat", response_model=None)
@router.post("/api/chat", response_model=None)
async def ollama_chat(
    request: Request,
    authorization: str | None = Header(default=None),
    x_conversation_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    vk = await _resolve_virtual_key(authorization, db)

    if await proxy_manager.is_budget_exceeded(vk, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "budget_exceeded", "message": "Daily token budget exceeded"},
        )

    body = await request.json()
    if body.get("stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "streaming_unsupported",
                "message": "Streaming is not supported on the Ollama-compatible endpoint; set stream=false",
            },
        )
    model: str = str(body.get("model", "auto"))
    if model == "auto" and vk.model_preference:
        model = vk.model_preference
    normalized = normalize_request(body, "ollama")
    messages: list[dict] = normalized.get("messages", [])

    decision = memory_service.resolve(vk, x_conversation_id)
    result, actual_model, conversation_id = await proxy_manager.call_with_router(
        messages=messages,
        virtual_key=vk,
        model_request=model,
        db=db,
        protocol="ollama",
        conversation_id=decision.conversation_id,
        memory_active=decision.active,
    )

    provider_slug = actual_model.split("/")[0] if "/" in actual_model else "unknown"
    headers = {
        "X-Model-Used": actual_model,
        "X-Provider-Used": provider_slug,
        "X-Virtual-Key": vk.key_prefix,
    }
    if conversation_id:
        headers["X-Conversation-Id"] = conversation_id
    return JSONResponse(
        content=format_response(result, "ollama"),
        headers=headers,
    )


@router.get("/v1/models", response_model=None)
async def list_proxy_models(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> dict:
    vk = await _resolve_virtual_key(authorization, db)
    models = await proxy_manager.get_available_models(user_id=vk.user_id, db=db)
    return {
        "object": "list",
        "data": [
            {"id": m["model_id"], "object": "model", "owned_by": m["provider_slug"]}
            for m in models
        ],
    }
