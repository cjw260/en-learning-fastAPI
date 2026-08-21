# en-learning FastAPI backend

P01 establishes the process and database foundation. P02 adds deterministic,
auditable development-data initialization. P03 migrates only the authenticated AI API;
Core business routes, payment, Socket.IO, and production rollout remain out of scope.

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

## P03 AI API

The AI process exposes the legacy-compatible paths below:

- `GET /ai/v1/` remains a public health-style root.
- `GET /ai/v1/prompt/list` requires a Bearer access token.
- `POST /ai/v1/chat` requires a Bearer access token and streams the existing
  `{content, role: "ai", type: "reasoning" | "chat"}` SSE payload.
- `GET /ai/v1/chat/history` requires a Bearer access token and returns the current
  user's new P03 history for one role.

The legacy `userId` body/query field is retained for frontend compatibility but must equal
the signed JWT `userId`; it never decides authorization. History is stored in the P03
`AIChatThread` and `AIChatMessage` tables and is isolated by user and role. Old LangGraph
history is intentionally not migrated, so an empty initial history is expected.

Set `SECRET_KEY` to the same HS256 signing secret used by the existing Core API. Set the
DeepSeek and optional paired Bocha variables in the local `.env`; never commit their values.
The service retries only before the first model output, emits comment heartbeats, disables
proxy buffering, cancels the upstream stream on disconnect, and uses a Redis lease to prevent
concurrent writes to the same user/role conversation.

The prepared, unapplied AI-only canary and rollback procedure is documented in
`../docs/fastapi-refactor/runbooks/P03-ai-canary.md`. It must not be applied without separate
production authorization.

## Quality gates

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```
