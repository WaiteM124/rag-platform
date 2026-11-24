from __future__ import annotations

from pathlib import Path

import yaml

from app.core.cost import (
    TokenUsage,
    combine_costs,
    estimate_embed_cost,
    load_price_cards,
)


def test_verified_generation_cost():
    cards = {
        "qwen.qwen3-235b-a22b-2507-v1:0": {
            "input_per_1k": 0.00034,
            "output_per_1k": 0.00137,
            "verified": True,
        }
    }
    est = TokenUsage(1000, 1000, "qwen.qwen3-235b-a22b-2507-v1:0").estimate_cost(cards)
    assert est.status == "ok"
    assert est.usd is not None
    assert abs(est.usd - (0.00034 + 0.00137)) < 1e-12


def test_unverified_price_returns_unverified_status():
    cards = {
        "mystery.model": {
            "input_per_1k": None,
            "output_per_1k": None,
            "verified": False,
        }
    }
    est = TokenUsage(10, 5, "mystery.model").estimate_cost(cards)
    assert est.status == "unverified"
    assert est.usd is None
    assert est.verified is False


def test_unverified_flag_even_with_numbers():
    cards = {
        "foo": {
            "input_per_1k": 0.1,
            "output_per_1k": 0.2,
            "verified": False,
        }
    }
    est = TokenUsage(1000, 1000, "foo").estimate_cost(cards)
    assert est.status == "unverified"
    assert est.usd is None


def test_missing_model_is_unverified():
    est = TokenUsage(1, 1, "nope").estimate_cost({})
    assert est.status == "unverified"


def test_embed_and_combine():
    cards = {
        "amazon.titan-embed-text-v2:0": {
            "input_per_1k": 0.0001,
            "output_per_1k": 0.0,
            "verified": True,
        },
        "qwen.qwen3-235b-a22b-2507-v1:0": {
            "input_per_1k": 0.00034,
            "output_per_1k": 0.00137,
            "verified": True,
        },
    }
    embed = estimate_embed_cost(1000, "amazon.titan-embed-text-v2:0", cards)
    gen = TokenUsage(1000, 0, "qwen.qwen3-235b-a22b-2507-v1:0").estimate_cost(cards)
    total = combine_costs(embed, gen)
    assert total.status == "ok"
    assert abs(float(total.usd) - 0.00044) < 1e-12


def test_combine_unverified_short_circuits():
    ok = TokenUsage(1, 1, "a").estimate_cost(
        {"a": {"input_per_1k": 1.0, "output_per_1k": 1.0, "verified": True}}
    )
    bad = TokenUsage(1, 1, "b").estimate_cost({})
    assert combine_costs(ok, bad).status == "unverified"


def test_repo_price_cards_have_verified_flags():
    path = Path(__file__).resolve().parents[2] / "config" / "prices.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    models = data["models"]
    for model_id in (
        "qwen.qwen3-235b-a22b-2507-v1:0",
        "deepseek.v3.2",
        "amazon.titan-embed-text-v2:0",
    ):
        card = models[model_id]
        assert card["verified"] is True
        assert card["input_per_1k"] is not None
        assert "source_url" in card
    loaded = load_price_cards(path)
    assert "qwen.qwen3-235b-a22b-2507-v1:0" in loaded
