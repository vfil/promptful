"""CLI entrypoint: `promptful-sync import <dir>` / `promptful-sync export <dir>`.

Talks to an already-running local API over HTTP (PROMPTFUL_BASE_URL, same env
var name the SDK uses) — see product/ai-specs/local-prompt-sync.md and
docs/adr/0009-local-sync-via-git-tracked-prompt-files.md for why a running
server is a documented precondition, not something this tool starts itself.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx

from promptful_sync.client import SyncClient, SyncClientConnectionError
from promptful_sync.export_cmd import ExportResult, run_export
from promptful_sync.import_cmd import ImportResult, run_import

_BASE_URL_ENV_VAR = "PROMPTFUL_BASE_URL"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="promptful-sync")
    parser.add_argument(
        "--base-url", default=None, help=f"Overrides the {_BASE_URL_ENV_VAR} env var."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser(
        "import", help="Prompt Files on disk -> local database (never deletes)."
    )
    import_parser.add_argument("directory", type=Path)

    export_parser = subparsers.add_parser(
        "export", help="Local database -> Prompt Files on disk."
    )
    export_parser.add_argument("directory", type=Path)

    return parser.parse_args(argv)


def _resolve_base_url(cli_value: str | None) -> str:
    resolved = cli_value or os.environ.get(_BASE_URL_ENV_VAR)
    if not resolved:
        raise SystemExit(
            f"--base-url must be passed explicitly or set via the {_BASE_URL_ENV_VAR} "
            "environment variable"
        )
    return resolved


def _print_import_result(result: ImportResult) -> None:
    print(
        f"import: {len(result.created)} created, {len(result.updated)} updated, "
        f"{len(result.skipped)} unchanged, {len(result.errors)} errors"
    )
    for slug in result.created:
        print(f"  created {slug}")
    for slug in result.updated:
        print(f"  updated {slug}")
    for error in result.errors:
        print(f"  error   {error}")


def _print_export_result(result: ExportResult) -> None:
    print(
        f"export: {len(result.created)} created, {len(result.updated)} updated, "
        f"{len(result.deleted)} deleted, {len(result.skipped)} unchanged"
    )
    for slug in result.created:
        print(f"  created {slug}")
    for slug in result.updated:
        print(f"  updated {slug}")
    for slug in result.deleted:
        print(f"  deleted {slug}")


async def _run(args: argparse.Namespace) -> int:
    base_url = _resolve_base_url(args.base_url)
    async with httpx.AsyncClient(base_url=base_url) as http:
        client = SyncClient(http)
        try:
            if args.command == "import":
                import_result = await run_import(client, args.directory)
                _print_import_result(import_result)
                return 1 if import_result.errors else 0

            export_result = await run_export(client, args.directory)
            _print_export_result(export_result)
            return 0
        except SyncClientConnectionError as exc:
            print(f"error: could not reach the API at {base_url} — is it running? ({exc})")
            return 1


def main() -> None:
    args = parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
