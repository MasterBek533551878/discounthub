from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BACKEND_ROOT


class AiSettings(BaseSettings):
    ai_assistant_enabled: bool = True
    ai_assistant_hourly_limit: int = 30
    ai_assistant_browser_hourly_limit: int = 30
    ai_assistant_ip_hourly_limit: int = 300
    ai_assistant_result_limit: int = 8
    ai_assistant_provider_timeout_seconds: int = 12
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )


@lru_cache
def get_ai_settings() -> AiSettings:
    return AiSettings()
