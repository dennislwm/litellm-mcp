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
