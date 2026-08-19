#!/usr/bin/env bash
set -euo pipefail

CONTAINER_CMD="${CONTAINER_CMD:-podman}"
PROXY_DIR="local-proxy"
PROXY_IMAGE="litellm/litellm:main-stable"
PROXY_COMPOSE="${PROXY_DIR}/compose.yaml"
PROXY_SERVICE="litellm"

check_pipenv() {
  command -v pipenv > /dev/null 2>&1 || { echo "[ERROR][check_pipenv]: pipenv not installed."; return 1; }
  echo "[OK]   pipenv found ($(pipenv --version 2>&1))"
}

setup_pipenv() {
  if pipenv --venv > /dev/null 2>&1; then
    echo "[SKIP] pipenv environment already set up"
  else
    pipenv install --dev
    echo "[OK]   pipenv environment installed"
  fi
}

check_pins() {
  local unpinned
  unpinned=$(grep -nE '=\s*"\*"' Pipfile || true)
  if [[ -n "$unpinned" ]]; then
    echo "[ERROR][check_pins]: unpinned dependencies in Pipfile:"
    echo "$unpinned"
    return 1
  fi
  echo "[OK]   all Pipfile dependencies are pinned"
}

show_status() {
  echo "=== Status ==="
  check_pipenv
  echo "=============="
}

setup_commands() {
  echo "=== Setup ==="
  check_pipenv
  setup_pipenv
  echo "============="
}

install_deps() {
  check_pipenv
  pipenv install --dev
}

run_test() {
  check_pipenv
  pipenv run pytest tests/
}

run_lint() {
  check_pipenv
  pipenv run flake8 app tests
  pipenv run mypy app
}

_proxy_compose() {
  ${CONTAINER_CMD} compose -f "${PROXY_COMPOSE}" "$@"
}

proxy_init() {
  if ${CONTAINER_CMD} machine list --format '{{.Running}}' 2>/dev/null | grep -q 'true'; then
    echo "Podman machine is already running"
  else
    ${CONTAINER_CMD} machine init
    ${CONTAINER_CMD} machine start
  fi
}

proxy_up() {
  if _proxy_compose ps --quiet 2>/dev/null | grep -q .; then
    echo "Already running: http://localhost:4000/ui"
  else
    (cd "${PROXY_DIR}" && ${CONTAINER_CMD} compose -f compose.yaml up -d)
    echo "Proxy available at: http://localhost:4000/ui"
  fi
  echo ""
  echo "export LITELLM_PROXY_API_BASE=http://localhost:4000"
  echo "export LITELLM_PROXY_API_KEY=\${LITELLM_MASTER_KEY}"
}

proxy_down() {
  (cd "${PROXY_DIR}" && ${CONTAINER_CMD} compose -f compose.yaml down)
}

proxy_status() {
  _proxy_compose ps
}

proxy_logs() {
  _proxy_compose logs "${PROXY_SERVICE}"
}

proxy_key_status() {
  set -a; source "${PROXY_DIR}/.env"; set +a
  curl -s -G http://localhost:4000/key/info \
    --data-urlencode "key=${LITELLM_VIRTUAL_KEY}" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | jq .
}

proxy_key_update() {
  set -a; source "${PROXY_DIR}/.env"; set +a
  curl -s -X POST http://localhost:4000/key/update \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    -d "{
      \"key\": \"${LITELLM_VIRTUAL_KEY}\",
      \"max_budget\": 5.00,
      \"budget_duration\": \"30d\",
      \"tpm_limit\": 100000,
      \"rpm_limit\": 60,
      \"models\": [\"gpt-4o-mini\"]
    }" | jq .
}

proxy_clean() {
  echo ""
  echo "WARNING: Deleting volumes will permanently destroy all Postgres and Redis data"
  echo "         (users, keys, spend history)."
  echo -n "Delete volumes? [y/N] "
  read -r answer
  if [[ "$(echo "$answer" | tr '[:upper:]' '[:lower:]')" == "y" ]]; then
    (cd "${PROXY_DIR}" && ${CONTAINER_CMD} compose -f compose.yaml down --remove-orphans --volumes 2>/dev/null || true)
    echo "Volumes deleted."
  else
    (cd "${PROXY_DIR}" && ${CONTAINER_CMD} compose -f compose.yaml down --remove-orphans 2>/dev/null || true)
    echo "Volumes kept."
  fi
  ${CONTAINER_CMD} ps -a --filter "ancestor=${PROXY_IMAGE}" --format '{{.ID}}' \
    | xargs -r ${CONTAINER_CMD} rm -f
}

"$@"
