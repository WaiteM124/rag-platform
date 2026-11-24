from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PriceCard:
    model_id: str
    input_per_1k: float | None
    output_per_1k: float | None
    verified: bool
    source_url: str = ""

    @property
    def usable(self) -> bool:
        return self.verified and self.input_per_1k is not None and self.output_per_1k is not None


@dataclass(frozen=True)
class CostEstimate:
    """USD cost for a model call, or unverified when prices are missing."""

    usd: float | None
    verified: bool
    status: str  # "ok" | "unverified"

    @classmethod
    def ok(cls, usd: float) -> CostEstimate:
        return cls(usd=usd, verified=True, status="ok")

    @classmethod
    def unverified(cls) -> CostEstimate:
        return cls(usd=None, verified=False, status="unverified")


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    model_id: str

    def cost_usd(self, price_cards: dict[str, Any]) -> float:
        """Legacy helper: returns 0.0 when unverified (prefer estimate_cost)."""
        est = self.estimate_cost(price_cards)
        return float(est.usd or 0.0)

    def estimate_cost(self, price_cards: dict[str, Any]) -> CostEstimate:
        card = _as_card(self.model_id, price_cards.get(self.model_id))
        if card is None or not card.usable:
            return CostEstimate.unverified()
        usd = (self.input_tokens / 1000.0) * float(card.input_per_1k) + (
            self.output_tokens / 1000.0
        ) * float(card.output_per_1k)
        return CostEstimate.ok(usd)


def _as_card(model_id: str, raw: Any) -> PriceCard | None:
    if not isinstance(raw, dict):
        return None
    return PriceCard(
        model_id=model_id,
        input_per_1k=_maybe_float(raw.get("input_per_1k")),
        output_per_1k=_maybe_float(raw.get("output_per_1k")),
        verified=bool(raw.get("verified", False)),
        source_url=str(raw.get("source_url") or ""),
    )


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def load_price_cards(path: Path | None = None) -> dict[str, Any]:
    path = path or Path(__file__).resolve().parents[2] / "config" / "prices.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("models", {})


def estimate_embed_cost(
    input_tokens: int,
    model_id: str,
    price_cards: dict[str, Any],
) -> CostEstimate:
    card = _as_card(model_id, price_cards.get(model_id))
    if card is None or not card.verified or card.input_per_1k is None:
        return CostEstimate.unverified()
    return CostEstimate.ok((input_tokens / 1000.0) * float(card.input_per_1k))


def combine_costs(*parts: CostEstimate) -> CostEstimate:
    if any(not p.verified or p.usd is None for p in parts):
        return CostEstimate.unverified()
    return CostEstimate.ok(sum(float(p.usd) for p in parts))
