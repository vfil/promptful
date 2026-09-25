# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Promptful is a CRUD service for managing LLM prompts for individuals and companies. Each Prompt lives at a
hierarchical Slug (e.g. `/sales/screening/first-lead`), assembled from an explicit Category tree (e.g.
`/sales/screening`) plus a Leaf Slug (`first-lead`) — Category is a real, first-class entity, not just a
naming convention baked into the slug string. Beyond plain CRUD, every prompt keeps a full version history.
See [CONTEXT.md](CONTEXT.md) for the full glossary (Category, Slug Segment, Version, Live Version,
Tombstone, Role, ...) and the Domain model section below for what's implemented vs. still planned.

`api/` and `ui/` were originally bootstrapped from another project, so treat any copied file (e.g.
`api/docker-compose.yml` comments referencing `doc_import`, snapshot seeding, or ADR docs) with suspicion
until you confirm it actually reflects this project's design — cross-check against
[CONTEXT.md](CONTEXT.md) and [docs/adr/](docs/adr/), which are this project's own and are kept current.

Repo layout: `api/` is the backend, `ui/` is the frontend, `sdk/` is a Python client library for
third-party developers who want to fetch prompts from their own code, `cli/` is a local sync
(import/export) CLI for teams running Promptful locally without a shared server. There is no
root-level package manager — each side is built and run independently.

## Backend (`api/`)

FastAPI + SQLAlchemy (async) + PostgreSQL, dependency-managed with `uv`. Migrations via Alembic.

Key dependencies: `fastapi[standard]`, `sqlalchemy[asyncio]`, `asyncpg` (runtime async driver),
`psycopg2-binary` (sync driver, typically used by Alembic), `pydantic` / `pydantic-settings`, `alembic`.

```bash
cd api
uv sync                       # install dependencies into .venv
uv run fastapi dev --port 8001  # run the dev server with reload (port 8001; 8000 conflicts locally)
uv run alembic upgrade head   # apply migrations
uv run alembic revision --autogenerate -m "message"   # generate a migration after model changes
uv run pytest                          # run the full test suite
uv run pytest tests/path/to_test.py::test_name   # run a single test
```

Test config (`pyproject.toml`): `testpaths = ["tests"]`, `pythonpath = ["."]` (so tests import app modules
directly, e.g. `main`, `db.*`), `asyncio_mode = "auto"` (plain `async def test_*` functions are collected
without needing `@pytest.mark.asyncio`).

Local Postgres + Adminer for development:

```bash
cd api
docker compose up -d     # postgres on :5432 (password: example), adminer on :8085
```

## Frontend (`ui/`)

Next.js (App Router) + React + TypeScript, package-managed with `pnpm`. Styling via Tailwind CSS v4 with
shadcn/ui components (`components.json`: "new-york" style, icons from `lucide-react`, global CSS at
`app/globals.css`). Data fetching via `@tanstack/react-query`; client state via `zustand`; toasts via
`sonner`; prompt content rendering via `react-markdown`.

Import aliases (`@/*` → repo root): `@/components`, `@/components/ui`, `@/lib`, `@/lib/utils`, `@/hooks`.

```bash
cd ui
pnpm install
pnpm dev          # runs `tsc --noEmit --watch` and `next dev` concurrently
pnpm build
pnpm lint
pnpm typecheck    # tsc --noEmit, standalone (no watch)
```

`pnpm dev` type-checks in parallel with the dev server — a red squiggly in the terminal from the `tsc`
process is a real type error even if the Next.js server itself doesn't fail to compile.

Do not use the `playwright-cli` skill (or other browser automation) to verify UI changes unless the user
directly asks for it — the user prefers to test manually in their own browser. Typecheck/lint/tests are
still expected before reporting a UI change complete; just don't drive a browser to do it.

## SDK (`sdk/`)

A thin, read-only, sync Python client for the API (`Client.get_prompt`, `.get_prompts`, `.list_prompts`),
dependency-managed with `uv`, src-layout (`src/promptful/`). Ships as a git/path dependency for now — not
published to PyPI. Full usage docs: [sdk/README.md](sdk/README.md).

```bash
cd sdk
uv sync                       # install dependencies into .venv
uv run pytest                 # full suite — needs api/'s docker-compose Postgres + app_test migrated
```

Its own test suite boots the real FastAPI app via uvicorn on a real port (not a mock, not ASGITransport —
the SDK's `Client` is sync-only, and `ASGITransport` only supports async clients), pointed at the same
`app_test` database `api/tests` uses. See `sdk/tests/conftest.py`.

## CLI (`cli/`)

`promptful-sync` — `import`/`export` Prompts between the local database and git-tracked Prompt Files,
for teams running Promptful locally without a shared server
([ADR-0009](docs/adr/0009-local-sync-via-git-tracked-prompt-files.md)). A separate package from the
SDK on purpose, not bundled in — see
[ADR-0010](docs/adr/0010-sync-cli-ships-as-its-own-package.md). Dependency-managed with `uv`,
src-layout (`src/promptful_sync/`). Full usage docs: [cli/README.md](cli/README.md).

```bash
cd cli
uv sync                       # install dependencies into .venv
uv run pytest                 # full suite — needs api/'s docker-compose Postgres + app_test migrated
```

Its own test suite drives the real FastAPI app in-process over `ASGITransport` (this client is async,
unlike the SDK's, so unlike `sdk/tests` it needs no real bound socket), pointed at the same
`app_test` database `api/tests` and `sdk/tests` use. See `cli/tests/conftest.py`.

## Domain model

The implemented domain model — Slug, Category, Slug Segment, Category Path, Leaf Slug, Version, Live
Version, Tombstone, Role, and the Local Sync concepts (Prompt File, Import, Export) — is documented in
[CONTEXT.md](CONTEXT.md), the canonical glossary. Keep that file in sync with the code, not this one.

### Planned, not yet built

- **Tags**: free-form labels attached to a Prompt, orthogonal to the Category hierarchy, for cross-cutting
  organization and search. Deliberately deferred so far — see
  [ADR-0001](docs/adr/0001-versions-are-immutable-rows.md).
- **Owner**: Prompts are meant to belong to a private person or a company, but ownership/visibility scoping
  isn't modeled anywhere in the schema or API yet. Treat this as a first-class concern for whenever
  auth/multi-tenancy work starts, not something to bolt on after the fact.
