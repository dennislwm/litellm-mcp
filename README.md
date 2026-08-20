# litellm-mcp

MCP server exposing [LiteLLM](https://github.com/BerriAI/litellm)'s multi-provider LLM gateway as tools callable over the Model Context Protocol, built on the official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).

Requires: [pipenv](https://pipenv.pypa.io/)

## Workflow

One-time `make setup` installs the pipenv environment; everything else
runs against it. Day to day: point the server at a running LiteLLM
Proxy and run it (below); `make test`/`make lint`/`make check-pins`
verify a change before it ships. `make test-integration` also verifies
against a real LiteLLM Proxy -- requires [Podman](https://podman.io/),
no setup needed otherwise: it stands up and tears down its own
ephemeral, isolated proxy automatically, separate from the one `make
proxy-up` manages.

## Running the server

Requires: a reachable [LiteLLM Proxy](https://docs.litellm.ai/docs/proxy/quick_start) instance.

No proxy handy? Start one locally:

Requires: [Podman](https://podman.io/)

1. Copy `local-proxy/.env.example` to `local-proxy/.env` and fill in `OPENAI_API_KEY`/`LITELLM_MASTER_KEY`
2. `make proxy-init` (one-time: starts the Podman machine)
3. `make proxy-up`

Also available: `make proxy-down`, `make proxy-status`, `make proxy-logs`, `make proxy-key-status`, `make proxy-key-update`, `make proxy-clean` (see `make help`).

Set the proxy connection as environment variables, then run the server over stdio:

    export LITELLM_PROXY_API_BASE=http://localhost:4000
    export LITELLM_PROXY_API_KEY=sk-1234
    pipenv run mcp dev app/server.py

Need a client that can't spawn a local subprocess? Run over
`streamable-http` instead (per ADR-07), using the entry point directly
rather than the `mcp dev` wrapper, which is stdio-only:

    export MCP_TRANSPORT=streamable-http
    export MCP_HOST=127.0.0.1   # optional, defaults shown
    export MCP_PORT=8000        # optional, defaults shown
    pipenv run python3 app/server.py

Over `streamable-http`, per ADR-06, the server also verifies each
connecting client's bearer token against LiteLLM's own `/key/info` --
the client must present a valid LiteLLM key as its MCP bearer token.
`stdio` has no such check (no enforcement point exists for that
transport). This is single-tenant scoped: every verified caller still
shares this process's one `LITELLM_PROXY_API_KEY` for outbound calls.

## Maintainer setup

    make setup
    make test
    make test-integration
    make lint
    make check-pins
