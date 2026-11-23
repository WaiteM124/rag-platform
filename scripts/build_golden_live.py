#!/usr/bin/env python3
"""One-off builder: fetch sources and emit golden_live candidates (stdout JSON)."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
import httpx
import yaml

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
SOURCES = ROOT / "collections/complex-systems/sources.yaml"
NS = {"a": "http://www.w3.org/2005/Atom"}

ARXIV_RE = re.compile(r"arxiv\.org/abs/([^?#]+)")


def arxiv_id_from_url(url: str) -> str | None:
    m = ARXIV_RE.search(url)
    if not m:
        return None
    return m.group(1).rstrip("/")


def fetch_arxiv_abstract(arxiv_id: str) -> str | None:
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    r = httpx.get(url, timeout=60.0, follow_redirects=True)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    entry = root.find("a:entry", NS)
    if entry is None:
        return None
    summary = entry.find("a:summary", NS)
    return summary.text.strip().replace("\n", " ") if summary is not None and summary.text else None


def fetch_html_snippet(url: str, max_chars: int = 8000) -> str | None:
    r = httpx.get(
        url,
        timeout=60.0,
        follow_redirects=True,
        headers={"User-Agent": "rag-platform-golden-builder/1.0"},
    )
    if r.status_code >= 400:
        return None
    text = r.text
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars] if text else None


def fetch_source_text(source: dict) -> str | None:
    url = source["url"]
    fmt = source.get("format", "")
    aid = arxiv_id_from_url(url)
    if aid or fmt == "arxiv_src":
        aid = aid or url.split("/")[-1]
        return fetch_arxiv_abstract(aid)
    if fmt in ("libretexts", "html", "jats", "pmc"):
        return fetch_html_snippet(url)
    if fmt == "pdf":
        try:
            import fitz  # pymupdf

            r = httpx.get(url, timeout=90.0, follow_redirects=True)
            r.raise_for_status()
            doc = fitz.open(stream=r.content, filetype="pdf")
            parts = [page.get_text() for page in doc[:3]]
            return re.sub(r"\s+", " ", "\n".join(parts)).strip()[:12000]
        except Exception:
            return fetch_html_snippet(url)
    return fetch_html_snippet(url)


def main() -> int:
    data = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    picks = sys.argv[1:] if len(sys.argv) > 1 else [s["id"] for s in data["sources"]]
    by_id = {s["id"]: s for s in data["sources"]}
    for sid in picks:
        if sid not in by_id:
            print(json.dumps({"id": sid, "error": "unknown"}), flush=True)
            continue
        src = by_id[sid]
        try:
            text = fetch_source_text(src)
        except Exception as exc:
            print(json.dumps({"id": sid, "error": str(exc)}), flush=True)
            continue
        if not text or len(text) < 80:
            print(json.dumps({"id": sid, "error": "empty_or_short", "url": src["url"]}), flush=True)
            continue
        print(
            json.dumps(
                {
                    "source_id": sid,
                    "module": src["module"],
                    "title": src["title"],
                    "url": src["url"],
                    "text": text[:4000],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())