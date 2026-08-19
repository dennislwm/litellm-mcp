import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("LITELLM_PROXY_API_BASE", "http://localhost:4000")
os.environ.setdefault("LITELLM_PROXY_API_KEY", "sk-test")

from app.server import (  # noqa: E402
    WriteNotAllowedError,
    _call_litellm,
    _get_spend_logs,
)


@patch("app.server.httpx2.get")
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


@patch("app.server.httpx2.request")
def test_call_litellm_calls_proxy_with_bearer_auth(
    mock_request: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"guardrails": []}
    mock_request.return_value = mock_response

    result = _call_litellm("GET", "/guardrails/list")

    mock_request.assert_called_once_with(
        "GET",
        "http://localhost:4000/guardrails/list",
        params=None,
        json=None,
        headers={"Authorization": "Bearer sk-test"},
        timeout=30.0,
    )
    mock_response.raise_for_status.assert_called_once()
    assert result == {"guardrails": []}


def test_call_litellm_rejects_write_without_opt_in() -> None:
    with pytest.raises(WriteNotAllowedError):
        _call_litellm("POST", "/key/generate")


@patch("app.server.httpx2.request")
def test_call_litellm_allows_write_with_opt_in(
    mock_request: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "sk-new"}
    mock_request.return_value = mock_response

    result = _call_litellm("POST", "/key/generate", allow_write=True)

    mock_request.assert_called_once_with(
        "POST",
        "http://localhost:4000/key/generate",
        params=None,
        json=None,
        headers={"Authorization": "Bearer sk-test"},
        timeout=30.0,
    )
    assert result == {"key": "sk-new"}
