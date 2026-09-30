# Backlog

Prioritised list of features to build next, derived from the specs in
[`product/ai-specs/`](product/ai-specs/), the ADRs in [`docs/adr/`](docs/adr/), the target domain
model in [CLAUDE.md](CLAUDE.md) / [CONTEXT.md](CONTEXT.md), and the current state of the code.

Every item below is something a spec or ADR explicitly marked **deferred / out of scope / revisit
later**, or a gap between the target domain model and what's built.

## Already shipped (for context)

| Area | What exists |
|---|---|
| API | Prompt CRUD over immutable Version rows (ADR-0001), Tombstone delete (ADR-0002), id-gated optimistic concurrency (ADR-0003), Jinja2 syntax validation (ADR-0004), Categories with materialized path (ADR-0005), immutable Role (ADR-0007), `GET /prompts` list + `POST /prompts/batch` |
| UI | Prompt list (home), create page with Category combobox, edit page with rich Jinja2 editor + role guidance, delete with confirmation |
| SDK | Read-only sync client (`get_prompt`, `get_prompts`, `list_prompts`) + narrow `delete_prompt` (ADR-0008) |
| CLI | `promptful-sync import` / `export` of git-tracked Prompt Files (ADR-0009, ADR-0010) |

## Priority legend

- **P0** — the product's core promise isn't met without it, or it gets much more expensive later.
- **P1** — high-value features the domain model already calls for.
- **P2** — solid improvements; build once P0/P1 are in.
- **P3** — nice-to-have or "revisit when a real need shows up" (per the ADRs).

---

## P0 — Core promise and foundations

### 1. Version history: browse, view, diff, restore

"Every prompt keeps a full version history" is the product's headline, but today nobody can see it:
[add-prompt-endpoint.md](product/ai-specs/add-prompt-endpoint.md) deferred listing versions for a
slug, so a caller can only reach versions whose `id`/`version` it already knows.

- API: `GET /prompt/history?slug=...` → every Version for the slug (Tombstones included),
  newest first, without `text` by default (same trade-off as `GET /prompts`).
- UI: a history panel on the edit page — version number, created_at, Tombstone marker; click to
  view a read-only past Version (`GET /prompt?slug=&version=` already exists).
- UI: side-by-side / inline diff between any two Versions.
- Restore: "restore this version" = `POST /prompt/{live_id}` with the old `text` — a new Version,
  not a rewind, so ADR-0001/0003 hold unchanged. Also covers un-deleting a Tombstoned slug via
  `POST /prompt/create` with the last non-Tombstone text.
- SDK: optional `get_prompt(slug, version=N)` for pinning a specific Version in production code.

### 2. Owner model (person / company) and scoping

CLAUDE.md says ownership "should be a first-class part of any schema or API design", and every spec
so far has deferred it ([add-categories.md](product/ai-specs/add-categories.md),
[add-prompt-endpoint.md](product/ai-specs/add-prompt-endpoint.md), ADR-0009). Each new table built
without it is another retrofit, and the "no production data yet — no data migration needed" window
used by add-categories won't last. Do this before Tags/Search.

- `owners` table (`kind: person | company`), `owner_id` on `categories` (prompts inherit it via
  their Category).
- Uniqueness becomes per-owner: sibling Slug Segments unique within an owner; Slugs unique within
  an owner, not globally.
- Every read/write endpoint scoped to the caller's owner. Needs an ADR: how the owner appears in
  the address (`/{owner}/sales/...` vs. implied by credentials).
- Company membership (person ↔ company) with at least a read/write split.

### 3. Authentication

Prerequisite for #2 to mean anything; today the API is open to anyone who can reach it.

- API keys (per owner, revocable) for SDK and CLI — both already read `PROMPTFUL_BASE_URL`; add a
  `PROMPTFUL_API_KEY` alongside it.
- Session login for the UI.
- CORS allow-list moved from the hardcoded `http://localhost:3001` in `api/app/main.py` into
  settings.

### 4. Bootstrap / config cleanup (small, do first)

CLAUDE.md warns the skeleton was copied from another project. Concrete leftovers found:

- `api/docker-compose.yml`: project/service names `ply_project` / `ply_db`, comments about
  `doc_import`, `snapshot.sql` and a non-existent "ADR-0004 database snapshot" — remove.
- CLAUDE.md says Postgres is on `:5432` with password `example`; compose and
  `api/app/core/config.py` actually use `:5433` / `ply_example`. Pick one and fix the docs.
- `ui/lib/api.ts` defaults `NEXT_PUBLIC_API_URL` to `http://localhost:8000`, but CLAUDE.md runs the
  API on `8001` because 8000 conflicts locally. Align the default or ship a `ui/.env.example`.

---

## P1 — Domain-model features

### 5. Tags

In CLAUDE.md's domain model ("free-form labels … orthogonal to the slug/namespace hierarchy"), not
yet in any spec. Needs a decision/ADR first: are tags per-Prompt (mutable, outside the Version
history) or per-Version (immutable, part of the snapshot)? Per-Prompt is the likelier fit, since
retagging shouldn't create a new Version.

- API: add/remove tags on a Prompt; filter `GET /prompts?tag=...`.
- UI: tag chips on list and edit page; tag filter on the list.
- SDK: `list_prompts(tag=...)`.
- CLI: tags in Prompt File frontmatter (ADR-0009 currently allows only `role` — update it).

### 6. Search and filtering on the prompt list

`GET /prompts` returns every live Prompt with no filtering or pagination.

- Filters: Category Path prefix (namespace browsing — "everything under `/sales`"), role, tag,
  free-text over slug and `text`.
- Pagination (cursor or limit/offset) — required before anyone has more than a few hundred prompts.
- UI: search box + filters; optional tree view by Category.

### 7. Category management

[add-categories.md](product/ai-specs/add-categories.md) lists "Category delete (requires its own
management UI)" as out of scope; the 409 rule (no delete while children or live Prompts) is
already specified.

- `DELETE /categories/{id}` with the 409 rule.
- A Category management page: tree view, create child, delete empty.
- Rename/move stays out: Slug Segments are immutable by design (Slug stability).

### 8. Jinja2 rendering / preview

ADR-0004 kept rendering out of scope (validate only). Consumers render on their own side today.

- UI: "preview" panel — detect template variables, let the user fill them, render client-side or
  via a sandboxed `POST /prompt/render`.
- SDK: `prompt.render(**vars)` helper using a sandboxed Jinja2 environment, so every consumer
  doesn't reimplement it.
- API: expose the variable list per Version (derived from the template AST) — useful for the UI
  form and for SDK type hints.

---

## P2 — Robustness and developer experience

### 9. Hard delete (purge a Version)

ADR-0002 defers physically deleting a specific Version (e.g. a leaked secret in a prompt). Needs
its own ADR: admin-only, audited, explicitly breaks ADR-0001's "never destroyed" invariant for that
one row, and must handle the gap it leaves in the version sequence.

### 10. Sync CLI conflict detection (Sync Baseline)

ADR-0009: "Whichever runs more recently wins; an unexported local edit can be silently
overwritten." A three-way Sync Baseline was designed and parked "until this is a real, reported
problem." Promote when a team reports lost edits.

### 11. Sync CLI propagating deletes on import

ADR-0009: import never deletes because a missing file is ambiguous without tracking prior state.
Falls out naturally from #10's baseline — schedule together.

### 12. Publish the SDK and CLI

Both ship as git/path dependencies only ([sdk/README.md](sdk/README.md)). Publish to PyPI with
versioning, a changelog, and a CI release job.

### 13. CI

No `.github/` workflows exist. Run `api` / `sdk` / `cli` pytest against a Postgres service
container, plus `pnpm lint`, `pnpm typecheck` and UI tests, on every PR.

### 14. Containerised local stack

Out of scope in [local-prompt-sync.md](product/ai-specs/local-prompt-sync.md). A `docker compose up`
that runs Postgres + migrations + API + UI would make the local-sync workflow (ADR-0009) one
command for new team members.

---

## P3 — Later / revisit on demand

### 15. Environment labels / pinning

Label a specific Version (`production`, `staging`) and let the SDK fetch by label instead of Live
Version, so editing a prompt doesn't instantly change production behaviour.

### 16. Multiple consuming apps for local sync

ADR-0009: "Revisit if a second consuming application needs the same prompts" — expected to extend
to "one repo per Owner" once #2 lands.

### 17. Automatic sync triggers

Out of scope in local-prompt-sync.md: file watcher / git hook / daemon. Manual commands only until
someone asks.

### 18. Audit trail of who changed what

Once #3 exists, record the author on every Version row (`created_by`) and surface it in the
history view (#1).

### 19. Usage analytics

Which slugs/Versions the SDK actually fetches, and when — helps find dead prompts before deleting
them.
