import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("LITELLM_PROXY_API_BASE", "http://localhost:4000")
os.environ.setdefault("LITELLM_PROXY_API_KEY", "sk-test")

from app.server import _get_spend_logs  # noqa: E402


@patch("app.server.httpx.get")
def test_get_spend_logs_calls_proxy_with_bearer_auth(
    mock_get: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = [{"spend": 1.23}]
    mock_get.return_value = mock_response

    result = _get_spend_logs("2024-01-01", "2024-01-02")

    mock_get.assert_called_once_with(
        "http://localhost:4000/spend/logs",
        params={"start_date": "2024-01-01", "end_date": "2024-01-02"},
        headers={"Authorization": "Bearer sk-test"},
        timeout=30.0,
    )
    mock_response.raise_for_status.assert_called_once()
    assert result == [{"spend": 1.23}]
