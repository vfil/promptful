# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Promptful is a CRUD service for managing LLM prompts for individuals and companies. Prompts are addressed
by a hierarchical slug (e.g. `/sales/screening/first-lead`), which doubles as a namespace — slashes group
related prompts the way directories group files. Beyond plain CRUD, every prompt keeps a full version
history, and prompts can carry tags for cross-namespace organization.

This is currently a skeleton: `api/` and `ui/` contain only dependency/config manifests, no application
code yet. Both directories were bootstrapped from another project, so check whether copied files (e.g.
`api/docker-compose.yml` comments referencing `doc_import`, snapshot seeding, or ADR docs) actually apply
before trusting them — they may be stale leftovers rather than this project's design.

Repo layout: `api/` is the backend, `ui/` is the frontend. There is no root-level package manager — each
side is built and run independently.

## Backend (`api/`)

FastAPI + SQLAlchemy (async) + PostgreSQL, dependency-managed with `uv`. Migrations via Alembic.

Key dependencies: `fastapi[standard]`, `sqlalchemy[asyncio]`, `asyncpg` (runtime async driver),
`psycopg2-binary` (sync driver, typically used by Alembic), `pydantic` / `pydantic-settings`, `alembic`.

```bash
cd api
uv sync                       # install dependencies into .venv
uv run fastapi dev            # run the dev server with reload
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

## Domain model (target design)

- **Slug**: hierarchical path (e.g. `/sales/screening/first-lead`) that identifies a prompt and implies its
  namespace via path segments.
- **Prompt**: the entity at a slug. Mutations create a new version rather than overwriting — full history
  is kept per slug.
- **Version**: an immutable snapshot of a prompt's content tied to a slug; CRUD operations on a prompt are
  really operations that read/write specific versions while preserving prior ones.
- **Tags**: free-form labels attached to a prompt, orthogonal to the slug/namespace hierarchy, for
  cross-cutting organization and search.
- **Owner**: prompts belong to a private person or a company — ownership/visibility scoping should be a
  first-class part of any schema or API design here.

When implementing this, the slug/namespace/version relationship is the architectural core: get the data
model for "one slug → many versions, slug implies namespace by path segments" right before building CRUD
endpoints or UI around it.
