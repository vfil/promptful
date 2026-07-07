# Prompt gets a persisted, immutable `role` field (system/user/assistant)

Prompts had no way to express which LLM message position their `text` fills. We added `role`
(`system` | `user` | `assistant`) as a required field on Prompt, fixed at creation alongside
`leaf_slug` and `category_id` — `PromptUpdate` does not accept it, matching the existing
invariant that only `text` varies across a Prompt's Versions (see
[CONTEXT.md](../../CONTEXT.md)).

We considered two alternatives and rejected both. Keeping `role` as UI-only guidance with no
schema change would have been simpler, but it gives the UI no way to drive contextual
guidance/highlighting and gives future consumers (SDK, other tooling) no way to filter or
reason about a Prompt's intended usage. Making `role` editable per-Version like `text` would let
a single Prompt's history target different message positions over time, which no consumer could
reason about consistently — `role` describes what a Prompt fundamentally *is*, not how its
content evolves.

There's no real data to preserve yet (two migrations total at the time of this change), so the
column is added as `NOT NULL` with no default and no backfill — a clean migration rather than a
defensive one.
