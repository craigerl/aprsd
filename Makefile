.PHONY: virtual install build-requirements black isort flake8

virtual: .venv/bin/pip # Creates an isolated python 3 environment

.venv/bin/pip:
	virtualenv -p /usr/bin/python3 .venv

install:
	.venv/bin/pip install -Ur requirements.txt

dev: virtual
	.venv/bin/pip install -e .
	.venv/bin/pre-commit install

test: dev
	tox -p

update-requirements: install
	.venv/bin/pip freeze > requirements.txt

.venv/bin/tox: # install tox
	.venv/bin/pip install -U tox

check: .venv/bin/tox # Code format check with isort and black
	tox -efmt-check
	tox -epep8

fix: .venv/bin/tox # fixes code formatting with isort and black
	tox -efmt
