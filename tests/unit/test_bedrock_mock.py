from unittest.mock import patch

from app.core.answer import AnswerEngine
from app.core.retrieval import RetrievedChunk


@patch(
    "app.core.answer.converse",
    return_value=("Answer with cite [1]", {"input_tokens": 10, "output_tokens": 5}),
)
def test_answer_engine_mocked(mock_converse):
    chunk = RetrievedChunk(
        chunk_id=1,
        source_id="cs-018",
        text="Early warning signals include autocorrelation.",
        score=1.0,
        rank=1,
        licence_class="A",
        attribution_text="Dakos et al.",
        source_url="https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0041010",
        title="Early warnings",
    )

    with patch.object(AnswerEngine, "__init__", lambda self, dsn, price_path=None: None):
        engine = AnswerEngine.__new__(AnswerEngine)
        from app.core.composer import LicenceComposer
        from app.core.cost import load_price_cards

        engine.composer = LicenceComposer()
        engine.prices = load_price_cards()
        engine.retriever = type("R", (), {"retrieve": lambda *a, **k: [chunk]})()

    result = engine.answer("test?", collection="complex-systems")
    assert "Answer" in result.answer
    assert result.citations_valid
    mock_converse.assert_called_once()
