from app.proxy.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    slug = "gemini"
    litellm_prefix = "gemini/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {"model": f"gemini/{model_id}", "api_key": api_key}
