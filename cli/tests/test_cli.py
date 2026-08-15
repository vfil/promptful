"""Unit tests for CLI argument parsing — pure, no database, no HTTP.

See product/ai-specs/local-prompt-sync.md.
"""

from pathlib import Path

from promptful_sync.cli import parse_args


def test_parse_args_dispatches_import_with_its_directory() -> None:
    args = parse_args(["import", "some/prompts"])

    assert args.command == "import"
    assert args.directory == Path("some/prompts")


def test_parse_args_dispatches_export_with_its_directory() -> None:
    args = parse_args(["export", "some/prompts"])

    assert args.command == "export"
    assert args.directory == Path("some/prompts")
