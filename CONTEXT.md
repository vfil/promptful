# Promptful

A CRUD service for managing LLM prompts for private persons and companies, with full history
versioning per slug and category-based namespacing.

## Language

**Prompt**:
The entity addressed by a Slug, belonging to exactly one Category. Persists across all its
Versions, including after it has been deleted (Tombstoned) — a Prompt's history is never
destroyed. A Prompt cannot be moved to a different Category after creation.
_Avoid_: prompt entity (when referring to a single row)

**Category**:
A named grouping that organises Prompts hierarchically. A Category has one Slug Segment and an
optional parent Category; if no parent is set, it is a root Category. A Category cannot be
renamed or deleted while it has child Categories or Prompts.
_Avoid_: namespace, folder, group

**Slug Segment**:
The slug-safe name of a Category (e.g. `screening`). Lowercase alphanumeric with hyphens, no
slashes. Immutable once the Category is created.
_Avoid_: segment, name, label

**Category Path**:
The full hierarchical address of a Category (e.g. `/sales/screening`), assembled by joining its
ancestor Slug Segments with `/`. Immutable because Slug Segments never change.
_Avoid_: path, full path, category slug

**Leaf Slug**:
The slug-safe local name of a Prompt within its Category (e.g. `first-lead`). No slashes.
Together with the Category Path it forms the full Slug. Fixed at Prompt creation.
_Avoid_: name, prompt name, local slug

**Slug**:
The full address of a Prompt (e.g. `/sales/screening/first-lead`), derived as
`Category Path + "/" + Leaf Slug`. Stable and globally unique — neither the Category nor the
Leaf Slug can change after creation.
_Avoid_: path, key, name

**Version**:
One immutable row for a Prompt, identified by its `(Leaf Slug, Category, version number)`
triple, with its own `id`, `text`, `is_deleted` flag, and `created_at`. Created by every
Create/Update/Delete operation; never modified or overwritten in place.
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
