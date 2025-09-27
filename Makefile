type:
	uv run pyright

lint:
	uv run ruff check --fix --unsafe-fixes

dev:
	uv run uvicorn src.brewops.main:app --host 0.0.0.0 --port 8000 --reload
