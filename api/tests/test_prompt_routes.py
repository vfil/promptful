"""Integration tests: drive the real FastAPI app + Postgres over HTTP.

DB isolation/setup: see tests/conftest.py (transaction-per-test against the
`app_test` database, per Q1 of the grilling session in
/product/ai-specs/add-prompt-endpoint.md).
"""

from httpx import AsyncClient


async def _create(client: AsyncClient, slug: str = "/sales/screening/first-lead", text: str = "Hi {{ name }}"):
    return await client.post("/prompt/create", json={"slug": slug, "text": text})


# --- Create -------------------------------------------------------------------


async def test_create_returns_201_with_version_1(client: AsyncClient) -> None:
    response = await _create(client)
    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == "/sales/screening/first-lead"
    assert body["version"] == 1
    assert body["is_deleted"] is False
    assert body["text"] == "Hi {{ name }}"


async def test_create_duplicate_slug_returns_409(client: AsyncClient) -> None:
    await _create(client)
    response = await _create(client)
    assert response.status_code == 409


async def test_create_invalid_slug_returns_422(client: AsyncClient) -> None:
    response = await _create(client, slug="no-leading-slash")
    assert response.status_code == 422


async def test_create_invalid_jinja2_returns_422(client: AsyncClient) -> None:
    response = await _create(client, text="Hi {{ name")
    assert response.status_code == 422


# --- Update ---------------------------------------------------------------------


async def test_update_increments_version_and_returns_200(client: AsyncClient) -> None:
    created = (await _create(client)).json()

    response = await client.post(f"/prompt/{created['id']}", json={"text": "Hi {{ name }}, v2"})

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["slug"] == created["slug"]
    assert body["text"] == "Hi {{ name }}, v2"
    assert body["id"] != created["id"]


async def test_update_unknown_id_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/prompt/00000000-0000-0000-0000-000000000000", json={"text": "hi"}
    )
    assert response.status_code == 404


async def test_update_with_stale_id_returns_409(client: AsyncClient) -> None:
    v1 = (await _create(client)).json()
    await client.post(f"/prompt/{v1['id']}", json={"text": "v2"})

    # v1's id is no longer the slug's Live Version (v2 is) — optimistic concurrency, ADR-0003.
    response = await client.post(f"/prompt/{v1['id']}", json={"text": "v3 attempted from stale v1"})

    assert response.status_code == 409


async def test_update_invalid_jinja2_returns_422(client: AsyncClient) -> None:
    v1 = (await _create(client)).json()
    response = await client.post(f"/prompt/{v1['id']}", json={"text": "{% for x in y %}"})
    assert response.status_code == 422


# --- Delete (tombstone) ----------------------------------------------------------


async def test_delete_returns_tombstone_with_200(client: AsyncClient) -> None:
    v1 = (await _create(client)).json()

    response = await client.delete(f"/prompt/{v1['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["is_deleted"] is True
    assert body["version"] == 2
    assert body["id"] != v1["id"]


async def test_delete_unknown_id_returns_404(client: AsyncClient) -> None:
    response = await client.delete("/prompt/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_delete_with_stale_id_returns_409(client: AsyncClient) -> None:
    v1 = (await _create(client)).json()
    await client.post(f"/prompt/{v1['id']}", json={"text": "v2"})

    response = await client.delete(f"/prompt/{v1['id']}")

    assert response.status_code == 409


async def test_get_by_slug_after_delete_returns_404(client: AsyncClient) -> None:
    v1 = (await _create(client, slug="/sales/temp")).json()
    await client.delete(f"/prompt/{v1['id']}")

    response = await client.get("/prompt", params={"slug": "/sales/temp"})

    assert response.status_code == 404


async def test_get_by_id_still_resolves_a_tombstone(client: AsyncClient) -> None:
    v1 = (await _create(client)).json()
    tombstone = (await client.delete(f"/prompt/{v1['id']}")).json()

    response = await client.get(f"/prompt/{tombstone['id']}")

    assert response.status_code == 200
    assert response.json()["is_deleted"] is True


async def test_recreate_after_delete_continues_version_counter(client: AsyncClient) -> None:
    v1 = (await _create(client, slug="/sales/temp")).json()
    await client.delete(f"/prompt/{v1['id']}")

    recreated = await _create(client, slug="/sales/temp", text="back again")

    assert recreated.status_code == 201
    body = recreated.json()
    assert body["version"] == 3  # v1=1, tombstone=2, recreate=3 — never resets to 1
    assert body["is_deleted"] is False


async def test_update_via_tombstones_own_id_resurrects_the_slug(client: AsyncClient) -> None:
    v1 = (await _create(client, slug="/sales/temp")).json()
    tombstone = (await client.delete(f"/prompt/{v1['id']}")).json()

    # The tombstone is currently the slug's Live-Version-candidate row, so updating
    # via its own id is a valid optimistic-concurrency target (ADR-0003) — this is
    # an alternate resurrection path alongside POST /prompt/create (ADR-0002).
    response = await client.post(f"/prompt/{tombstone['id']}", json={"text": "resurrected"})

    assert response.status_code == 200
    body = response.json()
    assert body["is_deleted"] is False
    assert body["version"] == 3


# --- Get by id --------------------------------------------------------------------


async def test_get_by_id_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/prompt/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# --- Get by slug --------------------------------------------------------------------


async def test_get_by_slug_returns_live_version(client: AsyncClient) -> None:
    created = (await _create(client)).json()

    response = await client.get("/prompt", params={"slug": created["slug"]})

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_by_slug_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/prompt", params={"slug": "/never/created"})
    assert response.status_code == 404


async def test_get_by_slug_with_version_pins_exact_version(client: AsyncClient) -> None:
    v1 = (await _create(client)).json()
    await client.post(f"/prompt/{v1['id']}", json={"text": "v2 text"})

    response = await client.get(
        "/prompt", params={"slug": v1["slug"], "version": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == v1["id"]
    assert body["version"] == 1


async def test_get_by_slug_with_unknown_version_returns_404(client: AsyncClient) -> None:
    await _create(client)
    response = await client.get(
        "/prompt", params={"slug": "/sales/screening/first-lead", "version": 99}
    )
    assert response.status_code == 404
