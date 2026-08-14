"""Integration tests for `import` — Prompt Files on disk into the local
database, over HTTP against the real app in-process (tests/conftest.py's
`sync_client` fixture) and the `app_test` database.

See product/ai-specs/local-prompt-sync.md and
docs/adr/0009-local-sync-via-git-tracked-prompt-files.md.
"""

from pathlib import Path

from promptful_sync.client import SyncClient
from promptful_sync.import_cmd import run_import
from promptful_sync.prompt_file import write_prompt_file


async def test_import_creates_missing_categories_and_a_new_prompt(
    sync_client: SyncClient, tmp_path: Path
) -> None:
    write_prompt_file(
        tmp_path / "sales" / "screening" / "first-lead.prompt.md",
        role="system",
        text="You are a helpful assistant.\n",
    )

    result = await run_import(sync_client, tmp_path)

    assert result.created == ["/sales/screening/first-lead"]
    assert result.updated == []
    assert result.errors == []

    current = await sync_client.get_prompts_batch(["/sales/screening/first-lead"])
    prompt = current["/sales/screening/first-lead"]
    assert prompt is not None
    assert prompt.role == "system"
    assert prompt.text == "You are a helpful assistant.\n"


async def test_import_updates_when_text_differs(sync_client: SyncClient, tmp_path: Path) -> None:
    path = tmp_path / "sales" / "first-lead.prompt.md"
    write_prompt_file(path, role="system", text="Original text.\n")
    await run_import(sync_client, tmp_path)

    write_prompt_file(path, role="system", text="Updated text.\n")
    result = await run_import(sync_client, tmp_path)

    assert result.updated == ["/sales/first-lead"]
    assert result.created == []
    assert result.errors == []

    current = await sync_client.get_prompts_batch(["/sales/first-lead"])
    assert current["/sales/first-lead"].text == "Updated text.\n"


async def test_import_reports_role_mismatch_without_applying_or_crashing(
    sync_client: SyncClient, tmp_path: Path
) -> None:
    mismatched = tmp_path / "sales" / "first-lead.prompt.md"
    write_prompt_file(mismatched, role="system", text="Original text.\n")
    await run_import(sync_client, tmp_path)

    # Change the file's role (server disagrees) and add an unrelated new file
    # in the same run — the mismatch must not block the other one.
    write_prompt_file(mismatched, role="user", text="Changed text too.\n")
    write_prompt_file(
        tmp_path / "sales" / "second-lead.prompt.md", role="system", text="Second.\n"
    )

    result = await run_import(sync_client, tmp_path)

    assert result.created == ["/sales/second-lead"]
    assert result.updated == []
    assert len(result.errors) == 1
    assert "/sales/first-lead" in result.errors[0]

    current = await sync_client.get_prompts_batch(["/sales/first-lead", "/sales/second-lead"])
    assert current["/sales/first-lead"].role == "system"
    assert current["/sales/first-lead"].text == "Original text.\n"
    assert current["/sales/second-lead"] is not None


async def test_import_skips_when_file_matches_server(
    sync_client: SyncClient, tmp_path: Path
) -> None:
    path = tmp_path / "sales" / "first-lead.prompt.md"
    write_prompt_file(path, role="system", text="Same text.\n")
    await run_import(sync_client, tmp_path)

    result = await run_import(sync_client, tmp_path)

    assert result.skipped == ["/sales/first-lead"]
    assert result.created == []
    assert result.updated == []
    assert result.errors == []


async def test_import_leaves_local_prompt_alone_when_its_file_is_gone(
    sync_client: SyncClient, tmp_path: Path
) -> None:
    path = tmp_path / "sales" / "first-lead.prompt.md"
    write_prompt_file(path, role="system", text="Still here.\n")
    await run_import(sync_client, tmp_path)

    path.unlink()
    result = await run_import(sync_client, tmp_path)

    assert result.created == []
    assert result.updated == []
    assert result.skipped == []
    assert result.errors == []

    current = await sync_client.get_prompts_batch(["/sales/first-lead"])
    assert current["/sales/first-lead"] is not None
    assert current["/sales/first-lead"].text == "Still here.\n"
