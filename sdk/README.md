# Promptful SDK

A thin Python client for the Promptful API — fetch prompts by slug from your own codebase, with
one narrow write path (`delete_prompt`, for automation/cleanup scripts) — see
[ADR-0008](../docs/adr/0008-sdk-gains-a-narrow-slug-based-delete.md). See [/CONTEXT.md](../CONTEXT.md)
for the domain vocabulary (Prompt, Slug, Version, Live Version, Tombstone).

## Install

Not published to PyPI yet. Add it as a git or path dependency:

```bash
uv add "promptful @ git+https://github.com/<org>/<repo>#subdirectory=sdk"
# or, from a local checkout of this repo:
uv add --editable /path/to/promptful/sdk
```

## Quickstart

```python
from promptful import Client, PromptNotFoundError

client = Client(base_url="https://prompts.example.com")  # or set PROMPTFUL_BASE_URL

prompt = client.get_prompt("/sales/screening/first-lead")
print(prompt.text)  # raw Jinja2 template text — not rendered, see below

try:
    client.get_prompt("/sales/does-not-exist")
except PromptNotFoundError:
    ...

# Fetch several at once — missing slugs come back as None, aligned to input order.
results = client.get_prompts(["/sales/first-lead", "/sales/second-lead"])

# Lightweight listing of every live prompt (no `text`).
for summary in client.list_prompts():
    print(summary.slug, summary.version)

# Delete by slug — appends a Tombstone version server-side (ADR-0002).
client.delete_prompt("/sales/screening/first-lead")

client.close()  # or use `with Client(...) as client: ...`
```

### `Prompt` vs. the domain model's "Prompt"

`CONTEXT.md` defines **Prompt** as the entity across all its history and **Version**/**Live
Version** as a specific immutable snapshot. What `get_prompt`/`get_prompts` actually return is a
Live Version snapshot — but the SDK names the returned type `Prompt` anyway, for call-site
ergonomics (`prompt.text` reads better than `prompt_version.text`). This is a deliberate,
considered divergence for the SDK's public surface, not a modeling mistake — don't "fix" it to
match `CONTEXT.md` without raising it first.

## Error handling

All errors inherit from `PromptfulError`:

| Exception                   | Raised when                                              |
|------------------------------|-----------------------------------------------------------|
| `PromptNotFoundError`        | `get_prompt`/`delete_prompt` has no Live Version at that slug |
| `PromptConflictError`        | `delete_prompt(slug)` raced a concurrent write between resolving and deleting the Live Version |
| `PromptfulAPIError`          | The API responded with an unexpected error status         |
| `PromptfulConnectionError`   | The API couldn't be reached (network, timeout, DNS, ...)   |

## Not (yet) supported, on purpose

These are deliberate v1 scope decisions, not gaps:

- **No auth** — the API itself has none yet either.
- **No caching** — every call hits the API; wrap it yourself if you need caching.
- **No automatic retries** — a failure raises immediately, including `PromptConflictError` from
  `delete_prompt` — call it again if the delete should still happen.
- **No template rendering** — `text` is always the raw, unrendered Jinja2 source.
- **No version pinning** — `get_prompt`/`get_prompts` always return the current Live Version.
- **No create or update** — `delete_prompt` is the SDK's only write path (ADR-0008); creating and
  editing prompts stay API/UI-only.

## API reference

| Method                        | Returns                | Notes                                              |
|-------------------------------|-------------------------|-----------------------------------------------------|
| `Client(base_url=None, *, timeout=10.0)` | —          | `base_url` falls back to the `PROMPTFUL_BASE_URL` env var |
| `.get_prompt(slug)`            | `Prompt`                | Raises `PromptNotFoundError` if there's no Live Version |
| `.get_prompts(slugs)`          | `list[Prompt \| None]`  | Aligned to `slugs`' order/duplicates; `None` = not found |
| `.list_prompts()`              | `list[PromptSummary]`   | Every live prompt, no `text`                        |
| `.delete_prompt(slug)`         | `None`                  | Raises `PromptNotFoundError` or `PromptConflictError` |
| `.close()`                     | —                        | Or use `Client(...)` as a context manager           |

## Testing

```bash
cd sdk
uv sync
uv run pytest
```

Tests are integration tests that boot the real FastAPI app (from `../api`) via uvicorn on a real
port — not mocked HTTP — against the same `app_test` Postgres database `api/tests` uses. Requires:

```bash
cd ../api
docker compose up -d                              # postgres on :5433
POSTGRES_DB=app_test uv run alembic upgrade head   # once, if app_test isn't migrated yet
```

See `tests/conftest.py` for why a live server rather than a mock: `Client` is sync-only, and
httpx's `ASGITransport` (used by `api/tests` for in-process testing) only supports async clients.
