SOURCE_DIR = townsnet

lint:
	pylint ${SOURCE_DIR}

format:
	isort ${SOURCE_DIR}
	black ${SOURCE_DIR}

install:
	pip install .

venv: #then source .venv/bin/activate
	python3 -m venv .venv

install-dev:
	pip install -e '.[dev]'

build:
	python3 -m build .

clean:
	rm -rf ./build ./dist ./townsnet.egg-info

test:
	pytest tests

test-cov:
	pytest tests --cov
