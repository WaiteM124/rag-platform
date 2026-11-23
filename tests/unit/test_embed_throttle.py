from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from ingest.config import bedrock_runtime
from ingest.embed import EmbeddingThrottledError, embed_texts, get_embed_stats, reset_embed_stats

DIM = 1024


def _throttle_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "InvokeModel",
    )


def _ok_response() -> dict:
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": [0.1] * DIM}).encode()
    return {"body": body}


@pytest.fixture(autouse=True)
def _clear_bedrock_cache():
    bedrock_runtime.cache_clear()
    reset_embed_stats()
    yield
    bedrock_runtime.cache_clear()
    reset_embed_stats()


def test_embed_retries_after_throttling_then_succeeds() -> None:
    client = MagicMock()
    client.invoke_model.side_effect = [_throttle_error(), _ok_response()]
    with (
        patch.dict("os.environ", {"EMBED_MAX_RPS": "1000"}),
        patch("ingest.embed.bedrock_runtime", return_value=client),
    ):
        vectors = embed_texts(["hello"])

    assert len(vectors) == 1
    assert len(vectors[0]) == DIM
    stats = get_embed_stats()
    assert stats["calls"] == 2
    assert stats["throttle_retries"] == 1


def test_embed_raises_after_exhausted_throttle_retries() -> None:
    from tenacity import stop_after_attempt

    from ingest import embed as embed_mod

    client = MagicMock()
    client.invoke_model.side_effect = _throttle_error()
    with (
        patch.dict("os.environ", {"EMBED_MAX_RPS": "1000"}),
        patch("ingest.embed.bedrock_runtime", return_value=client),
        patch.object(embed_mod._invoke_model.retry, "stop", stop_after_attempt(3)),
        patch.object(embed_mod._invoke_model.retry, "wait", __import__("tenacity").wait_fixed(0)),
    ):
        with pytest.raises(EmbeddingThrottledError):
            embed_texts(["hello"])

    stats = get_embed_stats()
    assert stats["calls"] == 3
    assert stats["throttle_retries"] == 2
