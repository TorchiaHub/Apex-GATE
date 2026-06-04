from __future__ import annotations

import httpx

from app.discovery.base import AbstractScraper, ModelData


class OpenRouterScraper(AbstractScraper):
    provider_slug = "openrouter"
    _url = "https://openrouter.ai/api/v1/models"

    async def fetch_models(self) -> list[ModelData]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self._url)
            resp.raise_for_status()
            data = resp.json().get("data", [])

        results = []
        for m in data:
            model_id = m.get("id", "")
            if not model_id:
                continue

            pricing = m.get("pricing", {})
            try:
                cost_in = float(pricing.get("prompt", 0)) * 1_000_000
                cost_out = float(pricing.get("completion", 0)) * 1_000_000
            except (TypeError, ValueError):
                cost_in = cost_out = 0.0

            # Keep only free models: OpenRouter flags these with a ":free"
            # suffix and zero prompt/completion pricing.
            is_free = model_id.endswith(":free") or cost_in == 0
            if not is_free:
                continue

            modality = str(m.get("architecture", {}).get("modality", "")).lower()
            supports_vision = (
                "image" in modality or "vision" in str(m.get("description", "")).lower()
            )

            results.append(ModelData(
                model_id=model_id,
                display_name=m.get("name", model_id),
                context_window=m.get("context_length", 0) or 0,
                supports_vision=supports_vision,
                supports_tools=m.get("supports_tool_call", False),
                supports_streaming=True,
                cost_input_per_1m_usd=None,
                cost_output_per_1m_usd=None,
                tier="free",
            ))
        return results
