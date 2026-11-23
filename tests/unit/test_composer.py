from app.core.composer import LicenceComposer, validate_citations
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


def test_class_a_allows_full_quote():
    text = "Open content " * 5
    composer = LicenceComposer()
    _, ok = composer.apply_output_policy(text, [_chunk("A", text)])
    assert ok is True


def test_citation_validity():
    assert validate_citations("Claim [1] and [2]", 2)
    assert not validate_citations("Claim [3]", 2)
