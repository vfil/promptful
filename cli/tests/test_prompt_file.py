"""Unit tests for Prompt File read/write — pure functions, no database, no HTTP.

See product/ai-specs/local-prompt-sync.md and CONTEXT.md's "Local Sync" section.
"""

from pathlib import Path

from promptful_sync.prompt_file import (
    parse_prompt_file,
    path_to_slug,
    slug_to_path,
    write_prompt_file,
)


def test_write_then_parse_round_trips_role_and_text(tmp_path: Path) -> None:
    path = tmp_path / "first-lead.prompt.md"

    write_prompt_file(path, role="system", text="You are a helpful assistant.\n")
    parsed = parse_prompt_file(path)

    assert parsed.role == "system"
    assert parsed.text == "You are a helpful assistant.\n"


def test_slug_and_path_round_trip_for_a_nested_slug(tmp_path: Path) -> None:
    slug = "/sales/screening/first-lead"

    path = slug_to_path(slug, root=tmp_path)

    assert path == tmp_path / "sales" / "screening" / "first-lead.prompt.md"
    assert path_to_slug(path, root=tmp_path) == slug
