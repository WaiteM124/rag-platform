from __future__ import annotations

import json
import os

from pgvector import Vector

from ingest.config import bedrock_runtime

DEFAULT_MODEL = os.environ.get("RAG_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
DIMENSIONS = 1024


def to_vector(values: list[float]) -> Vector:
    return Vector(values)


def embed_texts(texts: list[str], model_id: str | None = None) -> list[list[float]]:
    model_id = model_id or DEFAULT_MODEL
    client = bedrock_runtime()
    vectors: list[list[float]] = []
    for text in texts:
        body = json.dumps({"inputText": text[:25000], "dimensions": DIMENSIONS})
        resp = client.invoke_model(modelId=model_id, body=body)
        payload = json.loads(resp["body"].read())
        emb = payload.get("embedding") or payload.get("embeddingsByType", {}).get("float")
        if not emb:
            raise RuntimeError(f"Unexpected embedding response keys: {payload.keys()}")
        vectors.append(emb)
    return vectors
