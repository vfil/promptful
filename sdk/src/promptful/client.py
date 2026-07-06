from __future__ import annotations

import os
from datetime import datetime

import httpx

from promptful.exceptions import (
    PromptfulAPIError,
    PromptfulConnectionError,
    PromptNotFoundError,
)
from promptful.models import Prompt, PromptSummary

_BASE_URL_ENV_VAR = "PROMPTFUL_BASE_URL"


class Client:
    """A thin, read-only client for the Promptful API.

    Fetches Prompts by slug. Does not authenticate, cache, retry, or render
    Jinja2 template text — `text` is always returned raw, exactly as stored.
    These are deliberate v1 scope decisions; see sdk/README.md.
    """

    def __init__(self, base_url: str | None = None, *, timeout: float = 10.0) -> None:
        """Create a client bound to one Promptful API instance.

        Args:
            base_url: The API's base URL (e.g. "https://prompts.example.com").
                Falls back to the `PROMPTFUL_BASE_URL` environment variable if
                omitted.
            timeout: Per-request timeout in seconds, passed to the underlying
                httpx.Client.

        Raises:
            ValueError: Neither `base_url` nor `PROMPTFUL_BASE_URL` is set.
        """
        resolved = base_url or os.environ.get(_BASE_URL_ENV_VAR)
        if not resolved:
            raise ValueError(
                "base_url must be passed explicitly or set via the "
                f"{_BASE_URL_ENV_VAR} environment variable"
            )
        self._http = httpx.Client(base_url=resolved, timeout=timeout)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def get_prompt(self, slug: str) -> Prompt:
        """Fetch a Prompt's current Live Version by its full slug.

        Args:
            slug: Full slug, e.g. "/sales/screening/first-lead".

        Returns:
            The Prompt's current Live Version (raw, unrendered `text`).

        Raises:
            PromptNotFoundError: `slug` has no Live Version (never existed,
                wrong namespace, or Tombstoned).
            PromptfulAPIError: The API responded with an unexpected error status.
            PromptfulConnectionError: The API could not be reached.
        """
        response = self._get("/prompt", params={"slug": slug})
        if response.status_code == 404:
            raise PromptNotFoundError(slug)
        _raise_for_unexpected_status(response)
        return _prompt_from_json(response.json())

    def list_prompts(self) -> list[PromptSummary]:
        """List every Prompt's current Live Version (Tombstoned prompts excluded).

        Returns:
            One `PromptSummary` per Prompt (no `text`), alphabetical by slug.

        Raises:
            PromptfulAPIError: The API responded with an unexpected error status.
            PromptfulConnectionError: The API could not be reached.
        """
        response = self._get("/prompts")
        _raise_for_unexpected_status(response)
        return [_summary_from_json(item) for item in response.json()]

    def get_prompts(self, slugs: list[str]) -> list[Prompt | None]:
        """Fetch each slug's current Live Version in one round trip.

        Args:
            slugs: Full slugs to fetch. May contain duplicates; each
                occurrence gets its own entry in the result.

        Returns:
            A list the same length and order as `slugs`. `None` at a given
            position means that slug currently has no Live Version — a single
            miss does not fail the whole batch.

        Raises:
            PromptfulAPIError: `slugs` is empty, exceeds the API's max batch
                size, or the API responded with another unexpected error status.
            PromptfulConnectionError: The API could not be reached.
        """
        response = self._post("/prompts/batch", json={"slugs": slugs})
        _raise_for_unexpected_status(response)
        return [
            _prompt_from_json(item["prompt"]) if item["prompt"] is not None else None
            for item in response.json()
        ]

    def _get(self, path: str, **kwargs: object) -> httpx.Response:
        try:
            return self._http.get(path, **kwargs)
        except httpx.HTTPError as exc:
            raise PromptfulConnectionError(str(exc)) from exc

    def _post(self, path: str, **kwargs: object) -> httpx.Response:
        try:
            return self._http.post(path, **kwargs)
        except httpx.HTTPError as exc:
            raise PromptfulConnectionError(str(exc)) from exc


def _raise_for_unexpected_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = response.text
    if response.content:
        try:
            detail = response.json().get("detail", detail)
        except ValueError:
            pass
    raise PromptfulAPIError(response.status_code, detail)


def _prompt_from_json(data: dict) -> Prompt:
    return Prompt(
        id=data["id"],
        slug=data["slug"],
        leaf_slug=data["leaf_slug"],
        category_id=data["category_id"],
        version=data["version"],
        text=data["text"],
        is_deleted=data["is_deleted"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _summary_from_json(data: dict) -> PromptSummary:
    return PromptSummary(
        id=data["id"],
        slug=data["slug"],
        leaf_slug=data["leaf_slug"],
        category_id=data["category_id"],
        version=data["version"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )
