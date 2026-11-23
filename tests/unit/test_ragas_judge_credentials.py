import os
from unittest.mock import MagicMock, patch

from evals.metrics.ragas_judge import aws_credentials_available, ragas_available
from evals.run import main


@patch("evals.metrics.ragas_judge.boto3.Session")
def test_ragas_available_with_ecs_container_credentials_uri_only(mock_session):
    creds = MagicMock()
    mock_session.return_value.get_credentials.return_value = creds
    env = {"AWS_CONTAINER_CREDENTIALS_RELATIVE_URI": "/v2/credentials/01234567-89ab-cdef"}
    with patch.dict(os.environ, env, clear=True):
        assert aws_credentials_available() is True
        assert ragas_available() is True
    mock_session.assert_called_with()


@patch("evals.metrics.ragas_judge.boto3.Session")
def test_ragas_available_false_when_boto3_has_no_credentials(mock_session):
    mock_session.return_value.get_credentials.return_value = None
    with patch.dict(os.environ, {}, clear=True):
        assert aws_credentials_available() is False
        assert ragas_available() is False


@patch("evals.run.ragas_available", return_value=False)
def test_require_judge_exits_before_running_eval(mock_avail):
    code = main(["--collection", "complex-systems", "--require-judge"])
    assert code == 1
    mock_avail.assert_called()
