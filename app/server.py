import os
import re
from html.parser import HTMLParser

import httpx2
from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl
from mcp.types import ToolAnnotations


def _proxy_base() -> str:
    return os.environ["LITELLM_PROXY_API_BASE"].rstrip("/")


def _proxy_key() -> str:
    return os.environ["LITELLM_PROXY_API_KEY"]


class LiteLLMKeyVerifier(TokenVerifier):
    """Verifies an MCP client's bearer token against LiteLLM's own
    /key/info, per ADR-06 Option 1. Single-tenant scope only (see
    ADR-06's Decision Outcome): confirms the token is a valid LiteLLM
    key, but every verified caller still shares this process's one
    LITELLM_PROXY_API_KEY for outbound calls."""

    async def verify_token(self, token: str) -> AccessToken | None:
        response = httpx2.get(
            f"{_proxy_base()}/key/info",
            params={"key": token},
            headers={"Authorization": f"Bearer {_proxy_key()}"},
            timeout=10.0,
        )
        if response.status_code != 200:
            return None
        info = response.json().get("info", response.json())
        return AccessToken(
            token=token,
            client_id=info.get("key_name") or token[:12],
            scopes=info.get("models") or [],
        )


def _build_mcp() -> MCPServer:
    if os.environ.get("MCP_TRANSPORT") != "streamable-http":
        # ponytail: auth is only ever enforced for streamable-http
        # transport (confirmed via SDK source, ADR-06 Decision
        # Drivers) -- wiring it for stdio would require issuer/
        # resource URLs with no enforcement point to apply to.
        return MCPServer("litellm-mcp")
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = os.environ.get("MCP_PORT", "8000")
    return MCPServer(
        "litellm-mcp",
        token_verifier=LiteLLMKeyVerifier(),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(_proxy_base()),
            resource_server_url=AnyHttpUrl(f"http://{host}:{port}"),
        ),
    )


mcp = _build_mcp()


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


@mcp.tool(
    annotations=ToolAnnotations(
        destructive_hint=True,
        read_only_hint=False,
        open_world_hint=True,
    )
)
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
    deliberately intends a write/destructive call. Per ADR-04's Option
    2, this tool's annotations mark it destructive/non-read-only/open-
    world -- a hint, not enforcement (see the allow_write gate above
    for the actual server-side guarantee).
    """
    return _call_litellm(
        method, path, params=params, json=json, allow_write=allow_write
    )


class _ConfigTableParser(HTMLParser):
    """Collects every <table>'s rows as lists of cell texts."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif (
            tag in ("td", "th")
            and self._cell is not None
            and self._row is not None
        ):
            self._row.append("".join(self._cell).strip())
            self._cell = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


_CONFIG_DOCS_URL = "https://docs.litellm.ai/docs/proxy/config_settings"

_SOURCE_FALLBACK_TARGETS = {
    "general_settings": (
        "https://raw.githubusercontent.com/BerriAI/litellm/main/"
        "litellm/proxy/_types.py"
    ),
    "admin_ui_settings": (
        "https://raw.githubusercontent.com/BerriAI/litellm/main/litellm/"
        "proxy/ui_crud_endpoints/proxy_setting_endpoints.py"
    ),
}


def _search_config_docs(field: str) -> dict | None:
    response = httpx2.get(_CONFIG_DOCS_URL, timeout=30.0)
    response.raise_for_status()
    parser = _ConfigTableParser()
    parser.feed(response.text)
    for table in parser.tables:
        for row in table:
            if row and row[0] == field:
                return {"source": "docs", "url": _CONFIG_DOCS_URL, "row": row}
    return None


def _search_config_source(field: str) -> dict | None:
    # ponytail: regex scrape of Field(description=...) kwargs, depends on
    # the upstream file's current single-line field-declaration shape --
    # switch to ast.parse if BerriAI/litellm reformats these files.
    for sub_tree, url in _SOURCE_FALLBACK_TARGETS.items():
        response = httpx2.get(url, timeout=30.0)
        response.raise_for_status()
        match = re.search(
            rf'{re.escape(field)}\s*:.*?Field\([^)]*description\s*=\s*'
            r'"((?:[^"\\]|\\.)*)"',
            response.text,
            re.DOTALL,
        )
        if match:
            return {
                "source": "code",
                "sub_tree": sub_tree,
                "url": url,
                "field": field,
                "description": match.group(1),
            }
    return None


def _search_config_issues(field: str) -> list[dict]:
    try:
        response = httpx2.get(
            "https://api.github.com/search/issues",
            params={"q": f"{field} repo:BerriAI/litellm"},
            timeout=10.0,
        )
        response.raise_for_status()
        return [
            {"title": item["title"], "url": item["html_url"]}
            for item in response.json().get("items", [])[:5]
        ]
    except Exception:
        return []


def _search_config(field: str) -> dict:
    result = _search_config_docs(field)
    if result is None:
        result = _search_config_source(field)
    if result is None:
        result = {"source": "not_found", "field": field}
    result["known_issues"] = _search_config_issues(field)
    return result


@mcp.tool()
def search_config(field: str) -> dict:
    """Look up a LiteLLM config.yaml or Admin UI setting (per ADR-03).

    Tries docs.litellm.ai's config reference page first (all four
    config.yaml sub-trees); on no match, falls back to LiteLLM's own
    source code, scoped to general_settings and Admin UI settings only
    (litellm_settings/router_settings have no single canonical source
    target yet). Always appends a best-effort "known_issues" annex from
    GitHub, non-blocking. field: the exact config.yaml/Admin UI setting
    name (e.g. "database_url").
    """
    return _search_config(field)


def _run() -> None:
    """Entry point (per ADR-07). MCP_TRANSPORT selects stdio (default)
    or streamable-http; MCP_HOST/MCP_PORT only apply to the latter."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8000")),
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    _run()
