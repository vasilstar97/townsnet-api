SOURCE_DIR = app

lint:
	pylint ${SOURCE_DIR}

format:
	isort ${SOURCE_DIR}
	black ${SOURCE_DIR}

install:
	pip install -r requirements.txt

venv: #then source .venv/bin/activate
	python3 -m venv .venv

compose-dev:
	docker compose -f "docker-compose.dev.yml" up --build
