# litellm-mcp

MCP server exposing [LiteLLM](https://github.com/BerriAI/litellm)'s multi-provider LLM gateway as tools callable over the Model Context Protocol, built on the official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).

Requires: [pipenv](https://pipenv.pypa.io/)

## Setup

    make setup

## Usage

    make test
    make lint
    make check-pins

## Running the server

Requires: a reachable [LiteLLM Proxy](https://docs.litellm.ai/docs/proxy/quick_start) instance.

Set the proxy connection as environment variables, then run the server over stdio:

    export LITELLM_PROXY_API_BASE=http://localhost:4000
    export LITELLM_PROXY_API_KEY=sk-1234
    pipenv run mcp dev app/server.py
