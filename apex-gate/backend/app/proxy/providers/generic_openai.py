from __future__ import annotations
from app.proxy.providers.base import BaseProvider


class GenericOpenAIProvider(BaseProvider):
    """Handles any OpenAI-compatible API with a custom base URL."""
    slug = "generic_openai"
    litellm_prefix = "openai/"

    def __init__(self, api_base: str) -> None:
        self.api_base = api_base

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {
            "model": f"openai/{model_id}",
            "api_key": api_key,
            "api_base": self.api_base,
        }
