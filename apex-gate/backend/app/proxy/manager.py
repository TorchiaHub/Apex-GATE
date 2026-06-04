from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import litellm
from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt_key
from app.models.api_key import ApiKey
from app.models.exhaustion_state import ExhaustionState
from app.models.model_catalog import ModelCatalog
from app.models.provider import Provider
from app.models.request_log import RequestLog
from app.models.virtual_key import VirtualKey
from app.models.virtual_key_assignment import VirtualKeyAssignment
from app.models.conversation import Conversation
from app.proxy import memory as memory_service

litellm.drop_params = True

logger = logging.getLogger(__name__)

# Default cooldown applied to a key when a provider returns a rate-limit error.
_RATE_LIMIT_BACKOFF_SECONDS = 60


class ProxyManager:
    async def call_with_router(
        self,
        messages: list[dict],
        virtual_key: VirtualKey,
        model_request: str,
        db: AsyncSession,
        protocol: str = "openai",
        conversation_id: str | None = None,
        memory_active: bool = False,
        **extra_kwargs,
    ) -> tuple[dict | object, str, str | None]:
        """
        Main proxy method. Builds a priority-ordered list of candidate keys for
        the virtual key and tries them sequentially, failing over to the next
        candidate on rate-limit / provider errors.

        For non-streaming requests returns
        (response_dict, actual_litellm_model_string, conversation_id).
        For streaming requests (stream=True in extra_kwargs) returns
        (async_generator, "streaming", conversation_id) — the caller iterates the
        generator.

        When ``memory_active`` is set and a ``conversation_id`` is provided, prior
        history is loaded from the DB and prepended to ``messages`` before the
        call, and the new turn is persisted afterwards. ``conversation_id`` is
        echoed back so the caller can return it to the client.
        """
        now = datetime.now(timezone.utc)
        is_stream = bool(extra_kwargs.get("stream", False))
        # Ask providers to include token usage in the final stream chunk.
        # litellm.drop_params drops this for providers that don't support it.
        if is_stream and "stream_options" not in extra_kwargs:
            extra_kwargs["stream_options"] = {"include_usage": True}

        # 0. Conversation memory: reconstruct prior history (option a). The client
        # only sends the latest turn; we prepend stored history before calling.
        incoming_messages = messages
        conversation = None
        if memory_active and conversation_id:
            try:
                messages, conversation = await memory_service.prepare_messages(
                    db, virtual_key, conversation_id, incoming_messages
                )
            except PermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "conversation_forbidden", "message": str(exc)},
                )

        # 1. Load VirtualKeyAssignment for virtual_key.id, sorted by priority ASC
        assignments_result = await db.execute(
            select(VirtualKeyAssignment)
            .where(VirtualKeyAssignment.vk_id == virtual_key.id)
            .order_by(VirtualKeyAssignment.priority.asc())
        )
        assignments = assignments_result.scalars().all()

        allowed_slugs: list[str] | None = None
        if virtual_key.allowed_providers:
            allowed_slugs = [
                s.strip() for s in virtual_key.allowed_providers.split(",") if s.strip()
            ]

        # 2. Build the ordered list of viable candidates (priority ASC).
        candidates: list[dict] = []
        for assignment in assignments:
            api_key = await db.get(ApiKey, assignment.api_key_id)
            if api_key is None or not api_key.is_enabled:
                continue

            # Skip keys with an active exhaustion window.
            exhaustion = await db.scalar(
                select(ExhaustionState)
                .where(ExhaustionState.api_key_id == api_key.id)
                .where(ExhaustionState.exhausted_until > now)
            )
            if exhaustion is not None:
                continue

            provider = await db.get(Provider, api_key.provider_id)
            if provider is None:
                continue

            # Skip if the virtual key restricts to specific providers.
            if allowed_slugs is not None and provider.slug not in allowed_slugs:
                continue

            # Resolve the model: AUTO -> provider default, otherwise by name.
            if model_request == "auto":
                model_entry = await self._get_default_model(provider.id, db)
            else:
                model_entry = await self._get_model_by_name(provider.id, model_request, db)
            if model_entry is None:
                continue

            try:
                plaintext_key = decrypt_key(api_key.key_encrypted)
            except Exception:
                continue

            litellm_model_str = f"{provider.litellm_prefix or ''}{model_entry.model_id}"
            params: dict = {"model": litellm_model_str, "api_key": plaintext_key}
            if provider.api_base_url:
                params["api_base"] = provider.api_base_url

            candidates.append({
                "api_key_id": api_key.id,
                "litellm_model_str": litellm_model_str,
                "params": params,
            })

        # 3. No viable providers found
        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "all_providers_exhausted",
                    "message": "No available providers or models for this request",
                },
            )

        # 4. Sequential priority-ordered fallback.
        last_error_code = "all_providers_failed"
        for candidate in candidates:
            start = datetime.now(timezone.utc)
            try:
                response = await litellm.acompletion(
                    messages=messages,
                    **candidate["params"],
                    **extra_kwargs,
                )
            except litellm.exceptions.RateLimitError:
                # Cool the key down so it is skipped until the window expires.
                await self.mark_exhausted(
                    candidate["api_key_id"], "rate_limit", _RATE_LIMIT_BACKOFF_SECONDS, db
                )
                last_error_code = "all_providers_exhausted"
                continue
            except litellm.exceptions.AuthenticationError:
                # The token is invalid — disable just this key and try the next.
                ak = await db.get(ApiKey, candidate["api_key_id"])
                if ak is not None:
                    ak.is_enabled = False
                    await db.commit()
                last_error_code = "authentication_error"
                continue
            except Exception:
                logger.exception(
                    "Provider call failed (key=%s model=%s)",
                    candidate["api_key_id"],
                    candidate["litellm_model_str"],
                )
                last_error_code = "all_providers_failed"
                continue

            # Streaming: log via a generator that owns its own DB session, because
            # the request-scoped session is closed once StreamingResponse returns.
            if is_stream:
                return (
                    self._logged_stream(
                        response,
                        virtual_key,
                        candidate["api_key_id"],
                        candidate["litellm_model_str"],
                        start,
                        protocol,
                        conversation,
                        incoming_messages,
                    ),
                    "streaming",
                    conversation_id if memory_active else None,
                )

            latency_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            actual_model: str = (
                (getattr(response, "_hidden_params", {}) or {}).get("model")
                or getattr(response, "model", None)
                or candidate["litellm_model_str"]
            )
            usage = getattr(response, "usage", None)
            input_tokens: int = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens: int = getattr(usage, "completion_tokens", 0) or 0
            try:
                cost: float = litellm.completion_cost(completion_response=response)
            except Exception:
                cost = 0.0

            db.add(RequestLog(
                user_id=virtual_key.user_id,
                virtual_key_id=virtual_key.id,
                api_key_id=candidate["api_key_id"],
                model_id=actual_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                status="success",
                protocol=protocol,
            ))
            await db.commit()

            response_dict: dict = (
                response.model_dump() if hasattr(response, "model_dump") else dict(response)
            )

            # Persist the turn after a successful non-streaming call.
            if conversation is not None:
                assistant_content = self._extract_assistant_content(response_dict)
                try:
                    await memory_service.persist_turn(
                        db, virtual_key, conversation, incoming_messages, assistant_content
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist conversation turn (conversation=%s)",
                        conversation.id,
                    )

            return response_dict, actual_model, conversation_id if memory_active else None

        # 5. Every candidate failed or is exhausted.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": last_error_code,
                "message": "All configured providers failed or are exhausted",
            },
        )

    async def _logged_stream(
        self,
        response: object,
        virtual_key: VirtualKey,
        api_key_id: str,
        litellm_model_str: str,
        start: datetime,
        protocol: str,
        conversation: Conversation | None = None,
        incoming_messages: list[dict] | None = None,
    ):
        """Wrap a litellm streaming generator, logging usage at stream end.

        Uses a fresh DB session because the request-scoped session has already
        been closed by the time the StreamingResponse iterates this generator.
        When a conversation is provided, the assistant reply is accumulated from
        the stream and persisted once the stream completes.
        """
        from app.database import AsyncSessionLocal

        actual_model = litellm_model_str
        input_tokens = 0
        output_tokens = 0
        assistant_parts: list[str] = []
        try:
            async for chunk in response:  # type: ignore[attr-defined]
                chunk_model: str | None = getattr(chunk, "model", None)
                if chunk_model:
                    actual_model = chunk_model
                usage = getattr(chunk, "usage", None)
                if usage:
                    input_tokens = getattr(usage, "prompt_tokens", input_tokens) or input_tokens
                    output_tokens = getattr(usage, "completion_tokens", output_tokens) or output_tokens
                if conversation is not None:
                    delta = self._extract_stream_delta(chunk)
                    if delta:
                        assistant_parts.append(delta)
                yield chunk
        finally:
            latency_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            try:
                async with AsyncSessionLocal() as log_db:
                    log_db.add(RequestLog(
                        user_id=virtual_key.user_id,
                        virtual_key_id=virtual_key.id,
                        api_key_id=api_key_id,
                        model_id=actual_model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=0.0,
                        latency_ms=latency_ms,
                        status="success",
                        protocol=protocol,
                    ))
                    await log_db.commit()
            except Exception:
                logger.exception("Failed to log streaming request for virtual_key=%s", virtual_key.id)

            if conversation is not None and incoming_messages is not None:
                try:
                    async with AsyncSessionLocal() as mem_db:
                        conv = await mem_db.get(Conversation, conversation.id)
                        if conv is not None:
                            await memory_service.persist_turn(
                                mem_db,
                                virtual_key,
                                conv,
                                incoming_messages,
                                "".join(assistant_parts),
                            )
                except Exception:
                    logger.exception(
                        "Failed to persist streamed conversation turn (conversation=%s)",
                        getattr(conversation, "id", None),
                    )

    @staticmethod
    def _extract_assistant_content(response_dict: dict) -> str:
        try:
            choices = response_dict.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message") or {}
            content = message.get("content")
            return content if isinstance(content, str) else ""
        except Exception:
            return ""

    @staticmethod
    def _extract_stream_delta(chunk: object) -> str:
        try:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                return ""
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None) if delta is not None else None
            return content if isinstance(content, str) else ""
        except Exception:
            return ""

    async def _get_default_model(
        self, provider_id: str, db: AsyncSession
    ) -> ModelCatalog | None:
        # Prefer explicit provider default, but keep AUTO usable even when
        # no default is configured by falling back to the first active model.
        default_model = await db.scalar(
            select(ModelCatalog)
            .where(ModelCatalog.provider_id == provider_id)
            .where(ModelCatalog.is_default == True)  # noqa: E712
            .where(ModelCatalog.is_active == True)  # noqa: E712
            .where(ModelCatalog.is_enabled == True)  # noqa: E712
        )
        if default_model is not None:
            return default_model

        return await db.scalar(
            select(ModelCatalog)
            .where(ModelCatalog.provider_id == provider_id)
            .where(ModelCatalog.is_active == True)  # noqa: E712
            .where(ModelCatalog.is_enabled == True)  # noqa: E712
            .order_by(ModelCatalog.model_id.asc())
            .limit(1)
        )

    async def _get_model_by_name(
        self, provider_id: str, model_name: str, db: AsyncSession
    ) -> ModelCatalog | None:
        return await db.scalar(
            select(ModelCatalog)
            .where(ModelCatalog.provider_id == provider_id)
            .where(ModelCatalog.model_id.contains(model_name))
            .where(ModelCatalog.is_active == True)  # noqa: E712
            .where(ModelCatalog.is_enabled == True)  # noqa: E712
            .limit(1)
        )

    async def is_budget_exceeded(
        self, virtual_key: VirtualKey, db: AsyncSession
    ) -> bool:
        """Return True if the virtual key has exceeded its daily token budget."""
        if virtual_key.daily_token_budget is None:
            return False

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        used = await db.scalar(
            select(
                func.coalesce(
                    func.sum(RequestLog.input_tokens + RequestLog.output_tokens), 0
                )
            ).where(
                RequestLog.virtual_key_id == virtual_key.id,
                RequestLog.created_at >= today_start,
                RequestLog.status == "success",
            )
        )
        return (used or 0) >= virtual_key.daily_token_budget

    async def get_available_models(
        self, user_id: str, db: AsyncSession
    ) -> list[dict]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ApiKey, Provider)
            .join(Provider, ApiKey.provider_id == Provider.id)
            .outerjoin(ExhaustionState, ApiKey.id == ExhaustionState.api_key_id)
            .where(
                ApiKey.user_id == user_id,
                ApiKey.is_enabled == True,  # noqa: E712
                or_(
                    ExhaustionState.id == None,  # noqa: E711
                    ExhaustionState.exhausted_until < now,
                ),
            )
            .order_by(ApiKey.priority.asc())
        )
        pairs = result.all()

        models = []
        for ak, prov in pairs:
            catalog_result = await db.execute(
                select(ModelCatalog).where(
                    ModelCatalog.provider_id == prov.id,
                    ModelCatalog.is_active == True,  # noqa: E712
                    ModelCatalog.is_enabled == True,  # noqa: E712
                )
            )
            for mc in catalog_result.scalars().all():
                models.append({
                    "api_key": ak,
                    "provider": prov,
                    "model_id": mc.model_id,
                    "provider_slug": prov.slug,
                })
        return models

    async def mark_exhausted(
        self,
        api_key_id: str,
        reason: str,
        backoff_seconds: int,
        db: AsyncSession,
    ) -> None:
        exhausted_until = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
        result = await db.execute(
            select(ExhaustionState).where(ExhaustionState.api_key_id == api_key_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.exhausted_until = exhausted_until
            existing.reason = reason
        else:
            db.add(
                ExhaustionState(
                    api_key_id=api_key_id,
                    exhausted_until=exhausted_until,
                    reason=reason,
                )
            )
        await db.commit()

    async def reset_expired_exhaustions(self, db: AsyncSession) -> None:
        now = datetime.now(timezone.utc)
        await db.execute(
            delete(ExhaustionState).where(ExhaustionState.exhausted_until < now)
        )
        await db.commit()


proxy_manager = ProxyManager()
# Backward-compatibility alias used by app/scheduler.py
provider_manager = proxy_manager
