from app.proxy.providers.base import BaseProvider


class OpenRouterProvider(BaseProvider):
    slug = "openrouter"
    litellm_prefix = "openrouter/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {
            "model": f"openrouter/{model_id}",
            "api_key": api_key,
            "api_base": "https://openrouter.ai/api/v1",
            "extra_headers": {"HTTP-Referer": "http://localhost:4000"},
        }
