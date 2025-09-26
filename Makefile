PY=python
UVICORN=uvicorn
APP=src.app:app

.PHONY: run dev test lint format precommit hooks docker-up docker-down

run:
	$(UVICORN) $(APP) --host 0.0.0.0 --port 8000

dev:
	$(UVICORN) $(APP) --reload --host 0.0.0.0 --port 8000

test:
	pytest -q

lint:
	flake8 src tests

format:
	black src tests && isort src tests

precommit:
	pre-commit run --all-files

hooks:
	pre-commit install

docker-up:
	docker compose -f deploy/docker-compose.yml up --build -d

docker-down:
	docker compose -f deploy/docker-compose.yml down
