# Versions are immutable rows, identified by (slug, version)

We need full history per Prompt slug. Rather than a `prompts` table holding current state plus a
separate `prompt_versions` history table, `prompts` holds one row per Version directly, keyed by
`(slug, version)` with `version` a per-slug incrementing integer computed at write time
(`MAX(version) + 1`). No row is ever updated after insert; Create, Update, and Delete (see
[ADR-0002](./0002-delete-is-a-tombstone-version.md)) all append a new row. "The current Prompt at
a slug" is resolved at read time by taking the row at `MAX(version)` for that slug and checking
whether it's a Tombstone — there is no separate pointer/flag column tracking "latest," and no
search backward past a Tombstone to an earlier non-Tombstone row.

A two-table split (identity table + version table) was considered and rejected for this first
cut: it adds a join and a second write path for no benefit until slug-level metadata (tags,
ownership) needs to exist independently of any version, which isn't a current requirement.
