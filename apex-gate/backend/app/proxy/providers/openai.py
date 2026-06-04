from app.proxy.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    slug = "openai"
    litellm_prefix = "openai/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {"model": model_id, "api_key": api_key}
