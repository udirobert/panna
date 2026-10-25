.PHONY: backend frontend test lint test-backend test-frontend

backend:
	uvicorn src.api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	pytest -q

test-frontend:
	cd frontend && npx vitest run

lint:
	ruff check src tests && ruff format --check src tests

run-pipeline:
	python -m src.cli
