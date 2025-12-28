.PHONY: help ruff ruff-fix mypy test

help:
	@echo "Available targets:"
	@echo "  ruff      - Run ruff linter on src/"
	@echo "  ruff-fix  - Run ruff linter with auto-fix on src/"
	@echo "  mypy      - Run mypy type checker on src/"
	@echo "  test      - Run ruff and mypy"

ruff:
	uv run ruff check src/

ruff-fix:
	uv run ruff check --fix src/

mypy:
	uv run mypy src/

test: ruff mypy
