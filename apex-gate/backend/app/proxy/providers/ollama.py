from app.proxy.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    slug = "ollama"
    litellm_prefix = "ollama/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {
            "model": f"ollama/{model_id}",
            "api_key": api_key or "ollama",
            "api_base": "http://localhost:11434",
        }
