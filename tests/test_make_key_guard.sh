#!/usr/bin/env bash
# Self-check for make.sh's proxy_key_update empty-allowed_routes guard
# (REQ-007 / ADR-05). No network/podman needed: the guard must return
# before curl is ever reached.
set -uo pipefail

cd "$(dirname "$0")/.."
source make.sh

PROXY_KEY_ALLOWED_ROUTES='[]'
if proxy_key_update > /dev/null 2>&1; then
  echo "[FAIL] proxy_key_update did not refuse an empty allowed_routes"
  exit 1
fi
echo "[OK]   proxy_key_update refuses an empty allowed_routes"
