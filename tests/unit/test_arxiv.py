from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingest.fetchers import arxiv


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://arxiv.org/abs/1112.1440", "1112.1440"),
        ("https://arxiv.org/abs/2101.00001v2", "2101.00001v2"),
        ("https://arxiv.org/pdf/1101.2899.pdf", "1101.2899"),
        ("https://arxiv.org/abs/nlin/0307015", "nlin/0307015"),
        ("https://arxiv.org/abs/cond-mat/0106096", "cond-mat/0106096"),
        ("https://arxiv.org/pdf/nlin/0204062.pdf", "nlin/0204062"),
    ],
)
def test_arxiv_id_from_url(url: str, expected: str) -> None:
    assert arxiv.arxiv_id_from_url(url) == expected
    assert arxiv.is_valid_arxiv_id(expected)


def test_arxiv_id_from_url_rejects_non_arxiv() -> None:
    assert arxiv.arxiv_id_from_url("https://example.com/abs/1112.1440") is None


def test_arxiv_old_style_not_truncated() -> None:
    url = "https://arxiv.org/abs/nlin/0307015"
    aid = arxiv.arxiv_id_from_url(url)
    assert aid == "nlin/0307015"
    assert aid != "nlin"


def _make_tex_tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        data = b"\\begin{document}hello\\end{document}"
        info = tarfile.TarInfo("main.tex")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_fetch_arxiv_markdown_tex_tar() -> None:
    payload = _make_tex_tar()
    mock_resp = MagicMock()
    mock_resp.content = payload
    with patch("ingest.fetchers.arxiv.polite_get", return_value=mock_resp):
        md = arxiv.fetch_arxiv_markdown("https://arxiv.org/abs/1112.1440")
    assert "hello" in md


def test_fetch_arxiv_markdown_gzipped_tex() -> None:
    tex = b"\\documentclass{article}\\begin{document}gzip tex\\end{document}"
    payload = gzip.compress(tex)
    mock_resp = MagicMock()
    mock_resp.content = payload
    with patch("ingest.fetchers.arxiv.polite_get", return_value=mock_resp):
        md = arxiv.fetch_arxiv_markdown("https://arxiv.org/abs/nlin/0307015")
    assert "gzip tex" in md


def test_fetch_arxiv_markdown_pdf_fallback() -> None:
    mock_resp = MagicMock()
    mock_resp.content = b"%PDF-1.4 minimal"
    with (
        patch("ingest.fetchers.arxiv.polite_get", return_value=mock_resp),
        patch(
            "ingest.fetchers.arxiv.fetch_pdf_text",
            return_value="fallback pdf text",
        ) as pdf_fetch,
    ):
        md = arxiv.fetch_arxiv_markdown("https://arxiv.org/abs/nlin/0303020")
    assert md == "fallback pdf text"
    pdf_fetch.assert_called_once_with("https://arxiv.org/pdf/nlin/0303020.pdf")


def test_safe_extractall_rejects_dotdot(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        data = b"evil"
        info = tarfile.TarInfo("../evil.tex")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    buf.seek(0)
    with (
        tarfile.open(fileobj=buf, mode="r:gz") as tf,
        pytest.raises(ValueError, match="Unsafe path"),
    ):
        arxiv._safe_extractall(tf, tmp_path)


def test_safe_extractall_enforces_size_cap(tmp_path: Path) -> None:
    tf = MagicMock()
    member = tarfile.TarInfo("big.tex")
    member.size = arxiv.MAX_TAR_BYTES + 1
    tf.getmembers.return_value = [member]
    with pytest.raises(ValueError, match="exceeds"):
        arxiv._safe_extractall(tf, tmp_path)


def test_complex_systems_arxiv_urls_parse() -> None:
    from ingest.licence import load_sources

    path = Path("collections/complex-systems/sources.yaml")
    records = load_sources(str(path))
    arxiv_urls = [r.url for r in records if "arxiv.org" in r.url]
    assert arxiv_urls, "expected arXiv sources in complex-systems config"
    for url in arxiv_urls:
        aid = arxiv.arxiv_id_from_url(url)
        assert aid is not None, url
        assert arxiv.is_valid_arxiv_id(aid), url
