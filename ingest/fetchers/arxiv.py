from __future__ import annotations

import gzip
import io
import logging
import re
import tarfile
import tempfile
from pathlib import Path

from ingest.fetchers.base import polite_get
from ingest.fetchers.pdf import fetch_pdf_text

logger = logging.getLogger(__name__)

# New-style: 1234.5678 or 2101.00001v2; old-style: archive[/subclass]/YYMMNNN[vN]
_ARXIV_NEW = r"\d{4}\.\d{4,5}(?:v\d+)?"
_ARXIV_OLD = r"[a-z\-]+(?:\.[a-z\-]+)*/\d{7}(?:v\d+)?"
_ARXIV_ID = rf"(?:{_ARXIV_NEW}|{_ARXIV_OLD})"
ARXIV_URL = re.compile(rf"arxiv\.org/(?:abs|pdf)/({_ARXIV_ID})(?:\.pdf)?", re.IGNORECASE)
ARXIV_ID_ONLY = re.compile(rf"^{_ARXIV_ID}$", re.IGNORECASE)

MAX_TAR_BYTES = 200 * 1024 * 1024


def arxiv_id_from_url(url: str) -> str | None:
    m = ARXIV_URL.search(url)
    return m.group(1) if m else None


def is_valid_arxiv_id(arxiv_id: str) -> bool:
    return ARXIV_ID_ONLY.match(arxiv_id) is not None


def fetch_arxiv_markdown(url: str) -> str:
    aid = arxiv_id_from_url(url)
    if not aid:
        raise ValueError(f"Not an arXiv abs/pdf URL: {url}")
    src_url = f"https://arxiv.org/e-print/{aid}"
    resp = polite_get(src_url, timeout=120.0)
    content = resp.content
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _unpack_eprint(content, root)
        tex_files = list(root.rglob("*.tex"))
        pdf_files = list(root.rglob("*.pdf"))
        if tex_files:
            parts = []
            for tex in sorted(tex_files):
                parts.append(tex.read_text(encoding="utf-8", errors="replace"))
            return _latex_to_markdown("\n\n".join(parts))
        if pdf_files:
            data = pdf_files[0].read_bytes()
            try:
                text = _pdf_bytes_to_text(data)
            except Exception:
                text = ""
            if text.strip():
                return text
    logger.warning("No usable TeX for arXiv %s; falling back to PDF", aid)
    pdf_url = f"https://arxiv.org/pdf/{aid}.pdf"
    return fetch_pdf_text(pdf_url)


def _unpack_eprint(content: bytes, root: Path) -> None:
    if content[:4] == b"%PDF":
        (root / "paper.pdf").write_bytes(content)
        return
    if _looks_like_compressed_archive(content):
        if _try_extract_tar(content, root):
            return
        decompressed = _try_gunzip(content)
        if decompressed is not None:
            if decompressed[:4] == b"%PDF":
                (root / "paper.pdf").write_bytes(decompressed)
            else:
                (root / "main.tex").write_bytes(decompressed)
            return
    (root / "main.tex").write_bytes(content)


def _looks_like_compressed_archive(content: bytes) -> bool:
    return content[:2] == b"\x1f\x8b" or content[:6] == b"\xfd7zX\x5a\x00"


def _try_extract_tar(content: bytes, root: Path) -> bool:
    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as tf:
            _safe_extractall(tf, root)
    except (tarfile.TarError, ValueError):
        return False
    return True


def _try_gunzip(content: bytes) -> bytes | None:
    try:
        return gzip.decompress(content)
    except OSError:
        return None


def _safe_extractall(tf: tarfile.TarFile, dest: Path) -> None:
    dest = dest.resolve()
    total = 0
    members: list[tarfile.TarInfo] = []
    for member in tf.getmembers():
        member_path = Path(member.name)
        if member.islnk() or member.issym():
            raise ValueError(f"Unsafe link in tar: {member.name}")
        if member.name.startswith("/") or ".." in member_path.parts:
            raise ValueError(f"Unsafe path in tar: {member.name}")
        resolved = (dest / member_path).resolve()
        if not str(resolved).startswith(str(dest) + "/") and resolved != dest:
            raise ValueError(f"Unsafe path in tar: {member.name}")
        if member.isfile():
            total += member.size
            if total > MAX_TAR_BYTES:
                raise ValueError(f"Tar decompressed size exceeds {MAX_TAR_BYTES} bytes")
        members.append(member)
    tf.extractall(dest, members=members, filter="data")


def _pdf_bytes_to_text(data: bytes) -> str:
    from ingest.fetchers import pdf as pdf_mod

    text = pdf_mod._extract_pymupdf(data) or pdf_mod._extract_pypdf(data)
    return text or ""


def _latex_to_markdown(latex: str) -> str:
    """Best-effort LaTeX preservation: keep display math, strip preamble noise."""
    body = latex
    for env in ("documentclass", "usepackage", "begin{document}", "end{document}"):
        body = re.sub(rf"\\{env}(\[[^\]]*\])?(\{{[^}}]*\}})*", "", body)
    return f"```latex\n{body.strip()}\n```\n"
