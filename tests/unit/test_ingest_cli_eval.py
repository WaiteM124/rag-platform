from unittest.mock import patch

from ingest.cli import main


@patch("evals.run.main", return_value=0)
def test_ingest_eval_forwards_to_eval_runner(mock_eval_main):
    code = main(
        [
            "eval",
            "--collection",
            "complex-systems",
            "--golden",
            "golden_live.jsonl",
            "--fast",
        ]
    )
    assert code == 0
    mock_eval_main.assert_called_once_with(
        [
            "--collection",
            "complex-systems",
            "--golden",
            "golden_live.jsonl",
            "--fast",
        ]
    )


@patch("evals.run.main", return_value=0)
def test_ingest_eval_uses_db_dsn_from_ingest_config_by_default(mock_eval_main):
    code = main(["eval", "--collection", "complex-systems"])
    assert code == 0
    argv = mock_eval_main.call_args[0][0]
    assert "--dsn" not in argv
    assert "--collection" in argv
