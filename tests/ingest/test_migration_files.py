from pathlib import Path


def test_daily_spend_migration_present():
    migrations = Path(__file__).resolve().parents[2] / "ingest" / "migrations"
    assert (migrations / "002_daily_spend.sql").is_file()
