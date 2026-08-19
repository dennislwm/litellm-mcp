import os

from app.server import _get_spend_logs


def test_get_spend_logs_reaches_ephemeral_proxy() -> None:
    """Smoke test against a real LiteLLM Proxy (make test-integration).

    No mocking -- proves the MCP<->LiteLLM plumbing actually works, not
    just that our code calls httpx2 correctly. Reads live env vars set
    by run_test_integration (make.sh), not the mocked ones test_server.py
    sets at import time.
    """
    assert "LITELLM_PROXY_API_BASE" in os.environ, (
        "run via `make test-integration`, which starts an ephemeral "
        "proxy and sets LITELLM_PROXY_API_BASE/LITELLM_PROXY_API_KEY"
    )

    result = _get_spend_logs("2026-01-01", "2026-01-02")

    assert result == []
