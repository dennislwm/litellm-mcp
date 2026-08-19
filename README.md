# litellm-mcp

MCP server exposing [LiteLLM](https://github.com/BerriAI/litellm)'s multi-provider LLM gateway as tools callable over the Model Context Protocol, built on the official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).

Requires: [pipenv](https://pipenv.pypa.io/)

## Workflow

One-time `make setup` installs the pipenv environment; everything else
runs against it. Day to day: point the server at a running LiteLLM
Proxy and run it (below); `make test`/`make lint`/`make check-pins`
verify a change before it ships.

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

## Maintainer setup

    make setup
    make test
    make lint
    make check-pins
