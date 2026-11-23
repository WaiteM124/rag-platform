from __future__ import annotations

from ingest.fetchers import arxiv, html, pdf
from ingest.licence import SourceRecord


def fetch_source_markdown(source: SourceRecord) -> str:
    fmt = source.format.lower()
    if fmt in {"latex", "arxiv_src"}:
        return arxiv.fetch_arxiv_markdown(source.url)
    if fmt == "pdf":
        return pdf.fetch_pdf_text(source.url)
    if fmt in {"html", "jats", "pmc", "libretexts"}:
        return html.fetch_html_markdown(source.url)
    if "arxiv.org" in source.url:
        return arxiv.fetch_arxiv_markdown(source.url)
    if source.url.lower().endswith(".pdf"):
        return pdf.fetch_pdf_text(source.url)
    return html.fetch_html_markdown(source.url)
