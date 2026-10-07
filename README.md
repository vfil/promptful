# Promptful - full management suite with versioning for all your prompts

A CRUD service for managing LLM prompts for individuals and companies. Every Prompt lives at a
hierarchical Slug (e.g. `/sales/screening/first-lead`) built from an explicit Category tree plus a
Leaf Slug, and every mutation appends a new Version rather than overwriting — full history is kept
per Prompt, including through deletion. See [CONTEXT.md](CONTEXT.md) for the full glossary (Prompt,
Category, Slug, Version, Live Version, Tombstone, Role) and [docs/adr/](docs/adr/) for the
architectural decisions behind it.

## Repository layout

- [`api/`](api/README.md) — FastAPI + SQLAlchemy (async) + PostgreSQL backend: the CRUD/versioning
  service itself.
- [`ui/`](ui/README.md) — Next.js (App Router) frontend for browsing, editing, and organizing
  Prompts.
- [`sdk/`](sdk/README.md) — a thin, read-only Python client for third-party developers who want to
  fetch Prompts from their own code.
- [`cli/`](cli/README.md) — `promptful-sync`, a local `import`/`export` CLI for teams running
  Promptful without a shared server, syncing Prompts through git-tracked files.

Each side is built and run independently — see its own README for setup, and
[CLAUDE.md](CLAUDE.md) for the full set of dev commands (tests, migrations, linting, etc.).

## License

Dual-licensed: everything outside Enterprise-marked files (any path containing `.ee.`) is available
under the Sustainable Use License, and those Enterprise-marked files require a Promptful Enterprise
License. See [LICENSE.md](LICENSE.md) and [LICENSE_EE.md](LICENSE_EE.md) for the full terms.
