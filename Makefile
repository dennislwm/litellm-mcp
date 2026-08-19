.PHONY: help setup status install test lint check-pins \
	proxy-init proxy-up proxy-down proxy-status proxy-logs \
	proxy-key-update proxy-key-status proxy-clean
SHELL := /bin/bash

help:
	@echo ""
	@echo "=== Targets ==="
	@echo "  help              Show this help"
	@echo "  setup             Install pipenv environment (dev deps included)"
	@echo "  status            Check local machine setup (pipenv installed, env present)"
	@echo "  install           Install/sync pipenv environment"
	@echo "  test              Run pytest against tests/"
	@echo "  lint              Run flake8 and mypy against app/"
	@echo "  check-pins        Fail if any Pipfile dependency is unpinned"
	@echo "  proxy-init        Initialize and start the local proxy's container machine"
	@echo "  proxy-up          Start a local LiteLLM Proxy via container compose"
	@echo "  proxy-down        Stop the local LiteLLM Proxy"
	@echo "  proxy-status      Show local proxy container status"
	@echo "  proxy-logs        Show local proxy logs"
	@echo "  proxy-key-update  Apply budget/rate-limit/model/allowed-route restrictions to the local proxy's virtual key"
	@echo "  proxy-key-status  Show current enforcement values for the local proxy's virtual key"
	@echo "  proxy-clean       Stop and remove local proxy containers (prompts to delete volumes)"
	@echo ""

setup:
	@bash make.sh setup_commands

status:
	@bash make.sh show_status

install:
	@bash make.sh install_deps

test:
	@bash make.sh run_test

lint:
	@bash make.sh run_lint

check-pins:
	@bash make.sh check_pins

proxy-init:
	@bash make.sh proxy_init

proxy-up:
	@bash make.sh proxy_up

proxy-down:
	@bash make.sh proxy_down

proxy-status:
	@bash make.sh proxy_status

proxy-logs:
	@bash make.sh proxy_logs

proxy-key-update:
	@bash make.sh proxy_key_update

proxy-key-status:
	@bash make.sh proxy_key_status

proxy-clean:
	@bash make.sh proxy_clean
