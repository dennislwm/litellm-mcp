import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("LITELLM_PROXY_API_BASE", "http://localhost:4000")
os.environ.setdefault("LITELLM_PROXY_API_KEY", "sk-test")

from app.server import (  # noqa: E402
    LiteLLMKeyVerifier,
    WriteNotAllowedError,
    _build_mcp,
    _call_litellm,
    _get_spend_logs,
    _run,
    _search_config,
    _search_config_docs,
    _search_config_source,
    mcp,
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


@patch("app.server.httpx2.get")
def test_get_spend_logs_forwards_caller_token_when_authenticated(
    mock_get: MagicMock,
) -> None:
    from mcp.server.auth.middleware.auth_context import auth_context_var
    from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
    from mcp.server.auth.provider import AccessToken as SDKAccessToken

    mock_response = MagicMock()
    mock_response.json.return_value = [{"spend": 1.23}]
    mock_get.return_value = mock_response
    caller_token = SDKAccessToken(
        token="sk-caller", client_id="alice", scopes=[]
    )
    reset_token = auth_context_var.set(AuthenticatedUser(caller_token))
    try:
        _get_spend_logs("2024-01-01", "2024-01-02")
    finally:
        auth_context_var.reset(reset_token)

    mock_get.assert_called_once_with(
        "http://localhost:4000/spend/logs",
        params={"start_date": "2024-01-01", "end_date": "2024-01-02"},
        headers={"Authorization": "Bearer sk-caller"},
        timeout=30.0,
    )


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


@pytest.mark.anyio
async def test_call_litellm_carries_write_annotations() -> None:
    tools = await mcp.list_tools()
    call_litellm_tool = next(t for t in tools if t.name == "call_litellm")

    assert call_litellm_tool.annotations.destructive_hint is True
    assert call_litellm_tool.annotations.read_only_hint is False
    assert call_litellm_tool.annotations.open_world_hint is True


@patch("app.server.mcp.run")
@patch.dict(os.environ, {}, clear=False)
def test_run_defaults_to_stdio(mock_run: MagicMock) -> None:
    os.environ.pop("MCP_TRANSPORT", None)

    _run()

    mock_run.assert_called_once_with(transport="stdio")


@patch("app.server.mcp.run")
@patch.dict(
    os.environ,
    {
        "MCP_TRANSPORT": "streamable-http",
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": "9000",
    },
)
def test_run_streamable_http_reads_host_and_port(mock_run: MagicMock) -> None:
    _run()

    mock_run.assert_called_once_with(
        transport="streamable-http", host="0.0.0.0", port=9000
    )


@patch("app.server.mcp.run")
@patch.dict(os.environ, {"MCP_TRANSPORT": "streamable-http"}, clear=False)
def test_run_streamable_http_defaults_host_and_port(
    mock_run: MagicMock,
) -> None:
    os.environ.pop("MCP_HOST", None)
    os.environ.pop("MCP_PORT", None)

    _run()

    mock_run.assert_called_once_with(
        transport="streamable-http", host="127.0.0.1", port=8000
    )


@pytest.mark.anyio
@patch("app.server.httpx2.get")
async def test_key_verifier_accepts_valid_key(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "key_name": "alice",
        "models": ["gpt-4"],
    }
    mock_get.return_value = mock_response

    token = await LiteLLMKeyVerifier().verify_token("sk-alice")

    mock_get.assert_called_once_with(
        "http://localhost:4000/key/info",
        params={"key": "sk-alice"},
        headers={"Authorization": "Bearer sk-test"},
        timeout=10.0,
    )
    assert token.token == "sk-alice"
    assert token.client_id == "alice"
    assert token.scopes == ["gpt-4"]


@pytest.mark.anyio
@patch("app.server.httpx2.get")
async def test_key_verifier_rejects_invalid_key(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    assert await LiteLLMKeyVerifier().verify_token("sk-bad") is None


@patch.dict(os.environ, {}, clear=False)
def test_build_mcp_skips_auth_for_stdio() -> None:
    os.environ.pop("MCP_TRANSPORT", None)

    server = _build_mcp()

    assert server._token_verifier is None


@patch.dict(os.environ, {"MCP_TRANSPORT": "streamable-http"}, clear=False)
def test_build_mcp_wires_token_verifier_for_streamable_http() -> None:
    server = _build_mcp()

    assert isinstance(server._token_verifier, LiteLLMKeyVerifier)
    issuer = str(server.settings.auth.issuer_url).rstrip("/")
    assert issuer == "http://localhost:4000"
