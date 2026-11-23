from __future__ import annotations

import json
import os
from functools import lru_cache

import boto3
from botocore.config import Config

USER_AGENT = (
    "rag-platform/0.1 (+https://github.com/WaiteM124/rag-platform; Complex-Systems-RAG-ingest)"
)

CACHE_DIR = os.environ.get("RAG_INGEST_CACHE", "/tmp/rag-platform-ingest-cache")


@lru_cache(maxsize=1)
def bedrock_runtime():
    region = os.environ.get("AWS_REGION", "eu-west-2")
    config = Config(retries={"mode": "adaptive", "max_attempts": 10})
    return boto3.client("bedrock-runtime", region_name=region, config=config)


def db_dsn() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    host = os.environ.get("RAG_DB_HOST", "localhost")
    port = os.environ.get("RAG_DB_PORT", "5432")
    name = os.environ.get("RAG_DB_NAME", "ragplatform")
    user = os.environ.get("RAG_DB_USER", "rag")
    password = os.environ.get("RAG_DB_PASSWORD", "raglocal")
    secret_arn = os.environ.get("RAG_DB_SECRET_ARN")
    if secret_arn:
        user, password = _credentials_from_secret(secret_arn)
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _credentials_from_secret(secret_arn: str) -> tuple[str, str]:
    sm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "eu-west-2"))
    raw = sm.get_secret_value(SecretId=secret_arn)["SecretString"]
    data = json.loads(raw)
    return data["username"], data["password"]
