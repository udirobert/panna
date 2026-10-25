.PHONY: backend frontend test lint

backend:
	uvicorn src.api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest -q

lint:
	ruff check src tests && ruff format --check src tests

run-pipeline:
	python -m src.cli
