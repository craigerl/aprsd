.DEFAULT_GOAL := help

.PHONY: help dev run server changelog docs check fix test build upload docker clean clean-build clean-pyc clean-test clean-dev

help:	# Help for the Makefile
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Create a uv virtualenv and install aprsd with the dev extras
	uv venv
	uv pip install -e ".[dev]"
	uv run pre-commit install

run: dev ## Install the dev environment, then run the aprsd CLI
	uv run aprsd

server: dev ## Run aprsd server with debug logging in the dev environment
	uv run aprsd server --loglevel DEBUG

changelog: ## Regenerate ChangeLog.md from git history (requires node/npm)
	npm i -g auto-changelog
	auto-changelog -l false --sort-commits date -o ChangeLog.md

docs: ## Build the Sphinx documentation (HTML in docs/build)
	uv run tox -edocs

check: ## Run the linter and formatter checks
	uv run tox -elint
	uv run tox -efmt

fix: ## Auto-fix code formatting and linting errors
	uv run tox -efmt

test: dev ## Run all the tox tests
	uv run tox -p all

build: dev ## Make the build artifact prior to doing an upload
	uv pip install twine
	uv run python -m build
	uv run twine check dist/*

upload: build ## Upload a new version to PyPI
	uv run twine upload dist/*

docker: test ## Make a docker container tagged with hemna6969/aprsd:latest
	docker build -t hemna6969/aprsd:latest -f docker/Dockerfile docker

update-requirements: dev ## Update the requirements.txt file from requirements.in
	uv run pip-compile --resolver backtracking --annotation-style=line requirements.in

clean: clean-dev clean-test clean-build clean-pyc ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -fr {} +
	find . -name '*.pyo' -exec rm -fr {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache
	rm -fr .mypy_cache
	rm -fr .ruff_cache

clean-dev: ## remove the virtualenv
	rm -rf .venv
