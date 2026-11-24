import time

from app.core.composer import (
    LicenceComposer,
    _exceeds_class_c_quote,
    validate_citations,
)
from app.core.retrieval import RetrievedChunk


def _chunk(licence_class: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=1,
        source_id="cs-001",
        text=text,
        score=1.0,
        rank=1,
        licence_class=licence_class,
        attribution_text="Author",
        source_url="https://example.com",
        title="Example",
    )


def test_class_c_long_quote_flagged():
    long_text = "x" * 400
    answer = "Summary " + long_text
    composer = LicenceComposer()
    _, ok = composer.apply_output_policy(answer, [_chunk("C", long_text)])
    assert ok is False


def test_class_c_short_quote_ok():
    text = "short overlap only"
    answer = "I summarise: " + text
    composer = LicenceComposer()
    _, ok = composer.apply_output_policy(answer, [_chunk("C", text * 20)])
    assert ok is True


def test_class_a_allows_full_quote():
    text = "Open content " * 5
    composer = LicenceComposer()
    _, ok = composer.apply_output_policy(text, [_chunk("A", text)])
    assert ok is True


def test_citation_validity():
    assert validate_citations("Claim [1] and [2]", 2)
    assert not validate_citations("Claim [3]", 2)


def test_exceeds_class_c_quote_fast_on_long_inputs():
    """Regression: old LCS was O(n²×m) and took tens of seconds in prod."""
    answer = ("early warning signals and variance " * 80) + ("UNIQUE_MARKER_" + "z" * 320)
    source = ("unrelated preamble about networks " * 100) + ("UNIQUE_MARKER_" + "z" * 320)
    t0 = time.perf_counter()
    assert _exceeds_class_c_quote(answer, source, 300) is True
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"overlap check too slow: {elapsed:.3f}s"


def test_exceeds_class_c_quote_no_match():
    assert _exceeds_class_c_quote("abc", "xyz" * 200, 300) is False
