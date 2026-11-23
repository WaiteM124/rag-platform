from unittest.mock import patch

from app.core.answer import AnswerEngine
from app.core.retrieval import RetrievedChunk


@patch(
    "app.core.answer.converse",
    return_value=(
        "I do not know based on the provided context.",
        {"input_tokens": 5, "output_tokens": 3},
    ),
)
def test_abstention_without_citation_not_counted_against_validity(mock_converse):
    chunk = RetrievedChunk(
        chunk_id=1,
        source_id="cs-018",
        text="Early warning signals.",
        score=1.0,
        rank=1,
        licence_class="A",
        attribution_text="Dakos et al.",
        source_url="https://example.com",
        title="Early warnings",
    )

    with patch.object(AnswerEngine, "__init__", lambda self, dsn, price_path=None: None):
        engine = AnswerEngine.__new__(AnswerEngine)
        from app.core.composer import LicenceComposer
        from app.core.cost import load_price_cards

        engine.composer = LicenceComposer()
        engine.prices = load_price_cards()
        engine.retriever = type(
            "R",
            (),
            {
                "retrieve": lambda *a, **k: [chunk],
                "_last_embed_input_tokens": 4,
                "_last_embed_model_id": "amazon.titan-embed-text-v2:0",
            },
        )()

    result = engine.answer("What is my tax bill?", collection="complex-systems")
    assert not result.citations_valid