import os
from unittest.mock import MagicMock, patch

from ingest.config import db_dsn


def test_db_dsn_prefers_database_url():
    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql://a:b@h/d", "RAG_DB_SECRET_ARN": "x"},
        clear=False,
    ):
        dsn = db_dsn()
        assert dsn == "postgresql://a:b@h/d"


@patch("ingest.config.boto3.client")
def test_db_dsn_uses_rag_db_secret_arn(mock_boto_client):
    sm = MagicMock()
    sm.get_secret_value.return_value = {
        "SecretString": '{"username":"ecsuser","password":"secret"}',
    }
    mock_boto_client.return_value = sm
    env = {
        "RAG_DB_SECRET_ARN": "arn:aws:secretsmanager:eu-west-2:1:secret:mock",
        "RAG_DB_HOST": "rds.example",
        "RAG_DB_PORT": "5432",
        "RAG_DB_NAME": "ragplatform",
    }
    with patch.dict(os.environ, env, clear=True):
        dsn = db_dsn()
    assert "ecsuser" in dsn and "secret" in dsn and "rds.example" in dsn
