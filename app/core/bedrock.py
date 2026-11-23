from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import Any

import boto3

THINKING_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINKING_OPEN = "<think>"
_THINKING_CLOSE = "</think>"

REGION = os.environ.get("AWS_REGION", "eu-west-2")


def _env_model(*keys: str, default: str) -> str:
    for key in keys:
        if value := os.environ.get(key):
            return value
    return default


ANSWER_MODEL = _env_model(
    "ANSWER_MODEL_ID",
    "RAG_ANSWER_MODEL_ID",
    default="qwen.qwen3-235b-a22b-2507-v1:0",
)
JUDGE_MODEL = _env_model(
    "JUDGE_MODEL_ID",
    "RAG_JUDGE_MODEL_ID",
    default="deepseek.v3.2",
)


def strip_thinking_text(text: str) -> str:
    return THINKING_BLOCK_RE.sub("", text)


class ThinkingStreamFilter:
    """Remove Qwen3 extended-thinking blocks from streamed Converse deltas."""

    def __init__(self) -> None:
        self._buffer = ""
        self._in_thinking = False

    def push(self, chunk: str) -> str:
        self._buffer += chunk
        emitted: list[str] = []
        while self._buffer:
            if self._in_thinking:
                close_at = self._buffer.find(_THINKING_CLOSE)
                if close_at == -1:
                    break
                self._buffer = self._buffer[close_at + len(_THINKING_CLOSE) :]
                self._in_thinking = False
                continue

            open_at = self._buffer.find(_THINKING_OPEN)
            if open_at == -1:
                keep = 0
                max_prefix = min(len(self._buffer), len(_THINKING_OPEN) - 1)
                for n in range(max_prefix, 0, -1):
                    if _THINKING_OPEN.startswith(self._buffer[-n:]):
                        keep = n
                        break
                flush_len = len(self._buffer) - keep
                if flush_len:
                    emitted.append(self._buffer[:flush_len])
                    self._buffer = self._buffer[flush_len:]
                break

            if open_at > 0:
                emitted.append(self._buffer[:open_at])
            self._buffer = self._buffer[open_at + len(_THINKING_OPEN) :]
            self._in_thinking = True

        return "".join(emitted)

    def finish(self) -> str:
        if self._in_thinking:
            self._buffer = ""
            self._in_thinking = False
            return ""
        tail = strip_thinking_text(self._buffer)
        self._buffer = ""
        return tail


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
    text = strip_thinking_text("".join(part.get("text", "") for part in output))
    usage = resp.get("usage", {})
    tokens = {
        "input_tokens": int(usage.get("inputTokens", 0)),
        "output_tokens": int(usage.get("outputTokens", 0)),
    }
    return text, tokens


def converse_stream(
    messages: list[dict[str, Any]],
    *,
    system: str,
    model_id: str | None = None,
    max_tokens: int = 1024,
) -> tuple[Iterator[str], dict[str, int]]:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    model_id = model_id or ANSWER_MODEL
    resp = client.converse_stream(
        modelId=model_id,
        system=[{"text": system}],
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0},
    )
    usage = {"input_tokens": 0, "output_tokens": 0}
    thinking_filter = ThinkingStreamFilter()

    def gen() -> Iterator[str]:
        for event in resp.get("stream", []):
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if text := delta.get("text"):
                    clean = thinking_filter.push(text)
                    if clean:
                        yield clean
            if "metadata" in event:
                meta = event["metadata"].get("usage", {})
                usage["input_tokens"] = int(meta.get("inputTokens", usage["input_tokens"]))
                usage["output_tokens"] = int(meta.get("outputTokens", usage["output_tokens"]))
        tail = thinking_filter.finish()
        if tail:
            yield tail

    return gen(), usage
