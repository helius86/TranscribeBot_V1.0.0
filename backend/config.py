from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    volcengine_api_key: Optional[str] = Field(
        default=None, env=["VOLCENGINE_API_KEY", "ARK_API_KEY"]
    )
    volcengine_model: str = Field(default="doubao-seed-1-6", env="VOLCENGINE_MODEL")
    volcengine_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        env="VOLCENGINE_BASE_URL",
    )

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
