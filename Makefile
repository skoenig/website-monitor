.PHONY: install lint test all clean help

.DEFAULT_GOAL := help

install: ## Install dependencies and set up pre-commit hooks
	poetry install -v --with dev
	poetry run pre-commit install

lint: ## Run linters, checks, formatters
	poetry run pre-commit run --all-files

test: ## Run tests
	poetry run pytest -vv

clean: ## Clean test, coverage and Python artifacts
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	rm -rf .coverage .pytest_cache .ruff_cache

.PHONY: coverage
coverage: ## Run tests with coverage and show report
	poetry run coverage run -m pytest -vv
	poetry run coverage report -m

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
