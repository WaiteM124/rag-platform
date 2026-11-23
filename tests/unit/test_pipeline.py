from ingest.pipeline import IngestSummary


def test_ingest_summary_exit_code_all_ok() -> None:
    s = IngestSummary(ok=10, unchanged=5, failed=0)
    assert s.exit_code() == 0


def test_ingest_summary_exit_code_partial_failure() -> None:
    s = IngestSummary(ok=8, unchanged=0, failed=2)
    assert s.exit_code() == 0


def test_ingest_summary_exit_code_majority_failed() -> None:
    s = IngestSummary(ok=2, unchanged=0, failed=3)
    assert s.exit_code() == 1


def test_ingest_summary_exit_code_all_failed() -> None:
    s = IngestSummary(ok=0, unchanged=0, failed=5, failed_ids=["a", "b"])
    assert s.exit_code() == 1
