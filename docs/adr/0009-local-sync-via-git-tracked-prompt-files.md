# Local instances sync via git-tracked Prompt Files instead of a shared server

Engineering teams running Promptful locally (e.g. via Docker) need the team's prompts to match
across everyone's machine without standing up an always-on shared instance. Rather than a
private-but-shared server (a non-public but still centrally-hosted Postgres/API), each developer's
Promptful instance is fully standalone. The team's current prompt set is represented as one
**Prompt File** per Prompt — `.prompt.md`, path mirroring the Slug, `role` in frontmatter, raw
`text` as the body — committed to the one consuming application's own repository, next to the code
that calls it via the SDK. Two CLI operations move data between the file tree and the local
database, over HTTP against that same locally-running API (the consuming app already needs it up
for its own SDK calls, so this adds no new precondition): **Import** (Prompt Files → DB, replayed
through the existing create/update endpoints, so ADR-0001/0002/0003's invariants apply unchanged —
never delete, see Consequences) and **Export** (DB → Prompt Files, the inverse, including removing
files for slugs that no longer have a Live Version). Git — not Promptful — is the sync transport:
`git pull` distributes changes, commits
and PR review are the audit trail, and ordinary text-merge conflict resolution handles two people
editing the same Prompt File. Git history replaces Postgres's own Version sequence as *the*
version history for this workflow; a Prompt File carries no `id`, `version`, or `created_at`.

## Considered options

- **A private, non-public shared server** that local instances read from. Rejected: it trades
  "always publicly available" for "always available," still leaving the team owning uptime,
  backups, and access control for infrastructure whose only job is holding text.
- **A dedicated repo for Prompt Files**, separate from any consuming application. Rejected in
  favor of embedding in the one consuming application's repo — juggling an extra repo wasn't worth
  the dev-experience cost for a single-consumer setup. Revisit if a second consuming application
  needs the same prompts; the fallback there is pointing its Import/Export at a checkout of the
  first app's repo, not standing up a third repo.
- **Wipe-and-rebuild the local DB from files on every sync.** Rejected: it would erase local
  Version history on every pull and contradicts ADR-0001's "no row is ever updated or destroyed"
  invariant. Import instead diffs and replays through the real API, so a sync is just another
  writer, not a parallel write path.

## Consequences

- **No conflict detection between a local edit and an Import.** Whichever runs more recently on
  that machine wins; an unexported local edit can be silently overwritten. Deliberately deferred —
  a three-way "Sync Baseline" comparison was designed and set aside until this is a real, reported
  problem, not a hypothetical one.
- **Import never deletes, only Export does.** Export's delete signal is unambiguous (a Live
  Version either currently exists or it doesn't); Import's would be a missing file, which is
  ambiguous between "never exported yet" and "deleted upstream" without tracking prior state —
  the same category of complexity as the Sync Baseline above. A teammate's deletion doesn't remove
  your local copy automatically; you'll notice the file is gone from git and can clean up by hand.
- **Categories with zero Prompts don't sync.** Git doesn't track empty directories, and Category is
  implied purely by directory structure, so an empty Category `export`s to nothing and never
  reaches a teammate's `import`. Accepted: an empty Category is inert either way, and adding one
  Prompt to it fixes this for free.
- **This doesn't yet address the Owner/multi-tenant model** CLAUDE.md describes as target design
  (prompts belonging to a person or company) — it isn't built. "One repo per consuming app" is
  expected to extend cleanly to "one repo per Owner" later without rework.
