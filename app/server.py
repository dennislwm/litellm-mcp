import os

import httpx2
from mcp.server import MCPServer

mcp = MCPServer("litellm-mcp")


def _proxy_base() -> str:
    return os.environ["LITELLM_PROXY_API_BASE"].rstrip("/")


def _proxy_key() -> str:
    return os.environ["LITELLM_PROXY_API_KEY"]


def _get_spend_logs(start_date: str, end_date: str) -> list[dict]:
    response = httpx2.get(
        f"{_proxy_base()}/spend/logs",
        params={"start_date": start_date, "end_date": end_date},
        headers={"Authorization": f"Bearer {_proxy_key()}"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_spend_logs(start_date: str, end_date: str) -> list[dict]:
    """Get LiteLLM Proxy spend logs for a date range (YYYY-MM-DD)."""
    return _get_spend_logs(start_date, end_date)


class WriteNotAllowedError(Exception):
    pass


def _call_litellm(
    method: str,
    path: str,
    params: dict | None = None,
    json: dict | None = None,
    allow_write: bool = False,
) -> dict | list:
    if method.upper() != "GET" and not allow_write:
        raise WriteNotAllowedError(
            f"{method} {path} is a write/destructive call; pass "
            "allow_write=True to confirm"
        )
    response = httpx2.request(
        method,
        f"{_proxy_base()}{path}",
        params=params,
        json=json,
        headers={"Authorization": f"Bearer {_proxy_key()}"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def call_litellm(
    method: str,
    path: str,
    params: dict | None = None,
    json: dict | None = None,
    allow_write: bool = False,
) -> dict | list:
    """Call any LiteLLM Proxy REST endpoint (per ADR-02).

    method: HTTP method (GET, POST, ...). path: endpoint path starting
    with "/" (e.g. "/guardrails/list"). params: query string params.
    json: request body for POST/PUT/PATCH. allow_write: must be True
    for any non-GET method, per ADR-04 -- confirms the caller
    deliberately intends a write/destructive call.
    """
    return _call_litellm(
        method, path, params=params, json=json, allow_write=allow_write
    )
