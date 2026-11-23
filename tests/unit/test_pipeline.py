from ingest.pipeline import IngestSummary


def test_ingest_summary_exit_code_all_ok() -> None:
    s = IngestSummary(ok=10, unchanged=5, failed=0, chunks_added=100, db_chunks=500)
    assert s.exit_code() == 0


def test_ingest_summary_exit_code_partial_failure() -> None:
    s = IngestSummary(ok=8, unchanged=0, failed=2, chunks_added=50, db_chunks=200)
    assert s.exit_code() == 0


def test_ingest_summary_exit_code_majority_failed() -> None:
    s = IngestSummary(ok=2, unchanged=0, failed=3, chunks_added=10, db_chunks=100)
    assert s.exit_code() == 1


def test_ingest_summary_exit_code_all_failed() -> None:
    s = IngestSummary(ok=0, unchanged=0, failed=5, failed_ids=["a", "b"])
    assert s.exit_code() == 1


def test_ingest_summary_exit_code_zero_chunks_added_and_db_empty() -> None:
    s = IngestSummary(ok=5, unchanged=40, failed=0, chunks_added=0, db_chunks=0)
    assert s.exit_code() == 1
