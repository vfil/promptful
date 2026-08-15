"""Integration tests for `export` — local Live Versions to Prompt Files on
disk, over HTTP against the real app in-process (tests/conftest.py's
`sync_client` fixture) and the `app_test` database.

See product/ai-specs/local-prompt-sync.md and
docs/adr/0009-local-sync-via-git-tracked-prompt-files.md.
"""

from pathlib import Path

from httpx import AsyncClient

from promptful_sync.client import SyncClient
from promptful_sync.export_cmd import run_export
from promptful_sync.import_cmd import run_import
from promptful_sync.prompt_file import parse_prompt_file, write_prompt_file


async def test_export_writes_a_file_for_a_live_prompt_with_none_locally(
    sync_client: SyncClient, tmp_path: Path
) -> None:
    setup_dir = tmp_path / "_setup"
    write_prompt_file(setup_dir / "sales" / "first-lead.prompt.md", role="system", text="Hello.\n")
    await run_import(sync_client, setup_dir)

    export_dir = tmp_path / "export"
    result = await run_export(sync_client, export_dir)

    assert result.created == ["/sales/first-lead"]
    parsed = parse_prompt_file(export_dir / "sales" / "first-lead.prompt.md")
    assert parsed.role == "system"
    assert parsed.text == "Hello.\n"


async def test_export_overwrites_a_file_that_differs(
    sync_client: SyncClient, tmp_path: Path
) -> None:
    setup_dir = tmp_path / "_setup"
    write_prompt_file(setup_dir / "sales" / "first-lead.prompt.md", role="system", text="V1.\n")
    await run_import(sync_client, setup_dir)

    export_dir = tmp_path / "export"
    await run_export(sync_client, export_dir)

    current = await sync_client.get_prompts_batch(["/sales/first-lead"])
    await sync_client.update_prompt(id=current["/sales/first-lead"].id, text="V2.\n")

    result = await run_export(sync_client, export_dir)

    assert result.updated == ["/sales/first-lead"]
    parsed = parse_prompt_file(export_dir / "sales" / "first-lead.prompt.md")
    assert parsed.text == "V2.\n"


async def test_export_deletes_a_file_whose_slug_is_no_longer_live(
    client: AsyncClient, sync_client: SyncClient, tmp_path: Path
) -> None:
    setup_dir = tmp_path / "_setup"
    write_prompt_file(setup_dir / "sales" / "first-lead.prompt.md", role="system", text="Bye.\n")
    await run_import(sync_client, setup_dir)

    export_dir = tmp_path / "export"
    await run_export(sync_client, export_dir)
    path = export_dir / "sales" / "first-lead.prompt.md"
    assert path.exists()

    current = await sync_client.get_prompts_batch(["/sales/first-lead"])
    # Tombstone it directly over the raw client — deleting isn't part of the
    # sync client's own surface (see ADR-0009: import never deletes, and
    # export's own delete path works from `GET /prompts`, not a DELETE call).
    await client.delete(f"/prompt/{current['/sales/first-lead'].id}")

    result = await run_export(sync_client, export_dir)

    assert result.deleted == ["/sales/first-lead"]
    assert not path.exists()
