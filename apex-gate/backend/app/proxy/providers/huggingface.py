from app.proxy.providers.base import BaseProvider


class HuggingFaceProvider(BaseProvider):
    slug = "huggingface"
    litellm_prefix = "huggingface/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {
            "model": f"huggingface/{model_id}",
            "api_key": api_key,
            "api_base": "https://api-inference.huggingface.co/v1",
        }
