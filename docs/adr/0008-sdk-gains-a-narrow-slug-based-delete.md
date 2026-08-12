# SDK gains a narrow, slug-based `delete_prompt`, deliberately breaking "read-only"

The SDK `Client` was read-only by design (`get_prompt`, `get_prompts`, `list_prompts`) so
third-party integrations could never mutate prompt state. We're adding `delete_prompt(slug)` for
automation/cleanup scripts that need to remove prompts programmatically — a concrete need, not
parity for its own sake — while adding no other write path (no create/update via the SDK).

`delete_prompt` takes a `slug`, not the internal version `id`, matching every other SDK method's
ergonomics: it resolves the slug's current Live Version via the existing `GET /prompt` lookup,
then calls `DELETE /prompt/{id}`. That resolve-then-delete is two round trips with a race window —
a concurrent writer can land a new version in between, and the `DELETE` call will 409 (ADR-0003).
Rather than retry silently, which would contradict the `Client` docstring's existing "does not ...
retry" guarantee, this raises a new `PromptConflictError(slug)` and leaves retrying to the caller.
Deleting a slug that already has no Live Version raises the existing `PromptNotFoundError`,
symmetric with `get_prompt`'s behavior for the same condition, rather than silently succeeding as
a no-op.

`delete_prompt` returns `None`. The backend's response is the newly-created Tombstone version, but
the SDK's `Prompt` dataclass is documented as "a prompt's current Live Version" — a Tombstone is
the opposite of that — so reusing `Prompt` for it would stretch that meaning rather than clarify
it.
