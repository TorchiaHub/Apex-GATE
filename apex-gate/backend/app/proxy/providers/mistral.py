from app.proxy.providers.base import BaseProvider


class MistralProvider(BaseProvider):
    slug = "mistral"
    litellm_prefix = "mistral/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {
            "model": f"mistral/{model_id}",
            "api_key": api_key,
            "api_base": "https://api.mistral.ai/v1",
        }
