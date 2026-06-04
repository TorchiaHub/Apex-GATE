from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_catalog import ModelCatalog
from app.models.provider import Provider

PROVIDERS: list[dict] = [
    {"slug": "nvidia_nim", "name": "NVIDIA NIM", "protocol": "openai", "api_base_url": "https://integrate.api.nvidia.com/v1", "supports_free_tier": True, "litellm_prefix": "nvidia_nim/", "is_active": True, "sort_order": 1},
    {"slug": "openrouter", "name": "OpenRouter", "protocol": "openai", "api_base_url": "https://openrouter.ai/api/v1", "supports_free_tier": True, "litellm_prefix": "openrouter/", "is_active": True, "sort_order": 2},
    {"slug": "gemini", "name": "Google Gemini", "protocol": "gemini", "api_base_url": None, "supports_free_tier": True, "litellm_prefix": "gemini/", "is_active": True, "sort_order": 3},
    {"slug": "groq", "name": "Groq", "protocol": "openai", "api_base_url": "https://api.groq.com/openai/v1", "supports_free_tier": True, "litellm_prefix": "groq/", "is_active": True, "sort_order": 4},
    {"slug": "mistral", "name": "Mistral AI", "protocol": "openai", "api_base_url": "https://api.mistral.ai/v1", "supports_free_tier": True, "litellm_prefix": "mistral/", "is_active": True, "sort_order": 5},
    {"slug": "ollama", "name": "Ollama (local)", "protocol": "ollama", "api_base_url": "http://localhost:11434", "supports_free_tier": True, "litellm_prefix": "ollama/", "is_active": True, "sort_order": 6},
    {"slug": "huggingface", "name": "HuggingFace Inference", "protocol": "openai", "api_base_url": "https://router.huggingface.co", "supports_free_tier": True, "litellm_prefix": "huggingface/", "is_active": True, "sort_order": 7},
    {"slug": "openai", "name": "OpenAI", "protocol": "openai", "api_base_url": None, "supports_free_tier": False, "litellm_prefix": "openai/", "is_active": True, "sort_order": 10},
    {"slug": "anthropic", "name": "Anthropic", "protocol": "anthropic", "api_base_url": None, "supports_free_tier": False, "litellm_prefix": "anthropic/", "is_active": True, "sort_order": 11},
    {"slug": "azure_openai", "name": "Azure OpenAI", "protocol": "openai", "api_base_url": None, "supports_free_tier": False, "litellm_prefix": "azure/", "is_active": True, "sort_order": 12},
    {"slug": "together_ai", "name": "Together AI", "protocol": "openai", "api_base_url": "https://api.together.xyz/v1", "supports_free_tier": False, "litellm_prefix": "together_ai/", "is_active": True, "sort_order": 13},
    {"slug": "fireworks_ai", "name": "Fireworks AI", "protocol": "openai", "api_base_url": "https://api.fireworks.ai/inference/v1", "supports_free_tier": False, "litellm_prefix": "fireworks_ai/", "is_active": True, "sort_order": 14},
    {"slug": "cerebras", "name": "Cerebras", "protocol": "openai", "api_base_url": "https://api.cerebras.ai/v1", "supports_free_tier": True, "litellm_prefix": "cerebras/", "is_active": True, "sort_order": 15},
    {"slug": "perplexity", "name": "Perplexity", "protocol": "openai", "api_base_url": "https://api.perplexity.ai", "supports_free_tier": False, "litellm_prefix": "perplexity/", "is_active": True, "sort_order": 16},
    {"slug": "cohere", "name": "Cohere", "protocol": "cohere", "api_base_url": None, "supports_free_tier": False, "litellm_prefix": "cohere/", "is_active": True, "sort_order": 17},
    {"slug": "xai", "name": "xAI (Grok)", "protocol": "openai", "api_base_url": "https://api.x.ai/v1", "supports_free_tier": False, "litellm_prefix": "xai/", "is_active": True, "sort_order": 18},
    {"slug": "deepseek", "name": "DeepSeek", "protocol": "openai", "api_base_url": "https://api.deepseek.com/v1", "supports_free_tier": False, "litellm_prefix": "deepseek/", "is_active": True, "sort_order": 19},
    {"slug": "cloudflare_ai", "name": "Cloudflare Workers AI", "protocol": "openai", "api_base_url": None, "supports_free_tier": True, "litellm_prefix": "cloudflare/", "is_active": False, "sort_order": 20},  # Requires manual account_id configuration before enabling
    {"slug": "replicate", "name": "Replicate", "protocol": "openai", "api_base_url": None, "supports_free_tier": False, "litellm_prefix": "replicate/", "is_active": True, "sort_order": 21},
]

# Default model per provider used in AUTO mode.
# is_default=True flags the model selected when a client sends model="auto".
# Only one is_default=True per provider is enforced at the application level.
DEFAULT_MODELS: list[dict] = [
    {"provider_slug": "groq", "model_id": "llama-3.3-70b-versatile", "display_name": "Llama 3.3 70B Versatile"},
    {"provider_slug": "nvidia_nim", "model_id": "meta/llama-3.1-8b-instruct", "display_name": "Llama 3.1 8B Instruct"},
    {"provider_slug": "gemini", "model_id": "gemini-2.0-flash", "display_name": "Gemini 2.0 Flash"},
    {"provider_slug": "openrouter", "model_id": "auto", "display_name": "OpenRouter Auto (free)"},
    {"provider_slug": "mistral", "model_id": "mistral-small-latest", "display_name": "Mistral Small"},
    {"provider_slug": "cerebras", "model_id": "llama3.1-8b", "display_name": "Llama 3.1 8B (Cerebras)"},
    {"provider_slug": "huggingface", "model_id": "Qwen/Qwen2.5-72B-Instruct", "display_name": "Qwen 2.5 72B"},
    {"provider_slug": "ollama", "model_id": "llama3.2", "display_name": "Llama 3.2"},
]


async def seed_providers(session: AsyncSession) -> None:
    for data in PROVIDERS:
        result = await session.execute(select(Provider).where(Provider.slug == data["slug"]))
        if result.scalar_one_or_none() is None:
            session.add(Provider(**data))
    await session.commit()


async def seed_default_models(session: AsyncSession) -> None:
    """Insert default model entries for AUTO mode routing.

    Idempotent: skips entries that already exist for (provider_id, model_id).
    Skips silently if the provider slug is not found in the database.
    """
    for entry in DEFAULT_MODELS:
        provider_result = await session.execute(
            select(Provider).where(Provider.slug == entry["provider_slug"])
        )
        provider = provider_result.scalar_one_or_none()
        if provider is None:
            continue

        existing = await session.execute(
            select(ModelCatalog).where(
                ModelCatalog.provider_id == provider.id,
                ModelCatalog.model_id == entry["model_id"],
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(
                ModelCatalog(
                    provider_id=provider.id,
                    model_id=entry["model_id"],
                    display_name=entry["display_name"],
                    tier="free",
                    is_active=True,
                    supports_streaming=True,
                    is_default=True,
                )
            )

    await session.commit()
