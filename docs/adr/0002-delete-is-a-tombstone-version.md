# Delete appends a Tombstone version, it never removes rows

`DELETE` does not destroy data. It inserts a new Version row with `is_deleted = true` (a
Tombstone) at the next version number for that slug. A slug-based read with no version pinned
returns 404 whenever the slug has no Live Version (see [CONTEXT.md](../../CONTEXT.md)) — i.e.
its highest-version row is a Tombstone — with no fallback search to an earlier, non-Tombstone
row. An explicit `?version=N` or `GET /prompt/{id}` still resolves a Tombstoned or historical row
directly, since that's a deliberate request rather than the "give me what's current" path. Re-creating a
deleted slug goes through `POST /prompt/create` again and continues the version counter — it
never resets to 1 — so a delete/recreate cycle leaves a complete, gapless history.

This was chosen over (a) a slug-level soft-delete flag, which would need to live outside the
per-version row model and reintroduce the pointer/consistency problem ADR-0001 avoided, and
(b) physical row deletion, which directly contradicts the "full history is kept per slug"
requirement. Physical deletion of a specific version (e.g. to purge an accidentally-leaked
secret) is a deliberately separate, more dangerous operation, out of scope for this endpoint.
