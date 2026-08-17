function check_pipenv {
  command -v pipenv > /dev/null 2>&1 || { echo "[ERROR][$FUNCNAME]: pipenv not installed."; return 1; }
  echo "[OK]   pipenv found ($(pipenv --version 2>&1))"
}

function setup_pipenv {
  if pipenv --venv > /dev/null 2>&1; then
    echo "[SKIP] pipenv environment already set up"
  else
    pipenv install --dev
    echo "[OK]   pipenv environment installed"
  fi
}

function check_pins {
  local unpinned
  unpinned=$(grep -nE '=\s*"\*"' Pipfile)
  if [[ -n "$unpinned" ]]; then
    echo "[ERROR][$FUNCNAME]: unpinned dependencies in Pipfile:"
    echo "$unpinned"
    return 1
  fi
  echo "[OK]   all Pipfile dependencies are pinned"
}

function show_status {
  echo "=== Status ==="
  check_pipenv
  echo "=============="
}

function setup_commands {
  echo "=== Setup ==="
  check_pipenv
  setup_pipenv
  echo "============="
}
