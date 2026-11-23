from __future__ import annotations

import re
import tarfile
import tempfile
from pathlib import Path

from ingest.fetchers.base import polite_get

ARXIV_ABS = re.compile(r"arxiv\.org/abs/([^/?#]+)")


def arxiv_id_from_url(url: str) -> str | None:
    m = ARXIV_ABS.search(url)
    return m.group(1) if m else None


def fetch_arxiv_markdown(url: str) -> str:
    aid = arxiv_id_from_url(url)
    if not aid:
        raise ValueError(f"Not an arXiv abs URL: {url}")
    src_url = f"https://arxiv.org/e-print/{aid}"
    resp = polite_get(src_url, timeout=120.0)
    content = resp.content
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if content[:2] == b"\x1f\x8b" or content[:6] == b"\xfd\x37\x7a\x58\x5a\x00":
            (root / "source.tar.gz").write_bytes(content)
            with tarfile.open(root / "source.tar.gz") as tf:
                tf.extractall(root)  # noqa: S202
        else:
            (root / "main.tex").write_bytes(content)
        tex_files = list(root.rglob("*.tex"))
        if not tex_files:
            raise RuntimeError(f"No TeX found for arXiv {aid}")
        parts = []
        for tex in sorted(tex_files):
            parts.append(tex.read_text(encoding="utf-8", errors="replace"))
        return _latex_to_markdown("\n\n".join(parts))


def _latex_to_markdown(latex: str) -> str:
    """Best-effort LaTeX preservation: keep display math, strip preamble noise."""
    body = latex
    for env in ("documentclass", "usepackage", "begin{document}", "end{document}"):
        body = re.sub(rf"\\{env}(\[[^\]]*\])?(\{{[^}}]*\}})*", "", body)
    return f"```latex\n{body.strip()}\n```\n"
