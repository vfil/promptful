"""A small, self-contained HTTP client for `import`/`export`.

Deliberately independent of the `sdk` package — ADR-0008 keeps the SDK's public
surface narrow on purpose (no create/update), and this tool needs endpoints
(Categories, create, update) third-party SDK consumers never should touch.
Production points it at PROMPTFUL_BASE_URL; tests point the underlying
`httpx.AsyncClient` at the app in-process instead (see tests/conftest.py's
`client` fixture) — this class just wraps whichever `httpx.AsyncClient` it's
given.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx


class SyncClientConnectionError(Exception):
    """The local API (ADR-0009: a running server is a documented precondition
    for `import`/`export`) couldn't be reached — network, timeout, DNS, or
    simply not started yet."""


@dataclass
class Category:
    id: uuid.UUID
    slug_segment: str
    parent_id: uuid.UUID | None
    path: str


@dataclass
class ServerPrompt:
    id: uuid.UUID
    slug: str
    role: str
    text: str


class SyncClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def list_live_slugs(self) -> list[str]:
        response = await self._get("/prompts")
        return [item["slug"] for item in response.json()]

    async def list_categories(self) -> list[Category]:
        response = await self._get("/categories")
        return [_category_from_json(item) for item in response.json()]

    async def create_category(
        self, *, slug_segment: str, parent_id: uuid.UUID | None
    ) -> Category:
        response = await self._post(
            "/categories",
            json={
                "slug_segment": slug_segment,
                "parent_id": str(parent_id) if parent_id else None,
            },
        )
        return _category_from_json(response.json())

    async def get_prompts_batch(self, slugs: list[str]) -> dict[str, ServerPrompt | None]:
        response = await self._post("/prompts/batch", json={"slugs": slugs})
        return {item["slug"]: _server_prompt_from_json(item["prompt"]) for item in response.json()}

    async def create_prompt(
        self, *, leaf_slug: str, category_id: uuid.UUID, role: str, text: str
    ) -> ServerPrompt:
        response = await self._post(
            "/prompt/create",
            json={
                "leaf_slug": leaf_slug,
                "category_id": str(category_id),
                "role": role,
                "text": text,
            },
        )
        return _server_prompt_from_json(response.json())

    async def update_prompt(self, *, id: uuid.UUID, text: str) -> ServerPrompt:
        response = await self._post(f"/prompt/{id}", json={"text": text})
        return _server_prompt_from_json(response.json())

    async def _get(self, path: str) -> httpx.Response:
        return self._raise_for_status(await self._send(self._http.get, path))

    async def _post(self, path: str, *, json: dict) -> httpx.Response:
        return self._raise_for_status(await self._send(self._http.post, path, json=json))

    @staticmethod
    async def _send(method, path: str, **kwargs: object) -> httpx.Response:
        try:
            return await method(path, **kwargs)
        except httpx.HTTPError as exc:
            raise SyncClientConnectionError(f"{path}: {exc}") from exc

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> httpx.Response:
        response.raise_for_status()
        return response


def _category_from_json(data: dict) -> Category:
    return Category(
        id=uuid.UUID(data["id"]),
        slug_segment=data["slug_segment"],
        parent_id=uuid.UUID(data["parent_id"]) if data["parent_id"] else None,
        path=data["path"],
    )


def _server_prompt_from_json(data: dict | None) -> ServerPrompt | None:
    if data is None:
        return None
    return ServerPrompt(id=uuid.UUID(data["id"]), slug=data["slug"], role=data["role"], text=data["text"])
