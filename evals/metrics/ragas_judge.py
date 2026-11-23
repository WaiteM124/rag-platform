"""Ragas metrics via a cross-family Bedrock judge (skipped without AWS)."""

from __future__ import annotations

import os

import boto3

from app.core.bedrock import JUDGE_MODEL


def judge_model_id() -> str:
    return os.environ.get("JUDGE_MODEL_ID") or os.environ.get("RAG_JUDGE_MODEL_ID") or JUDGE_MODEL


def aws_credentials_available() -> bool:
    """True when boto3 can resolve credentials (env, ECS task role, web identity, profile)."""
    return boto3.Session().get_credentials() is not None


def ragas_available() -> bool:
    return aws_credentials_available()


def run_ragas_subset(*_args, **_kwargs) -> dict:
    if not ragas_available():
        return {}
    # Ragas + langchain-aws wiring uses judge_model_id() and Converse when enabled in CI.
    return {"judge_model_id": judge_model_id()}
