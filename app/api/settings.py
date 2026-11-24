from __future__ import annotations

import logging
import os
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Terraform seeds Secrets Manager with this placeholder until the owner fills keys.
_LANGFUSE_PLACEHOLDER = "REPLACE_ME"


def normalize_langfuse_key(value: str | None) -> str:
    """Return a usable Langfuse key, or '' if blank / whitespace / placeholder."""
    if value is None:
        return ""
    cleaned = value.strip()
    if not cleaned:
        return ""
    if cleaned.casefold() == _LANGFUSE_PLACEHOLDER.casefold():
        return ""
    return cleaned


def langfuse_keys_configured(public_key: str, secret_key: str) -> bool:
    return bool(normalize_langfuse_key(public_key) and normalize_langfuse_key(secret_key))


def warn_langfuse_placeholder_once(public_key: str, secret_key: str) -> None:
    """Log a single warning when Terraform placeholders are still in place."""
    raw_public = (public_key or "").strip()
    raw_secret = (secret_key or "").strip()
    placeholder = _LANGFUSE_PLACEHOLDER.casefold()
    if raw_public.casefold() == placeholder or raw_secret.casefold() == placeholder:
        logger.warning(
            "Langfuse keys are still the Terraform placeholder (REPLACE_ME); "
            "tracing disabled until real keys are set in Secrets Manager"
        )


class Settings(BaseSettings):
    aws_region: str = "eu-west-2"
    answer_model_id: str = (
        os.environ.get("ANSWER_MODEL_ID")
        or os.environ.get("RAG_ANSWER_MODEL_ID")
        or "qwen.qwen3-235b-a22b-2507-v1:0"
    )
    judge_model_id: str = (
        os.environ.get("JUDGE_MODEL_ID") or os.environ.get("RAG_JUDGE_MODEL_ID") or "deepseek.v3.2"
    )
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

    @property
    def langfuse_enabled(self) -> bool:
        return langfuse_keys_configured(self.langfuse_public_key, self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    cap = os.environ.get("DAILY_SPEND_CAP_GBP")
    raw_public = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    raw_secret = os.environ.get("LANGFUSE_SECRET_KEY", "")
    settings = Settings(
        daily_spend_cap_gbp=float(cap) if cap else 2.0,
        langfuse_public_key=normalize_langfuse_key(raw_public),
        langfuse_secret_key=normalize_langfuse_key(raw_secret),
        langfuse_host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        https_enabled=os.environ.get("HTTPS_ENABLED", "").lower() in ("1", "true", "yes"),
    )
    return settings
