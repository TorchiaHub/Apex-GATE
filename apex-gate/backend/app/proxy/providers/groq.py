from app.proxy.providers.base import BaseProvider


class GroqProvider(BaseProvider):
    slug = "groq"
    litellm_prefix = "groq/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {
            "model": f"groq/{model_id}",
            "api_key": api_key,
            "api_base": "https://api.groq.com/openai/v1",
        }
