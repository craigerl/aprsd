REQUIREMENTS_TXT ?= requirements.txt dev-requirements.txt
.DEFAULT_GOAL := help

.PHONY: dev docs server test
include Makefile.venv
Makefile.venv:
	curl \
			-o Makefile.fetched \
			-L "https://github.com/sio/Makefile.venv/raw/v2020.08.14/Makefile.venv"
	echo "5afbcf51a82f629cd65ff23185acde90ebe4dec889ef80bbdc12562fbd0b2611 *Makefile.fetched" \
			| sha256sum --check - \
	 		&& mv Makefile.fetched Makefile.venv

help:	# Help for the Makefile
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: venv  ## Create the virtualenv with all the requirements installed

docs: build
	cp README.rst docs/readme.rst
	cp Changelog docs/changelog.rst
	tox -edocs

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

test: dev  ## Run all the tox tests
	tox -p all

build: test  ## Make the build artifact prior to doing an upload
	$(VENV)/python3 setup.py sdist bdist_wheel
	$(VENV)/twine check dist/*

upload: build  ## Upload a new version of the plugin
	$(VENV)/twine upload dist/*

check: dev ## Code format check with tox and pep8
	tox -efmt-check
	tox -epep8

fix: dev ## fixes code formatting with gray
	tox -efmt

server: venv  ## Create the virtual environment and run aprsd server --loglevel DEBUG
	$(VENV)/aprsd server --loglevel DEBUG

docker: test  ## Make a docker container tagged with hemna6969/aprsd:latest
	docker build -t hemna6969/aprsd:latest -f docker/Dockerfile docker

docker-dev: test  ## Make a development docker container tagged with hemna6969/aprsd:master
	docker build -t hemna6969/aprsd:master -f docker/Dockerfile-dev docker

update-requirements: dev  ## Update the requirements.txt and dev-requirements.txt files
	$(VENV)/pip-compile requirements.in
	$(VENV)/pip-compile dev-requirements.in
