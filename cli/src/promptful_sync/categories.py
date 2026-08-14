"""Auto-vivify Categories from a directory path, extending the same
materialized-path model ADR-0005 already established
(api/app/models/category.py) to Prompt File paths instead of combobox input.
"""

from __future__ import annotations

import uuid

from promptful_sync.client import SyncClient


async def ensure_category_path(client: SyncClient, category_path: str) -> uuid.UUID:
    """Return the id of the Category at `category_path` (e.g. "/sales/screening"),
    creating any missing ancestors along the way, top-down."""
    by_path = {category.path: category.id for category in await client.list_categories()}

    parent_id: uuid.UUID | None = None
    path_so_far = ""
    for segment in category_path.strip("/").split("/"):
        path_so_far += f"/{segment}"
        if path_so_far in by_path:
            parent_id = by_path[path_so_far]
            continue
        category = await client.create_category(slug_segment=segment, parent_id=parent_id)
        by_path[path_so_far] = category.id
        parent_id = category.id

    return by_path[category_path]
