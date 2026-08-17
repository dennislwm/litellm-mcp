.PHONY: help setup status install test lint check-pins
SHELL := /bin/bash

help:
	@echo ""
	@echo "=== Targets ==="
	@echo "  help        Show this help"
	@echo "  setup       Install pipenv environment (dev deps included)"
	@echo "  status      Check local machine setup (pipenv installed, env present)"
	@echo "  install     Install/sync pipenv environment"
	@echo "  test        Run pytest against tests/"
	@echo "  lint        Run flake8 and mypy against app/"
	@echo "  check-pins  Fail if any Pipfile dependency is unpinned"
	@echo ""

setup:
	@source ./make.sh && setup_commands

status:
	@source ./make.sh && show_status

install:
	@source ./make.sh && check_pipenv && pipenv install --dev

test:
	@source ./make.sh && check_pipenv && pipenv run pytest tests/

lint:
	@source ./make.sh && check_pipenv && pipenv run flake8 app tests && pipenv run mypy app

check-pins:
	@source ./make.sh && check_pins
