from __future__ import annotations

import json
from pathlib import Path

import yaml

GOLDEN = Path(__file__).resolve().parents[2] / "evals/complex-systems/golden_live.jsonl"
SOURCES = Path(__file__).resolve().parents[2] / "collections/complex-systems/sources.yaml"


def test_golden_live_answerable_rows() -> None:
    source_ids = {s["id"] for s in yaml.safe_load(SOURCES.read_text(encoding="utf-8"))["sources"]}
    lines = GOLDEN.read_text(encoding="utf-8").splitlines()
    items = [json.loads(line) for line in lines if line.strip()]
    answerable = [i for i in items if i.get("expected_source_ids")]
    assert len(answerable) >= 28
    for row in answerable:
        assert row.get("evidence", "").strip(), f"missing evidence on {row.get('id')}"
        for sid in row["expected_source_ids"]:
            assert sid in source_ids, f"unknown source_id {sid} on {row.get('id')}"