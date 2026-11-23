from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    model_id: str

    def cost_usd(self, price_cards: dict) -> float:
        card = price_cards.get(self.model_id, {})
        in_rate = float(card.get("input_per_1k", 0))
        out_rate = float(card.get("output_per_1k", 0))
        return (self.input_tokens / 1000.0) * in_rate + (self.output_tokens / 1000.0) * out_rate


def load_price_cards(path: Path | None = None) -> dict:
    path = path or Path(__file__).resolve().parents[2] / "config" / "prices.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("models", {})
