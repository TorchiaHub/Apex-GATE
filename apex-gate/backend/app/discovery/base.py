from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ModelData:
    model_id: str
    display_name: str
    context_window: int = 0
    supports_vision: bool = False
    supports_tools: bool = False
    supports_streaming: bool = True
    cost_input_per_1m_usd: float | None = None
    cost_output_per_1m_usd: float | None = None
    tier: str = "free"


class AbstractScraper(ABC):
    provider_slug: str

    @abstractmethod
    async def fetch_models(self) -> list[ModelData]: ...
