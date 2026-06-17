.PHONY: help install test test-verbose lint format typecheck check build clean

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-14s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install:  ## Install dev dependencies (uv sync --group dev)
	uv sync --group dev

test:  ## Run tests (quiet)
	uv run pytest tests/ -q

test-verbose:  ## Run tests (verbose)
	uv run pytest tests/ -v

lint:  ## Run ruff check
	uv run ruff check contree_mcp

format:  ## Run ruff format (auto-fix)
	uv run ruff format contree_mcp
	uv run ruff check contree_mcp --fix

typecheck:  ## Run mypy
	uv run mypy contree_mcp

check: lint typecheck test  ## Run lint + typecheck + tests (CI-equivalent)

build:  ## Build wheel + sdist
	uv build

clean:  ## Remove build artefacts and caches
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

docs-mintlify:
	$(MAKE) -C docs mintlify
