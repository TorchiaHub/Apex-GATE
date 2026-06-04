from __future__ import annotations

import httpx

from app.discovery.base import AbstractScraper, ModelData


class GeminiScraper(AbstractScraper):
    provider_slug = "google_gemini"
    _url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def fetch_models(self) -> list[ModelData]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self._url)
            if resp.status_code != 200:
                return []
            data = resp.json().get("models", [])

        results = []
        for m in data:
            name = m.get("name", "").replace("models/", "")
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            ctx = m.get("inputTokenLimit", 0) or 0
            results.append(ModelData(
                model_id=f"gemini/{name}",
                display_name=m.get("displayName", name),
                context_window=ctx,
                supports_vision=any("vision" in v.lower() for v in m.get("supportedGenerationMethods", [])),
                supports_streaming=True,
                tier="free",
            ))
        return results
