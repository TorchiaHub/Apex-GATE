from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the backend root directory from this file's location so that
# database paths are always absolute, regardless of the process CWD.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
_DATA_DIR = _BACKEND_DIR / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    DATABASE_URL: str = f"sqlite+aiosqlite:///{_DATA_DIR / 'apex_gate.db'}"
    AUTH_DATABASE_URL: str = f"sqlite+aiosqlite:///{_DATA_DIR / 'apex_gate_auth.db'}"

    SECRET_KEY: str
    FERNET_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    PROXY_HOST: str = "0.0.0.0"
    PROXY_PORT: int = 8000

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    DISCOVERY_INTERVAL_HOURS: int = 6
    LOG_RETENTION_DAYS: int = 90

    # Path to the real NVIDIA free-endpoint catalog produced by the
    # nvidia-free-models scraper. Used by discovery to populate the model
    # catalog with the genuinely-free NVIDIA NIM models.
    NVIDIA_FREE_MODELS_PATH: str = str(
        _BACKEND_DIR.parent.parent / "tools" / "nvidia-free-models" / "latest.json"
    )


settings = Settings()
