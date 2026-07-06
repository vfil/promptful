#!/usr/bin/env python3
"""Quickstart: exercise every promptful.Client method against a running API.

Standalone and not run by the test suite — if it breaks, it's telling you the
SDK's usage pattern has drifted from this example, not failing CI silently.

Usage:
    PROMPTFUL_BASE_URL=http://localhost:8001 python examples/quickstart.py
    python examples/quickstart.py http://localhost:8001
"""

from __future__ import annotations

import sys

from promptful import Client, PromptNotFoundError


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else None

    with Client(base_url=base_url) as client:
        print("Listing prompts...")
        summaries = client.list_prompts()
        if not summaries:
            print("  (no prompts yet — create one via the API first to see more)")
        for summary in summaries:
            print(f"  {summary.slug} (v{summary.version})")

        if summaries:
            slug = summaries[0].slug

            print(f"\nFetching a single prompt: {slug}")
            prompt = client.get_prompt(slug)
            print(f"  text: {prompt.text!r}")

            print("\nFetching a batch (mixing a real slug with a missing one)...")
            requested = [slug, "/does/not-exist"]
            results = client.get_prompts(requested)
            for requested_slug, result in zip(requested, results):
                status = "found" if result is not None else "not found"
                print(f"  {requested_slug}: {status}")

        print("\nHandling a not-found slug directly...")
        try:
            client.get_prompt("/does/not-exist")
        except PromptNotFoundError as exc:
            print(f"  caught expected error: {exc}")


if __name__ == "__main__":
    main()
