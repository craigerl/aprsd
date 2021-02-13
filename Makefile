.PHONY: virtual dev build-requirements black isort flake8

all: pip dev

virtual: .venv/bin/pip # Creates an isolated python 3 environment

.venv/bin/pip:
	virtualenv -p /usr/bin/python3 .venv

.venv/bin/aprsd: virtual
	test -s .venv/bin/aprsd || .venv/bin/pip install -q -e .

install: .venv/bin/aprsd
	.venv/bin/pip install -Ur requirements.txt

dev-pre-commit:
	test -s .git/hooks/pre-commit || .venv/bin/pre-commit install

dev-requirements:
	test -s .venv/bin/twine || .venv/bin/pip install -q -r dev-requirements.txt

pip: virtual
	.venv/bin/pip install -q -U pip

dev: pip .venv/bin/aprsd dev-requirements dev-pre-commit

pip-tools:
	test -s .venv/bin/pip-compile || .venv/bin/pip install pip-tools

clean:
	rm -rf dist/*
	rm -rf .venv

test: dev
	.venv/bin/pre-commit run --all-files
	tox -p all

build: test
	rm -rf dist/*
	.venv/bin/python3 setup.py sdist bdist_wheel
	.venv/bin/twine check dist/*

upload: build
	.venv/bin/twine upload dist/*

docker: test
	docker build -t hemna6969/aprsd:latest -f docker/Dockerfile docker

update-requirements: dev pip-tools
	.venv/bin/pip-compile -q -U requirements.in
	.venv/bin/pip-compile -q -U dev-requirements.in

.venv/bin/tox: # install tox
	test -s .venv/bin/tox || .venv/bin/pip install -q -U tox

check: .venv/bin/tox # Code format check with isort and black
	tox -efmt-check
	tox -epep8

fix: .venv/bin/tox # fixes code formatting with isort and black
	tox -efmt
