from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    aws_region: str = "eu-west-2"
    answer_model_id: str = os.environ.get("RAG_ANSWER_MODEL_ID", "eu.anthropic.claude-haiku-5-5")
    daily_spend_cap_gbp: float = 2.0
    usd_to_gbp: float = 0.79
    question_max_chars: int = 1000
    rate_limit_per_minute: int = 10
    rate_limit_per_day: int = 100
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    static_dir: str = "/app/static"
    https_enabled: bool = False

    model_config = {"env_prefix": "", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    cap = os.environ.get("DAILY_SPEND_CAP_GBP")
    settings = Settings(
        daily_spend_cap_gbp=float(cap) if cap else 2.0,
        langfuse_public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        langfuse_secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
        https_enabled=os.environ.get("HTTPS_ENABLED", "").lower() in ("1", "true", "yes"),
    )
    return settings
