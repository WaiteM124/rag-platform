#!/usr/bin/env python3
"""Generate collections/complex-systems/sources.yaml from docs/complex-systems-sources.md."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "complex-systems-sources.md"
OUT = ROOT / "collections" / "complex-systems" / "sources.yaml"

ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([A-I])\s*\|\s*\[(.+?)\]\((https?://[^)]+)\).*?\|\s*\*\*([ABC])\*\*\s*\|\s*([^|]+)\|",
    re.MULTILINE,
)


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    sources = []
    for m in ROW.finditer(text):
        num = int(m.group(1))
        module = m.group(2)
        title_authors = m.group(3)
        url = m.group(4).strip()
        licence_class = m.group(5)
        fmt = m.group(6).strip().lower()
        title = title_authors.split("—")[0].strip()
        authors_part = title_authors.split("—", 1)
        authors = []
        year = None
        if len(authors_part) > 1:
            meta = authors_part[1]
            authors = [a.strip() for a in meta.split(",") if a.strip()]
            ym = re.search(r"\((\d{4})", meta)
            if ym:
                year = int(ym.group(1))
        licence, licence_url, nc, nd, attr = _licence_defaults(licence_class, title, url, num)
        format_key = _format_key(fmt, url)
        sources.append(
            {
                "id": f"cs-{num:03d}",
                "module": module,
                "title": title,
                "authors": authors[:5] or ["Unknown"],
                "year": year,
                "url": _canonical_url(num, url),
                "licence": licence,
                "licence_url": licence_url,
                "licence_class": licence_class,
                "nc_flag": nc,
                "nd_flag": nd,
                "attribution_text": attr,
                "format": format_key,
            }
        )
    if len(sources) != 46:
        raise SystemExit(f"Expected 46 sources, parsed {len(sources)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        yaml.safe_dump(
            {"version": 1, "collection": "complex-systems", "sources": sources},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(sources)} sources to {OUT}")


def _canonical_url(num: int, url: str) -> str:
    overrides = {
        20: "https://sethna.lassp.cornell.edu/StatMech/EntropyOrderParametersComplexity20.pdf",
        34: "https://www.damtp.cam.ac.uk/user/tong/statphys.html",
        35: "https://www.ams.org/journals/bull/2003-40-04/S0273-0979-03-00988-1/",
    }
    return overrides.get(num, url)


def _format_key(fmt: str, url: str) -> str:
    if "latex" in fmt or "arxiv" in fmt:
        return "arxiv_src" if "arxiv" in url else "latex"
    if "pdf" in fmt:
        return "pdf"
    if "plos" in fmt or "jats" in fmt:
        return "jats"
    if "pmc" in fmt:
        return "pmc"
    if "libretexts" in fmt:
        return "libretexts"
    if "html" in fmt:
        return "html"
    return "html"


def _licence_defaults(licence_class: str, title: str, url: str, num: int) -> tuple:
    attr = f"{title}. Source: {url}"
    if licence_class == "A":
        return (
            "CC-BY-4.0",
            "https://creativecommons.org/licenses/by/4.0/",
            False,
            False,
            attr,
        )
    if licence_class == "B":
        nc = True
        if num == 3:
            return (
                "CC-BY-NC-SA-3.0",
                "https://creativecommons.org/licenses/by-nc-sa/3.0/",
                nc,
                False,
                attr,
            )
        if num == 21:
            return (
                "CC-BY-NC-SA-2.0",
                "https://creativecommons.org/licenses/by-nc-sa/2.0/",
                nc,
                False,
                attr,
            )
        return (
            "CC-BY-NC-SA-4.0",
            "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            nc,
            False,
            attr,
        )
    if num == 45:
        return (
            "CC-BY-NC-ND-4.0",
            "https://creativecommons.org/licenses/by-nc-nd/4.0/",
            True,
            True,
            attr,
        )
    if "arxiv" in url:
        return (
            "LicenseRef-arXiv-1.0",
            "https://info.arxiv.org/help/license/index.html",
            False,
            False,
            attr,
        )
    return (
        "LicenseRef-AllRightsReserved",
        url,
        False,
        False,
        attr,
    )


if __name__ == "__main__":
    main()
