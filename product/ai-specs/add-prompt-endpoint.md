# Add the `/prompt` endpoint

Plan for the first backend endpoint: CRUD over LLM prompts, with full version history kept per
slug. No code changes have been made yet — this is the design to implement against.

Domain vocabulary (Prompt, Slug, Version, Live Version, Tombstone) is defined in
[CONTEXT.md](../../CONTEXT.md). Key design decisions and their rationale are recorded as ADRs:
[0001](../../docs/adr/0001-versions-are-immutable-rows.md) (immutable versioned rows),
[0002](../../docs/adr/0002-delete-is-a-tombstone-version.md) (delete = tombstone),
[0003](../../docs/adr/0003-no-put-optimistic-concurrency-via-id.md) (no PUT, id-gated writes),
[0004](../../docs/adr/0004-jinja2-text-is-validated-not-rendered.md) (Jinja2 validated, not
rendered).

## Database

### Table: `prompts`

One row per Version (not per Prompt) — see ADR-0001.

| Column       | Type                          | Constraints                                         |
|--------------|-------------------------------|------------------------------------------------------|
| `id`         | `UUID`                        | PK, default `gen_random_uuid()`                      |
| `slug`       | `VARCHAR`                     | NOT NULL, `CHECK` matches `^(/[a-z0-9]+(-[a-z0-9]+)*)+$` |
| `version`    | `INTEGER`                     | NOT NULL, `CHECK (version >= 1)`                      |
| `text`       | `TEXT`                        | NOT NULL                                              |
| `is_deleted` | `BOOLEAN`                     | NOT NULL, default `false`                             |
| `created_at` | `TIMESTAMPTZ`                 | NOT NULL, default `now()`                             |

Constraints/indexes:
- `UNIQUE (slug, version)` — also serves as the index backing the "latest version for a slug"
  query (`... WHERE slug = :slug ORDER BY version DESC LIMIT 1`).
- `CHECK` on `slug` mirrors the Pydantic regex (Q7/Q13) — keep both in sync if the slug format
  rule ever changes; the Pydantic check is the better error message, the DB check is the safety
  net for any write path that bypasses the API.

No `updated_at` column — rows are never updated after insert (ADR-0001), so the column would be
meaningless. No row is ever physically deleted; "delete" inserts a Tombstone row.

### Migration

`api/` has no `alembic/` directory yet — this is the first migration in the project.

1. `uv run alembic init -t async alembic` (async template, matches the async SQLAlchemy engine
   used at runtime).
2. Point `alembic/env.py` at the app's `Base.metadata` and read `DATABASE_URL` from the app's
   `pydantic-settings` config rather than hardcoding it.
3. Alembic itself should run its migration connection via the **sync** driver (`psycopg2-binary`,
   already a dependency) rather than `asyncpg` — this is the standard split for this stack: async
   driver for the request-serving engine, sync driver for migrations. This is presumably why both
   `asyncpg` and `psycopg2-binary` are already listed in `api/pyproject.toml`.
4. `uv run alembic revision --autogenerate -m "create prompts table"` after the SQLAlchemy model
   (below) exists, then review the generated SQL before applying — autogenerate won't pick up the
   `CHECK` constraints on `slug`/`version`, those need to be added by hand to the migration.
5. `uv run alembic upgrade head` against the local Postgres started via `docker compose up -d`
   (see [CLAUDE.md](../../CLAUDE.md)).

## API

Base path: `/prompt`. No `PUT` (ADR-0003).

### `POST /prompt/create` — Create

- Body: `{ "slug": str, "text": str }`.
- Validates `slug` format and `text` as parseable Jinja2 (no execution) — 422 on either failure.
- 409 if the slug currently has a Live Version (a non-deleted row at the highest existing
  `version` for that slug).
- Otherwise inserts `version = MAX(version WHERE slug=...) + 1` (`1` if the slug has no rows at
  all yet; continues climbing, never resets, if the slug was previously deleted — see ADR-0002).
- 201, body is the new row (`id`, `slug`, `version`, `text`, `is_deleted`, `created_at`).

### `POST /prompt/{id}` — Update

- Path: `{id}` — must be the `id` of the slug's current Live Version.
- Body: `{ "text": str }` (slug is fixed at creation; this endpoint cannot move a Prompt to a
  different slug — that would be a different operation, out of scope here).
- 404 if `{id}` doesn't exist at all.
- 409 if `{id}` exists but is not the slug's current Live Version (optimistic concurrency —
  ADR-0003; another write landed since the caller last read this version).
- Validates `text` as parseable Jinja2 — 422 on failure.
- Inserts a new row at `version = MAX(version) + 1` for that slug, with the new `text`.
- 200, body is the new row.

### `DELETE /prompt/{id}` — Delete

- Path: `{id}` — same optimistic-concurrency rule as Update (must be the slug's current Live
  Version; 404 if unknown, 409 if stale).
- Inserts a Tombstone row (`is_deleted = true`) at `version = MAX(version) + 1`.
- 200, body is the new Tombstone row.

### `GET /prompt/{id}` — Read by id

- Returns the exact row for that `id`, regardless of `is_deleted` or whether it's the slug's Live
  Version — an explicit id lookup always resolves if the row exists.
- 404 if no row has that `id`.

### `GET /prompt?slug=...&version=...` — Read by slug

- `slug` required, `version` optional.
- With `version`: returns that exact `(slug, version)` row (Tombstone or not) — 404 if it doesn't
  exist.
- Without `version`: returns the slug's Live Version — 404 if the slug has no rows, or if its
  highest-version row is a Tombstone.

### Out of scope for this endpoint (deferred, not forgotten)

- Listing/history browsing for a slug (e.g. "all versions of `/sales/screening/first-lead`") — no
  route exists for this yet; today a caller can only reach versions whose `id`/`version` it
  already knows from its own prior writes.
- Rendering Jinja2 templates with variables (ADR-0004) — storage and syntax validation only.
- Physical deletion of a specific version (e.g. to purge a leaked secret) — `DELETE` only ever
  appends a Tombstone (ADR-0002); hard delete is a separate, more dangerous operation.
- Tags and ownership (private person vs. company) — present in CLAUDE.md's target domain model,
  not part of this first endpoint's field set.

## Backend implementation shape

Following the connection-handling practices from the referenced FastAPI+PostgreSQL article
(async SQLAlchemy engine via `asyncpg`, pooled connections, dependency-injected sessions,
Alembic-managed schema):

```
api/
  app/
    main.py            # FastAPI() app, includes the prompt router
    core/
      config.py        # pydantic-settings: DATABASE_URL, pool_size, max_overflow
    db/
      session.py        # async engine (asyncpg) + async_sessionmaker + get_db() dependency
      base.py            # declarative Base
    models/
      prompt.py          # SQLAlchemy model `PromptVersion`, table name `prompts`
    schemas/
      prompt.py          # Pydantic request/response models, slug regex + Jinja2 validators
    routers/
      prompt.py          # the five routes above
  alembic/
    env.py
    versions/
  alembic.ini
  tests/
    test_prompt.py
```

- `db/session.py`: async engine created once at import time with `pool_size` / `max_overflow`
  read from settings (article's example: `pool_size=20, max_overflow=10` as a starting point for
  local/MVP use); `get_db()` is a FastAPI dependency yielding an `AsyncSession` per request and
  closing it afterward.
- `tests/conftest.py`: implements Q1 against a real constraint discovered during
  implementation — pytest-asyncio opens a fresh event loop per test function, so a pooled
  asyncpg connection reused across tests fails ("another operation is in progress") because
  it's still bound to a now-closed loop. The test engine uses `NullPool` (a real connection
  opened and closed per checkout, never reused across a loop boundary) instead of the
  transaction-rollback-per-test pattern originally sketched in Q1; isolation between tests is a
  `TRUNCATE TABLE prompts` in an `autouse` fixture after each test instead.
- Model class is named `PromptVersion` (table name stays `prompts`) — see the Prompt/Version
  terminology split in [CONTEXT.md](../../CONTEXT.md).
- Error handling: a unique-constraint violation on `(slug, version)` during Create/Update (a race
  between the `MAX(version)` read and the insert) should be caught and surfaced as 409, not a raw
  500.

### Cleanup noted while planning

`api/pyproject.toml`'s `[tool.pytest.ini_options]` has a comment — *"tests import the app modules
(documents, main, db.*)"* — left over from the project this skeleton was copied from. `documents`
isn't a module in this project; once `app/` exists per the layout above, that comment should be
corrected to reflect this project's actual module names.

## UI

First frontend feature: a single page at the app's root route to create a Prompt (slug + text).
`ui/` has no application code yet — this is also the first Next.js App Router shell (root layout,
`globals.css`, shadcn primitives), not just one page.

### Backend prerequisite

`api/app/main.py` has no `CORSMiddleware`. The browser calls FastAPI directly (no Next.js proxy
route — considered and rejected: a proxy would avoid touching the backend at all, but was rejected
to keep this single-endpoint feature from needing a parallel route-handler layer in `ui/`). Before
this page works, add `CORSMiddleware` to `main.py` allowing the Next.js dev origin
(`http://localhost:3001`). This is a backend code change, out of scope for the planning-only session
that produced this doc.

### Page

- Route: `app/page.tsx` — the app's root page IS this page, per the brief.
- `app/page.tsx` stays a Server Component; the form lives in `components/create-prompt-form.tsx`,
  marked `"use client"`.
- Two inputs: a single-line slug input and a textarea for `text`, plus a submit button. No
  client-side duplicate of the backend's slug-regex or Jinja2-syntax validation — only `required`
  on both inputs. Every submission hits `POST /prompt/create` and renders whatever the backend
  returns.

### Data fetching

- `@tanstack/react-query` is used from the start (already a dependency), via a `useMutation`
  calling `POST /prompt/create`.
- Needs a `QueryClientProvider`: add `app/providers.tsx` (a client component wrapping
  `QueryClientProvider`), rendered by `app/layout.tsx` as `<Providers>{children}</Providers>`
  (`layout.tsx` itself stays a Server Component).
- API base URL: `NEXT_PUBLIC_API_URL` env var (must be `NEXT_PUBLIC_`-prefixed to be readable by
  client-side code), defaulting to `http://localhost:8000` in dev — confirm `ui/.env.local`
  defines this, or add it.

### Result handling

- Success (201): `sonner` toast ("Prompt created") + clear both fields. No redirect or detail
  view — there's no read/list page yet (the backend spec defers listing too), so there's nowhere
  meaningful to send the user.
- Error: render the backend's `detail` string inline near the relevant field — slug-format errors
  and the 409 ("slug already has a live version") near the slug input, Jinja2 syntax errors near
  the textarea. No generic catch-all toast for errors; the backend's `detail` text is the point.
- `<Toaster />` (sonner) mounted once in `app/layout.tsx`.

### Component scaffolding

- `pnpm dlx shadcn@latest add button input textarea sonner` — generates
  `components/ui/{button,input,textarea,sonner}.tsx` and `lib/utils.ts` (the `cn` helper used by
  the `@/lib/utils` alias), matching the `new-york` / `neutral` conventions already declared in
  `components.json`.
- Hand-write `app/layout.tsx` (mounts `Providers` + `Toaster`) and `app/globals.css` (Tailwind v4
  entrypoint) — these are app-shell files the `add` command doesn't generate.

### File layout

```
ui/
  app/
    layout.tsx              # root layout; wraps children in <Providers>, mounts <Toaster />
    page.tsx                 # root route; renders <CreatePromptForm />
    providers.tsx             # "use client"; QueryClientProvider
    globals.css                 # Tailwind v4 entrypoint
  components/
    create-prompt-form.tsx       # "use client"; slug input + textarea + submit, useMutation
    ui/
      button.tsx
      input.tsx
      textarea.tsx
      sonner.tsx
  lib/
    utils.ts                       # cn() helper (shadcn convention)
```

### Out of scope for this first page (deferred, not forgotten)

- Listing/browsing existing prompts or versions — no read UI yet, matching the backend's own
  deferred scope.
- Update/Delete UI.
- Client-side slug/Jinja2 validation ahead of the backend round-trip.
- Auth/ownership scoping in the UI (CLAUDE.md's target domain model; not in this endpoint's scope
  either).
