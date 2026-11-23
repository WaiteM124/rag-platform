from __future__ import annotations

from dataclasses import dataclass

import yaml


class LicenceValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SourceRecord:
    id: str
    title: str
    authors: list[str]
    year: int | None
    url: str
    licence: str
    licence_url: str
    licence_class: str
    nc_flag: bool
    nd_flag: bool
    attribution_text: str
    format: str
    module: str | None = None

    def validate(self) -> None:
        missing = []
        for field_name in (
            "licence",
            "licence_url",
            "licence_class",
            "attribution_text",
        ):
            if not getattr(self, field_name):
                missing.append(field_name)
        if missing:
            raise LicenceValidationError(
                f"Source {self.id} missing licence fields: {', '.join(missing)}"
            )
        if self.licence_class not in {"A", "B", "C"}:
            raise LicenceValidationError(f"Source {self.id} has invalid licence_class")


def load_sources(path: str) -> list[SourceRecord]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    records: list[SourceRecord] = []
    for raw in data["sources"]:
        rec = SourceRecord(
            id=raw["id"],
            title=raw["title"],
            authors=raw.get("authors", []),
            year=raw.get("year"),
            url=raw["url"],
            licence=raw["licence"],
            licence_url=raw["licence_url"],
            licence_class=raw["licence_class"],
            nc_flag=bool(raw.get("nc_flag", False)),
            nd_flag=bool(raw.get("nd_flag", False)),
            attribution_text=raw["attribution_text"],
            format=raw["format"],
            module=raw.get("module"),
        )
        rec.validate()
        records.append(rec)
    return records
