from ingest.chunking import chunk_markdown


def test_chunking_preserves_display_math_block():
    md = """# Intro

Some text before.

$$
E = mc^2
$$

More after.
"""
    chunks = chunk_markdown(md, min_tokens=10, max_tokens=200, overlap=10)
    joined = " ".join(c.text for c in chunks)
    assert "E = mc^2" in joined


def test_chunk_ids_increment():
    md = "# A\n\n" + ("word " * 400) + "\n\n# B\n\n" + ("term " * 400)
    chunks = chunk_markdown(md, min_tokens=50, max_tokens=120, overlap=20)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index < chunks[-1].chunk_index
