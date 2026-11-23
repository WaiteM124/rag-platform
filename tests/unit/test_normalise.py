from ingest.chunking import content_hash
from ingest.normalise import normalise_text


def test_normalise_strips_nul_bytes() -> None:
    raw = "Intro\x00section\x00tail"
    cleaned = normalise_text(raw)
    assert "\x00" not in cleaned
    assert cleaned == "Introsectiontail"


def test_normalise_preserves_newline_and_tab() -> None:
    raw = "line one\n\tindented\x00gone"
    cleaned = normalise_text(raw)
    assert cleaned == "line one\n\tindentedgone"


def test_normalise_strips_other_control_chars() -> None:
    raw = "a\x01b\x02c\nd"
    cleaned = normalise_text(raw)
    assert cleaned == "abc\nd"


def test_normalise_idempotent_and_affects_hash() -> None:
    raw = "same\x00content"
    once = normalise_text(raw)
    twice = normalise_text(once)
    assert once == twice
    assert content_hash(raw) != content_hash(once)
