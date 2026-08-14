# Local Prompt Sync (Import / Export)

Give developers running Promptful locally two commands — `export` and `import` — that move Prompts
between the local database and git-tracked **Prompt Files** in the consuming application's own
repo, so a team's prompts stay in sync via ordinary `git pull`/`push` instead of a shared server.

See also: [ADR-0009](../../docs/adr/0009-local-sync-via-git-tracked-prompt-files.md) for why, and
[CONTEXT.md](../../CONTEXT.md#local-sync) for the vocabulary (Prompt File, Import, Export).

> **Note:** this plan (and the "New backend API endpoints" claim below) describes the first cut,
> built inside `api/app/sync/`. It was relocated to its own package, `cli/`, shortly after — a
> real consuming project couldn't reach a CLI that only existed inside the backend's own project.
> See [ADR-0010](../../docs/adr/0010-sync-cli-ships-as-its-own-package.md) for why, and
> [/cli/README.md](../../cli/README.md) for where the usage instructions below now actually live.
> The behavior itself (the 9 steps, the constraints) is unchanged — only the package location is.

This is purely additive: **no existing file changes, no new backend API endpoints.** Everything
needed already exists (`GET /categories`, `POST /categories`, `GET /prompts`,
`POST /prompts/batch`, `POST /prompt/create`, `POST /prompt/{id}`) — this plan builds one new HTTP
client and a CLI around them.

---

## Constraints

- A Prompt File is `.prompt.md`, its path mirroring the Slug (Category Path → directories, Leaf
  Slug → filename), YAML frontmatter holding only `role`, raw Jinja2 `text` as the body. No `id`,
  `version`, or `created_at` in the file — see ADR-0009.
- `import`/`export` talk to the local API **over HTTP**, against an already-running instance — they
  do not start one. This is a documented precondition, not handled by the tool.
- `import` only ever creates or updates; it never deletes a local row. `export` does delete a
  Prompt File when its slug no longer has a Live Version.
- `role` is immutable once a Prompt is created (ADR-0007). If a Prompt File's `role` differs from
  the server's current `role` for that slug, `import` cannot apply it (there is no API for it) —
  report it as a per-slug error, don't crash the run and don't silently skip it.
- No conflict detection: whichever of a local edit or an `import` runs more recently wins.
- The sync client does not depend on, or extend, the `sdk` package — keeps ADR-0008's deliberately
  narrow SDK surface (no create/update) undisturbed. It's a separate, small `httpx` client.

---

## Step-by-step implementation plan

### Step 1 — Dependencies & scaffolding

`api/pyproject.toml`:
- Move `httpx` from `[dependency-groups] dev` into `dependencies` — the CLI needs it at runtime,
  not just in tests.
- Add `pyyaml` for frontmatter parsing.
- Add a console script entry point:
  ```toml
  [project.scripts]
  promptful-sync = "app.sync.cli:main"
  ```

New subpackage `api/app/sync/` (alongside `routers/`, `schemas/`, `models/`), holding everything
below.

### Step 2 — Prompt File read/write (`api/app/sync/prompt_file.py`)

Pure functions, no network — unit-testable with no database, same spirit as
`tests/test_prompt_schemas.py`.

```python
@dataclass
class ParsedPromptFile:
    role: str
    text: str

def parse_prompt_file(path: Path) -> ParsedPromptFile:
    raw = path.read_text()
    _, frontmatter, body = raw.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return ParsedPromptFile(role=meta["role"], text=body.lstrip("\n"))

def write_prompt_file(path: Path, role: str, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nrole: {role}\n---\n{text}")

def slug_to_path(slug: str, root: Path) -> Path:
    return root / f"{slug.lstrip('/')}.prompt.md"

def path_to_slug(path: Path, root: Path) -> str:
    return "/" + str(path.relative_to(root)).removesuffix(".prompt.md")
```

### Step 3 — Sync HTTP client (`api/app/sync/client.py`)

A small `SyncClient` wrapping `httpx.AsyncClient(base_url=...)`, reading `PROMPTFUL_BASE_URL` from
the environment (same env var name the SDK uses, independent implementation — see Constraints).
Methods, each a thin wrapper over one existing endpoint:

| Method | Endpoint |
|---|---|
| `list_categories()` | `GET /categories` |
| `create_category(slug_segment, parent_id)` | `POST /categories` |
| `list_live_prompts()` | `GET /prompts` |
| `get_prompts_batch(slugs)` | `POST /prompts/batch` |
| `create_prompt(leaf_slug, category_id, role, text)` | `POST /prompt/create` |
| `update_prompt(id, text)` | `POST /prompt/{id}` |

### Step 4 — Category resolution (`api/app/sync/categories.py`)

`ensure_category_path(client, category_path) -> UUID`: fetch all categories once per run (cached),
walk `category_path`'s segments top-down, create any missing ancestor via `create_category`,
return the leaf's id. Same materialized-path logic ADR-0005 already established — this just
auto-vivifies it from a directory path instead of a combobox selection.

### Step 5 — `export` (`api/app/sync/export_cmd.py`)

1. `list_live_prompts()` → current live slugs.
2. `get_prompts_batch(slugs)` → full `role`/`text` per slug (list endpoint omits `text` by design).
3. Walk the target directory for existing `.prompt.md` files → `{slug: path}`.
4. For each live prompt: write its file if missing, or if (role, text) differs from what's on
   disk.
5. For each existing file whose slug is no longer live: delete it.
6. Print created/updated/deleted counts and slugs.

### Step 6 — `import` (`api/app/sync/import_cmd.py`)

1. Walk the source directory for `.prompt.md` files → parse each into `(slug, role, text)`.
2. `ensure_category_path` for every distinct category path referenced.
3. `get_prompts_batch(slugs)` → current server state per slug (`None` = no Live Version).
4. Per file:
   - No Live Version → `create_prompt`.
   - Live Version exists, `role` matches, `text` differs → `update_prompt`.
   - Live Version exists, `role` differs → **error, not applied**: `"{slug}: file role '{x}' !=
     server role '{y}' — role is immutable, resolve by hand"`.
   - Live Version exists, identical → skip.
   - Never deletes (Constraints).
5. Print created/updated/skipped/errored counts and slugs; non-zero exit if anything errored.

### Step 7 — CLI entrypoint (`api/app/sync/cli.py`)

`argparse`, two subcommands (`import`, `export`), each taking a directory as a positional argument
and `--base-url` overriding `PROMPTFUL_BASE_URL`. Stdlib `argparse` over adding `click`/`typer` —
two subcommands and one positional argument don't need a framework.

```
uv run promptful-sync export ./prompts
uv run promptful-sync import ./prompts
```

### Step 8 — Tests

- `tests/test_sync_prompt_file.py` — unit tests for parse/write/slug↔path round-tripping. No
  database, no HTTP.
- `tests/test_sync_export.py` / `tests/test_sync_import.py` — integration tests driving
  `export_cmd`/`import_cmd` against the real FastAPI app in-process (`httpx.AsyncClient` +
  `ASGITransport`, `api/tests/conftest.py`'s existing pattern — the sync client is async, so unlike
  the SDK it doesn't need `sdk/tests`' real-uvicorn-server harness) and the `app_test` database,
  writing to a `tmp_path` directory. Cover: clean import, clean export, role-mismatch reported not
  crashed, export removing a file for a tombstoned slug, import leaving an orphaned local row alone
  when its file is gone.

### Step 9 — Docs

- `api/README.md`: new "Local sync" section — `export` before committing, `import` after
  `git pull`, and that the API must already be running.
- Flag (not this repo's to write): the consuming application's own onboarding docs should point
  new team members at this workflow.

---

## API surface summary

No new endpoints. Reused as-is: `GET /categories`, `POST /categories`, `GET /prompts`,
`POST /prompts/batch`, `POST /prompt/create`, `POST /prompt/{id}`.

---

## Out of scope

- Conflict detection between a local edit and an incoming `import` (Sync Baseline) — ADR-0009.
- `import` propagating deletes — ADR-0009.
- Any automatic/background trigger (file watcher, git hook, daemon) — manual commands only.
- A dedicated prompts repo, or support for more than one consuming application — revisit if a
  second consumer needs the same prompts.
- Syncing empty Categories — ADR-0009.
- Containerizing the API/UI themselves for `docker compose up` — separate packaging question, not
  addressed here.
