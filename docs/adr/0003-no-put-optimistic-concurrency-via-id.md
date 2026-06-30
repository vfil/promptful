# No PUT; create and update are both POST, gated by id-based optimistic concurrency

`/prompt` has no `PUT`. Create is `POST /prompt/create` (slug, text in body; 409 if the slug
currently has a Live Version). Update is `POST /prompt/{id}` (text in body), where `{id}` must be
the `id` of the slug's current Live Version — if it isn't (another write landed since the caller
last read that version, or the id is stale/unknown), the request is rejected with 409 rather than
silently appending alongside. Delete (`DELETE /prompt/{id}`) uses the same `{id}`-must-be-Live
check.

This was a deliberate deviation from standard REST verb usage, chosen for two reasons: Create and
Update perform the same underlying write (insert the next version row), so the only thing that
can actually distinguish them is a precondition check on what currently exists — `PUT`'s
conventional idempotent-replace semantics don't map cleanly onto an insert-only model. And using
`{id}` (rather than a bare slug) as the update/delete target doubles as a compare-and-swap token,
preventing two concurrent writers (e.g. two agentic workflows editing the same slug) from
silently clobbering each other's changes — a real risk once multiple processes can write to the
same Prompt.
