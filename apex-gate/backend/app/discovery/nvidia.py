from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.discovery.base import AbstractScraper, ModelData

# Fallback static list used only when the real free-models catalog file is
# missing or unreadable. NVIDIA NIM free-tier models don't expose a public
# /models endpoint, so we normally rely on the nvidia-free-models scraper output.
_KNOWN_NVIDIA_MODELS = [
    ("nvidia/llama-3.1-nemotron-70b-instruct", "Nemotron 70B", 131072),
    ("nvidia/llama-3.1-nemotron-51b-instruct", "Nemotron 51B", 131072),
    ("nvidia/llama-3.3-70b-instruct", "Llama 3.3 70B", 131072),
    ("nvidia/mistral-nemo-12b-instruct", "Mistral NeMo 12B", 131072),
    ("nvidia/llama-3.2-3b-instruct", "Llama 3.2 3B", 131072),
    ("nvidia/llama-3.2-1b-instruct", "Llama 3.2 1B", 131072),
]

_BUILD_URL_PREFIX = "https://build.nvidia.com/"


def _model_id_from_entry(entry: dict) -> str | None:
    """Derive the NIM model id (``publisher/model``) from a scraped entry.

    Prefers the build.nvidia.com URL path, which is exactly the model id NIM
    expects. Falls back to ``<publisher>/<name>`` when no URL is available.
    """
    url = (entry.get("url") or "").strip()
    if url.startswith(_BUILD_URL_PREFIX):
        path = url[len(_BUILD_URL_PREFIX):].strip("/")
        if path:
            return path
    name = (entry.get("name") or "").strip()
    publisher = (entry.get("publisher") or "").strip().lower()
    if name and publisher:
        return f"{publisher}/{name}"
    return None


class NvidiaScraper(AbstractScraper):
    """Reads the real NVIDIA free-endpoint catalog (nvidia-free-models output).

    Every entry in the catalog is a genuinely free endpoint, so all imported
    models are marked ``tier="free"``. The user then curates which ones are
    selectable via the per-model enable toggle (``is_enabled``).
    """

    provider_slug = "nvidia_nim"

    async def fetch_models(self) -> list[ModelData]:
        models = self._load_from_catalog()
        if models:
            return models
        return self._fallback_static()

    def _load_from_catalog(self) -> list[ModelData]:
        path = Path(settings.NVIDIA_FREE_MODELS_PATH)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(raw, list):
            return []

        out: list[ModelData] = []
        seen: set[str] = set()
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            model_id = _model_id_from_entry(entry)
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            display = (entry.get("name") or model_id).strip()
            out.append(
                ModelData(
                    model_id=model_id,
                    display_name=display,
                    context_window=0,
                    supports_tools=True,
                    supports_streaming=True,
                    tier="free",
                )
            )
        return out

    def _fallback_static(self) -> list[ModelData]:
        return [
            ModelData(
                model_id=mid,
                display_name=name,
                context_window=ctx,
                supports_tools=True,
                supports_streaming=True,
                tier="free",
            )
            for mid, name, ctx in _KNOWN_NVIDIA_MODELS
        ]
