.PHONY: help install fmt typecheck test test-unit test-integration clean

help:		## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies
	pip install -e ".[dev]"

fmt:		## Format code with black and ruff
	black .
	ruff check --fix .

typecheck:	## Run mypy type checking
	mypy apps/server --strict

test:		## Run all tests
	pytest

test-unit:	## Run unit tests only
	pytest -m "unit or not integration" apps/server/tests/unit

test-integration: ## Run integration tests only
	pytest -m integration apps/server/tests/integration

test-acceptance: ## Run acceptance tests for Phase 0
	pytest apps/server/tests/acceptance/test_phase_0.py -v

clean:		## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

check:		## Run all checks (format, type, test)
	$(MAKE) fmt
	$(MAKE) typecheck
	$(MAKE) test

dev-install:	## Set up development environment
	python -m pip install --upgrade pip
	$(MAKE) install
	@echo "Development environment ready! Run 'make check' to validate."
