from app.proxy.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    slug = "anthropic"
    litellm_prefix = "anthropic/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {"model": f"anthropic/{model_id}", "api_key": api_key}
