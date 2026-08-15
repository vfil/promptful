# Sync CLI ships as its own package, not bundled into the SDK

The local-sync CLI ([ADR-0009](./0009-local-sync-via-git-tracked-prompt-files.md)) was first built
inside `api/`, reachable only by developers with a checkout of the Promptful backend itself —
useless to a consuming application that only depends on `sdk/`'s `promptful` package, which is how
every actual consumer reaches Promptful (discovered when `uv run promptful-sync` failed in a real
consuming project with "No such file or directory": nothing that project depended on had ever
installed it). It now ships as its own package, `cli/` (distribution name `promptful-sync`), that a
consuming application adds alongside — not instead of — `promptful` only if it wants local sync.

Two alternatives were considered and rejected:

- **Bundle it into `sdk/`** so installing `promptful` installs the CLI for free. Rejected on two
  grounds: `sdk`'s `Client` is sync-only (`httpx.Client`) by design, while the sync CLI is fully
  async (`httpx.AsyncClient`) — a real technical mismatch, not just a style one — and bundling
  write-capable code into the same distribution as the deliberately narrow, read-only SDK
  ([ADR-0008](./0008-sdk-gains-a-narrow-slug-based-delete.md)) would mean every `promptful` install
  silently gains importable write access, not just the developers who actually asked for it.
- **Leave it in `api/`**, document invoking it via a local checkout or `uvx --from git+...`.
  Rejected: every consuming team would need either a second local checkout of the whole Promptful
  monorepo just to reach a CLI, or a non-standard invocation instead of the plain
  `uv run promptful-sync` a developer naturally reaches for.

`api/pyproject.toml` reverts to being a plain, unpackaged FastAPI app — the `[project.scripts]`
entry and the `tool.uv`/`tool.setuptools` packaging workaround it needed only existed because the
CLI was living somewhere it didn't belong. `cli/` mirrors `sdk/`'s existing packaging (`uv_build`,
src-layout) rather than repeating that workaround.
