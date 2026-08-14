"""`import`: Prompt Files on disk -> the local database, replayed through the
same create/update operations the UI uses. Never deletes — see ADR-0009's
Consequences (Import's "file is missing" signal is ambiguous between "never
exported" and "deleted upstream" without tracking prior state, so it's simply
not acted on).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from promptful_sync.categories import ensure_category_path
from promptful_sync.client import SyncClient
from promptful_sync.prompt_file import parse_prompt_file, path_to_slug


@dataclass
class ImportResult:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _split_slug(slug: str) -> tuple[str, str]:
    """slug -> (category_path, leaf_slug), e.g. "/sales/x" -> ("/sales", "x")."""
    category_path, _, leaf_slug = slug.rpartition("/")
    return category_path, leaf_slug


async def run_import(client: SyncClient, source_dir: Path) -> ImportResult:
    result = ImportResult()
    files = sorted(source_dir.rglob("*.prompt.md"))
    if not files:
        return result

    by_slug = {path_to_slug(f, root=source_dir): parse_prompt_file(f) for f in files}

    category_ids: dict[str, uuid.UUID] = {}
    for slug in by_slug:
        category_path, _ = _split_slug(slug)
        if category_path not in category_ids:
            category_ids[category_path] = await ensure_category_path(client, category_path)

    current = await client.get_prompts_batch(list(by_slug))

    for slug, parsed in by_slug.items():
        category_path, leaf_slug = _split_slug(slug)
        existing = current[slug]

        if existing is None:
            await client.create_prompt(
                leaf_slug=leaf_slug,
                category_id=category_ids[category_path],
                role=parsed.role,
                text=parsed.text,
            )
            result.created.append(slug)
        elif existing.role != parsed.role:
            result.errors.append(
                f"{slug}: file role '{parsed.role}' != server role '{existing.role}' "
                "— role is immutable, resolve by hand"
            )
        elif existing.text != parsed.text:
            await client.update_prompt(id=existing.id, text=parsed.text)
            result.updated.append(slug)
        else:
            result.skipped.append(slug)

    return result
