.PHONY: install lint test all clean help

.DEFAULT_GOAL := help

install: ## Install dependencies and set up pre-commit hooks
	poetry install -v --with dev
	poetry run pre-commit install

lint: ## Run linters, checks, formatters
	poetry run pre-commit run --all-files

test: ## Run tests
	poetry run pytest -vv

clean: clean-pyc clean-build clean-test ## Remove all build, test, coverage and Python artifacts

.PHONY: clean-pyc
clean-pyc: ## Remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

.PHONY: clean-build
clean-build: ## Remove build artifacts
	rm -rf build dist .eggs
	find . -name '*.egg-info' -exec rm -rf  {} +
	find . -name '*.egg' -exec rm -f {} +

.PHONY: clean-test
clean-test: ## Remove test and coverage artifacts
	rm -rf .coverage .mypy_cache .pytest_cache .tox


.PHONY: coverage
coverage: ## Check code coverage quickly with the default Python
	poetry run coverage erase
	poetry run coverage run --branch --source=monitor -m pytest --junitxml=ut-report.xml tests/

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
