# Promptful Sync

A small CLI (`import`/`export`) that keeps a team's Promptful prompts in sync across everyone's
local instance via git-tracked Prompt Files — no shared server required. See
[ADR-0009](../docs/adr/0009-local-sync-via-git-tracked-prompt-files.md) and
[/product/ai-specs/local-prompt-sync.md](../product/ai-specs/local-prompt-sync.md) for the design,
and [/CONTEXT.md](../CONTEXT.md#local-sync) for the vocabulary (Prompt File, Import, Export).

## Install

Not published to PyPI. Add it as a git or path dependency, alongside (not instead of) `promptful`
if you also need the read-only SDK:

```bash
uv add "promptful-sync @ git+https://github.com/<org>/<repo>#subdirectory=cli"
# or, from a local checkout of this repo:
uv add --editable /path/to/promptful/cli
```

## Usage

These commands are an HTTP client, not a process that starts one — the Promptful API must already
be running.

```bash
export PROMPTFUL_BASE_URL=http://localhost:8001   # or pass --base-url

uv run promptful-sync export ./prompts   # local database  -> Prompt Files, before committing
uv run promptful-sync import ./prompts   # Prompt Files -> local database, after `git pull`
```

- `export` also deletes a Prompt File once its slug no longer has a Live Version.
- `import` never deletes — a slug whose Prompt File disappeared is left alone locally.
- `import` reports (never applies, never crashes on) a Prompt File whose `role` disagrees with the
  server's current `role` for that slug — `role` is immutable once a Prompt is created.
- No conflict detection: whichever of a local edit or an `import` runs more recently wins.

## Why a separate package from the SDK

`sdk/`'s `Client` is deliberately read-only-plus-narrow-delete (see
[ADR-0008](../docs/adr/0008-sdk-gains-a-narrow-slug-based-delete.md)), and is sync-only
(`httpx.Client`) by design. This tool is fully async (`httpx.AsyncClient`) and needs write access
(create/update Prompts, create Categories) — bundling it into `sdk/` would either force a sync/async
mismatch or blur the SDK's narrow, read-only guarantee for everyone who installs it, not just the
developers who actually want local sync. Installing `promptful-sync` is opt-in and independent of
`promptful`; adding one never grants the other.

## Testing

```bash
cd cli
uv sync
uv run pytest
```

Tests drive the real FastAPI app (from `../api`) in-process (`httpx.AsyncClient` + `ASGITransport`
— this client is async, unlike the SDK's, so no real server/port is needed) against the same
`app_test` Postgres database `api/tests` and `sdk/tests` use. Requires:

```bash
cd ../api
docker compose up -d
POSTGRES_DB=app_test uv run alembic upgrade head   # once, if app_test isn't migrated yet
```

See `tests/conftest.py`.
