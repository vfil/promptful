# Mutations must sync every cached query that depends on the entity, not just list queries

`PromptForm`'s update mutation invalidated the `["prompts"]` list query on success but never
touched `["prompt", slug]`, the query the edit page reads. Since the frontend's `QueryClient` is
created once and lives for the whole SPA session (`app/providers.tsx`), that per-slug cache entry
kept serving the pre-edit Version indefinitely — visibly reproducible as "edit a prompt, go back
to the list, click Edit again, see the old text; only a hard refresh shows the latest Version."

Going forward, a mutation's `onSuccess` must update the cache for every query keyed off the
mutated entity, not only the list view. Prefer `queryClient.setQueryData(key, response)` using the
mutation's own response over `invalidateQueries` when the response already carries the
authoritative new state — it's immediately correct with no extra round trip, whereas invalidation
still serves stale cached data until a refetch completes. Reserve `invalidateQueries` for cases
where the mutation's response doesn't carry the full shape a dependent query needs.

This alone doesn't cover every staleness path — see the companion fix in `PromptForm`/`EditPrompt`
that remounts the form when the resolved Live Version's `id` changes, which also covers a
concurrent editor (ADR-0003) changing the same slug out from under an already-open edit page.
