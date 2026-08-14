"""`export`: local Live Versions -> Prompt Files on disk, ready to commit.

Also removes a Prompt File whose slug no longer has a Live Version. Unlike
Import's delete case, this direction's signal is unambiguous — a Live Version
either currently exists or it doesn't — so no state tracking is needed to do
it safely. See ADR-0009.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from promptful_sync.client import SyncClient
from promptful_sync.prompt_file import (
    parse_prompt_file,
    path_to_slug,
    slug_to_path,
    write_prompt_file,
)


@dataclass
class ExportResult:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


async def run_export(client: SyncClient, target_dir: Path) -> ExportResult:
    result = ExportResult()

    live_slugs = await client.list_live_slugs()
    live = await client.get_prompts_batch(live_slugs) if live_slugs else {}

    existing_files = (
        {path_to_slug(f, root=target_dir): f for f in target_dir.rglob("*.prompt.md")}
        if target_dir.exists()
        else {}
    )

    for slug in live_slugs:
        prompt = live[slug]
        path = slug_to_path(slug, root=target_dir)
        if slug not in existing_files:
            write_prompt_file(path, role=prompt.role, text=prompt.text)
            result.created.append(slug)
            continue
        parsed = parse_prompt_file(path)
        if parsed.role != prompt.role or parsed.text != prompt.text:
            write_prompt_file(path, role=prompt.role, text=prompt.text)
            result.updated.append(slug)
        else:
            result.skipped.append(slug)

    live_set = set(live_slugs)
    for slug, path in existing_files.items():
        if slug not in live_set:
            path.unlink()
            result.deleted.append(slug)

    return result
