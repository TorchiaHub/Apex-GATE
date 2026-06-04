from app.proxy.providers.base import BaseProvider


class NvidiaProvider(BaseProvider):
    slug = "nvidia_nim"
    litellm_prefix = "nvidia_nim/"

    def get_litellm_params(self, api_key: str, model_id: str) -> dict:
        return {
            "model": f"nvidia_nim/{model_id}",
            "api_key": api_key,
            "api_base": "https://integrate.api.nvidia.com/v1",
        }
