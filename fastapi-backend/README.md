# en-learning FastAPI backend

P01 establishes the two HTTP application entries, the worker/scheduler boundary,
shared lifecycle resources, health contracts, SQLAlchemy models, and Alembic.
It intentionally contains no data import or business endpoints.

## Local setup

```bash
uv sync --frozen
cp .env.example .env
```

Replace every `replace-me` value locally. Never commit `.env`.

## Explicit process entries

```bash
uv run uvicorn en_learning.api.main:create_app --factory --host 127.0.0.1 --port 8000
uv run uvicorn en_learning.ai.main:create_app --factory --host 127.0.0.1 --port 8001
uv run taskiq worker en_learning.worker.broker:broker --workers 1
uv run taskiq scheduler en_learning.worker.broker:scheduler --skip-first-run
```

Migrations are always explicit and are never run from an application lifespan:

```bash
uv run alembic upgrade head
uv run alembic downgrade base
```

## Quality gates

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```
