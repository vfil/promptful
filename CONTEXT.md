# Promptful

A CRUD service for managing LLM prompts for private persons and companies, with full history
versioning per slug and slug-based namespacing.

## Language

**Prompt**:
The namespace-level entity addressed by a Slug. Persists across all its Versions, including
after it has been deleted (Tombstoned) — a Prompt's history is never destroyed.
_Avoid_: prompt entity (when referring to a single row)

**Slug**:
A hierarchical, URL-path-like identifier (e.g. `/sales/screening/first-lead`) that addresses a
Prompt and implies its namespace via path segments. Fixed once a Prompt exists at it — there is
no rename/move operation.
_Avoid_: path, key, name

**Version**:
One immutable row for a Prompt: a specific `(slug, version number)` pair with its own `id`,
`text`, `is_deleted` flag, and `created_at`. Created by every Create/Update/Delete operation;
never modified or overwritten in place. This is what "an instance of a prompt ready to be used
in an agentic workflow" refers to.
_Avoid_: prompt entity (when referring to a row), revision

**Live Version**:
The Version at a Prompt's highest existing version number, if and only if that Version is not a
Tombstone. A Prompt whose highest-version row is a Tombstone has no Live Version — there is no
falling back to an earlier, non-Tombstone Version. What a slug-based read resolves to when no
specific version is requested; absence of a Live Version is a 404.
_Avoid_: latest, active, current

**Tombstone**:
A Version created by a delete operation (`is_deleted = true`, no usable `text`). Deleting a
Prompt never removes rows — it appends a Tombstone Version on top of the existing history.
_Avoid_: soft delete, deactivated
