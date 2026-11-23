from __future__ import annotations

import os
from typing import Any

import boto3

REGION = os.environ.get("AWS_REGION", "eu-west-2")
ANSWER_MODEL = os.environ.get("RAG_ANSWER_MODEL_ID", "eu.anthropic.claude-haiku-5-5")


def converse(
    messages: list[dict[str, Any]],
    *,
    system: str,
    model_id: str | None = None,
    max_tokens: int = 1024,
) -> tuple[str, dict[str, int]]:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    model_id = model_id or ANSWER_MODEL
    resp = client.converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0},
    )
    output = resp.get("output", {}).get("message", {}).get("content", [])
    text = "".join(part.get("text", "") for part in output)
    usage = resp.get("usage", {})
    tokens = {
        "input_tokens": int(usage.get("inputTokens", 0)),
        "output_tokens": int(usage.get("outputTokens", 0)),
    }
    return text, tokens
