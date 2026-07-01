"""Integration tests for /categories endpoints."""

from httpx import AsyncClient


# --- Create -------------------------------------------------------------------


async def test_create_root_category_returns_201_with_correct_path(client: AsyncClient) -> None:
    response = await client.post("/categories", json={"slug_segment": "sales"})
    assert response.status_code == 201
    body = response.json()
    assert body["slug_segment"] == "sales"
    assert body["parent_id"] is None
    assert body["path"] == "/sales"


async def test_create_child_category_inherits_parent_path(client: AsyncClient) -> None:
    root = (await client.post("/categories", json={"slug_segment": "sales"})).json()

    response = await client.post(
        "/categories",
        json={"slug_segment": "screening", "parent_id": root["id"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["path"] == "/sales/screening"
    assert body["parent_id"] == root["id"]


async def test_create_deeply_nested_category(client: AsyncClient) -> None:
    root = (await client.post("/categories", json={"slug_segment": "sales"})).json()
    mid = (
        await client.post(
            "/categories", json={"slug_segment": "screening", "parent_id": root["id"]}
        )
    ).json()

    response = await client.post(
        "/categories",
        json={"slug_segment": "phase-one", "parent_id": mid["id"]},
    )
    assert response.status_code == 201
    assert response.json()["path"] == "/sales/screening/phase-one"


async def test_create_duplicate_sibling_returns_409(client: AsyncClient) -> None:
    await client.post("/categories", json={"slug_segment": "sales"})
    response = await client.post("/categories", json={"slug_segment": "sales"})
    assert response.status_code == 409


async def test_create_same_segment_under_different_parents_is_allowed(
    client: AsyncClient,
) -> None:
    root_a = (await client.post("/categories", json={"slug_segment": "a"})).json()
    root_b = (await client.post("/categories", json={"slug_segment": "b"})).json()

    resp_a = await client.post(
        "/categories", json={"slug_segment": "screening", "parent_id": root_a["id"]}
    )
    resp_b = await client.post(
        "/categories", json={"slug_segment": "screening", "parent_id": root_b["id"]}
    )

    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    assert resp_a.json()["path"] == "/a/screening"
    assert resp_b.json()["path"] == "/b/screening"


async def test_create_unknown_parent_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/categories",
        json={"slug_segment": "sales", "parent_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404


async def test_create_invalid_slug_segment_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/categories", json={"slug_segment": "Has Spaces"}
    )
    assert response.status_code == 422


async def test_create_slug_segment_with_slash_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/categories", json={"slug_segment": "sales/screening"}
    )
    assert response.status_code == 422


# --- List ---------------------------------------------------------------------


async def test_list_returns_empty_list_initially(client: AsyncClient) -> None:
    response = await client.get("/categories")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_returns_all_categories_flat(client: AsyncClient) -> None:
    root = (await client.post("/categories", json={"slug_segment": "sales"})).json()
    await client.post(
        "/categories", json={"slug_segment": "screening", "parent_id": root["id"]}
    )

    response = await client.get("/categories")

    assert response.status_code == 200
    paths = [c["path"] for c in response.json()]
    assert "/sales" in paths
    assert "/sales/screening" in paths


async def test_list_ordered_by_path(client: AsyncClient) -> None:
    root = (await client.post("/categories", json={"slug_segment": "b"})).json()
    await client.post(
        "/categories", json={"slug_segment": "child", "parent_id": root["id"]}
    )
    await client.post("/categories", json={"slug_segment": "a"})

    paths = [c["path"] for c in (await client.get("/categories")).json()]
    assert paths == sorted(paths)
