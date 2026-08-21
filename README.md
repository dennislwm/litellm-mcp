# litellm-mcp

MCP server exposing [LiteLLM](https://github.com/BerriAI/litellm)'s multi-provider LLM gateway as tools callable over the Model Context Protocol, built on the official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).

Requires: [pipenv](https://pipenv.pypa.io/)

## Workflow

One-time `make setup` installs the pipenv environment; everything else
runs against it. Day to day: point the server at a running LiteLLM
Proxy and run it (below, `pipenv run mcp dev app/server.py` or `make
serve-http`); `make test`/`make lint`/`make check-pins` verify a
change before it ships. `make test-integration` also verifies
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
`streamable-http` instead (per ADR-07):

1. Generate a virtual key for the connecting client:

       make proxy-key-generate

   Copy the returned key into `local-proxy/.env` as
   `LITELLM_VIRTUAL_KEY`, then scope it (per ADR-05/ADR-08 -- each
   client's own key becomes its own outbound credential, so it needs
   its own `allowed_routes`/budget/rate-limit restrictions, set via
   `PROXY_KEY_ALLOWED_ROUTES` in `local-proxy/.env`):

       make proxy-key-update

2. Run the server, using the server's own credential (its
   `LITELLM_PROXY_API_KEY`, distinct from the client key from step 1):

       export LITELLM_PROXY_API_BASE=http://localhost:4000
       export LITELLM_PROXY_API_KEY=<the server's own key>
       make serve-http

   `MCP_HOST`/`MCP_PORT` are optional, defaulting to `127.0.0.1:8000`.

3. Register it with Claude Code:

       claude mcp add --transport http litellm-mcp http://127.0.0.1:8000 \
         --header "Authorization: Bearer <the virtual key from step 1>"

4. Run a first query in Claude Code, e.g. "check the LiteLLM spend logs
   for today" -- this exercises `get_spend_logs`, verifying the key
   from step 1 against `/key/info` (ADR-06) before forwarding it as the
   outbound credential (ADR-08).

Over `streamable-http`, per ADR-06, the server verifies each
connecting client's bearer token against LiteLLM's own `/key/info`
before any tool executes. `stdio` has no such check -- no enforcement
point exists for that transport.

Per ADR-08, each client's own verified key is then forwarded as the
credential for its own outbound LiteLLM calls, with ADR-05's
`allowed_routes`/budget/rate-limit scoping applying per client. `stdio`
has no verified caller to forward, so it still uses the server's own
`LITELLM_PROXY_API_KEY` for every call.

## Maintainer setup

    make setup
    make test
    make test-integration
    make lint
    make check-pins
