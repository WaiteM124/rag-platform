from __future__ import annotations

import io

from ingest.fetchers.base import polite_get

try:
    import fitz  # pymupdf
except ImportError:  # pragma: no cover
    fitz = None

from pypdf import PdfReader


def fetch_pdf_text(url: str) -> str:
    resp = polite_get(url, timeout=120.0)
    data = resp.content
    text = _extract_pymupdf(data) or _extract_pypdf(data)
    if not text.strip():
        raise RuntimeError(f"No text extracted from PDF: {url}")
    return text


def _extract_pymupdf(data: bytes) -> str | None:
    if fitz is None:
        return None
    doc = fitz.open(stream=data, filetype="pdf")
    pages = [page.get_text("text") for page in doc]
    return "\n\n".join(pages)


def _extract_pypdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((p.extract_text() or "") for p in reader.pages)
