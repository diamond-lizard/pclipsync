.PHONY: help ruff ruff-fix mypy test test-integration test-unit

help:
	@echo "Available targets:"
	@echo "  ruff      - Run ruff linter on src/"
	@echo "  ruff-fix  - Run ruff linter with auto-fix on src/"
	@echo "  mypy      - Run mypy type checker on src/"
	@echo "  test      - Run ruff, mypy, and pytest"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-unit - Run unit tests only (excludes integration)"

ruff:
	uv run ruff check src/

ruff-fix:
	uv run ruff check --fix src/

mypy:
	uv run mypy src/

test: ruff mypy
	uv run pytest

test-integration:
	uv run pytest -m integration

test-unit:
	uv run pytest -m "not integration"
