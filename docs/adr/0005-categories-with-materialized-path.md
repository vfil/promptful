# Categories with materialized path replace freeform slug entry

Prompts were originally identified by a freeform slug (`/sales/screening/first-lead`) that the
user typed in full. This was error-prone and produced poor UX on creation. We introduced a
first-class `Category` entity that captures the namespace hierarchy, letting users pick or
create categories via a combobox rather than typing a raw path.

**Why materialized path on Category (not computed at query time):**
Three approaches were considered:

1. Store the full slug on the Prompt row and use `LIKE` prefix queries for category listing.
2. Store only `leaf_slug + category_id` on Prompt and walk the tree with a recursive CTE on
   every read.
3. Store `leaf_slug + category_id` on Prompt, and store the full `path` on the Category row
   (materialized at creation time).

We chose option 3. Because Category names are immutable and Categories cannot be deleted while
they have children, the materialized `path` column is safe from staleness. This gives O(1) full
slug derivation (single join to Category), clean `WHERE category_id = ?` listing for direct
children, and subtree queries via `WHERE category.path LIKE '/sales/%'` — all without recursive
queries on the read path.

**Why `NULLS NOT DISTINCT` unique index on `(slug_segment, parent_id)`:**
Standard `UNIQUE(slug_segment, parent_id)` does not prevent two root Categories with the same
`slug_segment` because `NULL != NULL` in SQL. A single `NULLS NOT DISTINCT` unique index
covers both root and non-root Categories cleanly. The project runs unversioned `postgres`
(latest) which is Postgres 15+, so this feature is available.
