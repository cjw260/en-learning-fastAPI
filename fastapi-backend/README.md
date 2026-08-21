# en-learning FastAPI backend

P01 establishes the process and database foundation. P02 adds deterministic,
auditable development-data initialization; it still contains no migrated business API.

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

## P02 development bootstrap

The bootstrap is disabled for `ENVIRONMENT=production`. In development or test it performs
`migrate -> verify/download pinned ECDICT -> batch word upsert -> course upsert -> MinIO
course asset upsert -> verify -> JSON report` with one command:

```bash
uv run en-learning-bootstrap
```

The fixed ECDICT version, commit, SHA-256, byte size, and MIT attribution are recorded in
`resources/ecdict-source.json` and `resources/ECDICT-LICENSE.txt`. The 65.9 MB CSV is cached
under ignored `.bootstrap/`; pass `--source /absolute/path/ecdict.csv --no-download` for an
offline run. Reports and rejected-row JSONL are also written under `.bootstrap/` by default.
Each accepted CSV batch commits independently, so a failed run keeps an explicit recovery
point and is safe to rerun. No user, learning, payment, analytics, or chat rows are seeded.

## Quality gates

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```
