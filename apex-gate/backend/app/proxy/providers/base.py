from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    slug: str
    litellm_prefix: str

    @abstractmethod
    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        """Return kwargs for litellm.acompletion()."""
