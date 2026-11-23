from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class RankedItem:
    item_id: int
    score: float


def reciprocal_rank_fusion(
    ranked_lists: list[list[int]],
    *,
    k: int = 60,
    top_n: int = 8,
) -> list[RankedItem]:
    scores: dict[int, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] += 1.0 / (k + rank)
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [RankedItem(item_id=i, score=s) for i, s in ordered[:top_n]]
