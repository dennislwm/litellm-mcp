import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("LITELLM_PROXY_API_BASE", "http://localhost:4000")
os.environ.setdefault("LITELLM_PROXY_API_KEY", "sk-test")

from app.server import (  # noqa: E402
    WriteNotAllowedError,
    _call_litellm,
    _get_spend_logs,
    _search_config,
    _search_config_docs,
    _search_config_source,
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


@patch("app.server.httpx2.get")
def test_search_config_docs_finds_field_in_table(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.text = (
        "<table><tr><td>database_url</td><td>string</td>"
        "<td>The URL for the database connection</td></tr></table>"
    )
    mock_get.return_value = mock_response

    result = _search_config_docs("database_url")

    assert result == {
        "source": "docs",
        "url": "https://docs.litellm.ai/docs/proxy/config_settings",
        "row": [
            "database_url",
            "string",
            "The URL for the database connection",
        ],
    }


@patch("app.server.httpx2.get")
def test_search_config_docs_returns_none_when_field_absent(
    mock_get: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.text = "<table><tr><td>other_field</td></tr></table>"
    mock_get.return_value = mock_response

    assert _search_config_docs("database_url") is None


@patch("app.server.httpx2.get")
def test_search_config_source_finds_field_description(
    mock_get: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.text = (
        'database_url: Optional[str] = Field(\n'
        '    default=None, description="The URL for the database '
        'connection"\n)'
    )
    mock_get.return_value = mock_response

    result = _search_config_source("database_url")

    assert result["source"] == "code"
    assert result["sub_tree"] == "general_settings"
    assert result["description"] == "The URL for the database connection"


@patch("app.server._search_config_issues", return_value=[])
@patch("app.server._search_config_source")
@patch("app.server._search_config_docs", return_value=None)
def test_search_config_falls_back_to_source_when_docs_miss(
    mock_docs: MagicMock,
    mock_source: MagicMock,
    mock_issues: MagicMock,
) -> None:
    mock_source.return_value = {"source": "code", "field": "database_url"}

    result = _search_config("database_url")

    mock_docs.assert_called_once_with("database_url")
    mock_source.assert_called_once_with("database_url")
    assert result == {
        "source": "code",
        "field": "database_url",
        "known_issues": [],
    }


@patch("app.server._search_config_issues", return_value=[])
@patch("app.server._search_config_source")
@patch("app.server._search_config_docs", return_value=None)
def test_search_config_reports_not_found(
    mock_docs: MagicMock,
    mock_source: MagicMock,
    mock_issues: MagicMock,
) -> None:
    mock_source.return_value = None

    result = _search_config("nonexistent_field")

    assert result == {
        "source": "not_found",
        "field": "nonexistent_field",
        "known_issues": [],
    }


@patch("app.server.httpx2.get", side_effect=RuntimeError("network down"))
def test_search_config_issues_annex_fails_open(mock_get: MagicMock) -> None:
    from app.server import _search_config_issues

    assert _search_config_issues("database_url") == []
