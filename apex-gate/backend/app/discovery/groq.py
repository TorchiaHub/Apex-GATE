from __future__ import annotations

import httpx

from app.discovery.base import AbstractScraper, ModelData


class GroqScraper(AbstractScraper):
    provider_slug = "groq"
    _url = "https://api.groq.com/openai/v1/models"

    async def fetch_models(self) -> list[ModelData]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self._url)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", [])

        return [
            ModelData(
                model_id=m.get("id", ""),
                display_name=m.get("id", ""),
                context_window=m.get("context_window", 0) or 0,
                supports_streaming=True,
                tier="free",
            )
            for m in data
        ]
