from __future__ import annotations

import re

from app.core.retrieval import RetrievedChunk

MODE_MAP = {"A": "full_text", "B": "full_text", "C": "excerpt_link"}


def cited_indices(answer: str) -> list[int]:
    return sorted({int(m) for m in re.findall(r"\[(\d+)\]", answer)})


def build_citations(answer: str, chunks: list[RetrievedChunk]) -> list[dict]:
    by_idx = {i + 1: c for i, c in enumerate(chunks)}
    out: list[dict] = []
    for idx in cited_indices(answer):
        ch = by_idx.get(idx)
        if not ch:
            continue
        out.append(
            {
                "index": idx,
                "source_id": ch.source_id,
                "title": ch.title,
                "url": ch.source_url,
                "licence_class": ch.licence_class,
                "attribution": ch.attribution_text,
                "mode": MODE_MAP.get(ch.licence_class, "excerpt_link"),
            }
        )
    return out
