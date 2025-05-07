.PHONY: clean-pyc
clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

.PHONY: clean-build
clean-build: ## remove build artifacts
	rm -rf build dist .eggs
	find . -name '*.egg-info' -exec rm -rf  {} +
	find . -name '*.egg' -exec rm -f {} +

.PHONY: clean-test
clean-test: ## remove test and coverage artifacts
	rm -rf .coverage .mypy_cache .pytest_cache .tox

.PHONY: clean
clean: clean-pyc clean-build clean-test ## remove all build, test, coverage and Python artifacts

.PHONY: install
install: clean ## install the package to the active Python's site-packages
	poetry install -v --with dev
	poetry run pre-commit install

.PHONY: lint
lint: ## run linters, checks, formatters
	poetry run pre-commit run --all-files

.PHONY: test
test: ## Run tests
	poetry run pytest -vv


.PHONY: coverage
coverage: ## check code coverage quickly with the default Python
	poetry run coverage erase
	poetry run coverage run --branch --source=monitor -m pytest --junitxml=ut-report.xml tests/
