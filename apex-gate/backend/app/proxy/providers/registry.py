from __future__ import annotations

# NOTE: This module and the entire proxy/providers/ directory are DEAD CODE.
# ProxyManager (proxy/manager.py) routes all requests via LiteLLM Router and
# never imports PROVIDER_REGISTRY. Kept for potential future use but not
# executed in the current architecture.

from app.proxy.providers.anthropic import AnthropicProvider
from app.proxy.providers.base import BaseProvider
from app.proxy.providers.gemini import GeminiProvider
from app.proxy.providers.groq import GroqProvider
from app.proxy.providers.huggingface import HuggingFaceProvider
from app.proxy.providers.mistral import MistralProvider
from app.proxy.providers.nvidia import NvidiaProvider
from app.proxy.providers.ollama import OllamaProvider
from app.proxy.providers.openai import OpenAIProvider
from app.proxy.providers.openrouter import OpenRouterProvider

PROVIDER_REGISTRY: dict[str, BaseProvider] = {
    "nvidia_nim": NvidiaProvider(),
    "openrouter": OpenRouterProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "gemini": GeminiProvider(),
    "groq": GroqProvider(),
    "ollama": OllamaProvider(),
    "mistral": MistralProvider(),
    "huggingface": HuggingFaceProvider(),
}
