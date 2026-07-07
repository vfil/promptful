"""Integration tests: drive the real FastAPI app + Postgres over HTTP.

DB isolation/setup: see tests/conftest.py.
"""

import pytest
from httpx import AsyncClient


async def _make_category(
    client: AsyncClient,
    slug_segment: str = "sales",
    parent_id: str | None = None,
) -> dict:
    payload: dict = {"slug_segment": slug_segment}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    resp = await client.post("/categories", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create(
    client: AsyncClient,
    category_id: str,
    leaf_slug: str = "first-lead",
    text: str = "Hi {{ name }}",
    role: str = "user",
) -> object:
    return await client.post(
        "/prompt/create",
        json={"leaf_slug": leaf_slug, "category_id": category_id, "role": role, "text": text},
    )


# --- Create -------------------------------------------------------------------


async def test_create_returns_201_with_version_1(client: AsyncClient) -> None:
    cat = await _make_category(client)
    response = await _create(client, cat["id"], role="system")
    assert response.status_code == 201
    body = response.json()
    assert body["leaf_slug"] == "first-lead"
    assert body["category_id"] == cat["id"]
    assert body["slug"] == "/sales/first-lead"
    assert body["version"] == 1
    assert body["role"] == "system"
    assert body["is_deleted"] is False
    assert body["text"] == "Hi {{ name }}"


async def test_create_missing_role_returns_422(client: AsyncClient) -> None:
    cat = await _make_category(client)
    response = await client.post(
        "/prompt/create",
        json={"leaf_slug": "first-lead", "category_id": cat["id"], "text": "Hi"},
    )
    assert response.status_code == 422


async def test_create_invalid_role_returns_422(client: AsyncClient) -> None:
    cat = await _make_category(client)
    response = await _create(client, cat["id"], role="narrator")
    assert response.status_code == 422


async def test_create_duplicate_prompt_returns_409(client: AsyncClient) -> None:
    cat = await _make_category(client)
    await _create(client, cat["id"])
    response = await _create(client, cat["id"])
    assert response.status_code == 409


async def test_create_unknown_category_returns_404(client: AsyncClient) -> None:
    response = await _create(client, "00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_create_invalid_leaf_slug_returns_422(client: AsyncClient) -> None:
    cat = await _make_category(client)
    response = await _create(client, cat["id"], leaf_slug="Has/Slashes")
    assert response.status_code == 422


async def test_create_invalid_jinja2_returns_422(client: AsyncClient) -> None:
    cat = await _make_category(client)
    response = await _create(client, cat["id"], text="Hi {{ name")
    assert response.status_code == 422


# --- Update -------------------------------------------------------------------


async def test_update_increments_version_and_returns_200(client: AsyncClient) -> None:
    cat = await _make_category(client)
    created = (await _create(client, cat["id"], role="assistant")).json()

    response = await client.post(f"/prompt/{created['id']}", json={"text": "Hi {{ name }}, v2"})

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["slug"] == created["slug"]
    assert body["text"] == "Hi {{ name }}, v2"
    assert body["id"] != created["id"]
    assert body["role"] == "assistant"


async def test_update_ignores_role_in_payload(client: AsyncClient) -> None:
    """role is immutable (ADR-0007) — PromptUpdate has no role field, so any role
    sent in the update payload is silently ignored rather than changing the Prompt."""
    cat = await _make_category(client)
    created = (await _create(client, cat["id"], role="system")).json()

    response = await client.post(
        f"/prompt/{created['id']}", json={"text": "v2", "role": "assistant"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "system"


async def test_update_unknown_id_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/prompt/00000000-0000-0000-0000-000000000000", json={"text": "hi"}
    )
    assert response.status_code == 404


async def test_update_with_stale_id_returns_409(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"])).json()
    await client.post(f"/prompt/{v1['id']}", json={"text": "v2"})

    response = await client.post(f"/prompt/{v1['id']}", json={"text": "v3 from stale v1"})

    assert response.status_code == 409


async def test_update_invalid_jinja2_returns_422(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"])).json()
    response = await client.post(f"/prompt/{v1['id']}", json={"text": "{% for x in y %}"})
    assert response.status_code == 422


# --- Delete (tombstone) -------------------------------------------------------


async def test_delete_returns_tombstone_with_200(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"], role="system")).json()

    response = await client.delete(f"/prompt/{v1['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["is_deleted"] is True
    assert body["version"] == 2
    assert body["id"] != v1["id"]
    assert body["role"] == "system"


async def test_delete_unknown_id_returns_404(client: AsyncClient) -> None:
    response = await client.delete("/prompt/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_delete_with_stale_id_returns_409(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"])).json()
    await client.post(f"/prompt/{v1['id']}", json={"text": "v2"})

    response = await client.delete(f"/prompt/{v1['id']}")

    assert response.status_code == 409


async def test_get_by_slug_after_delete_returns_404(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"], leaf_slug="temp")).json()
    await client.delete(f"/prompt/{v1['id']}")

    response = await client.get("/prompt", params={"slug": "/sales/temp"})

    assert response.status_code == 404


async def test_get_by_id_still_resolves_a_tombstone(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"])).json()
    tombstone = (await client.delete(f"/prompt/{v1['id']}")).json()

    response = await client.get(f"/prompt/{tombstone['id']}")

    assert response.status_code == 200
    assert response.json()["is_deleted"] is True


async def test_recreate_after_delete_continues_version_counter(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"], leaf_slug="temp")).json()
    await client.delete(f"/prompt/{v1['id']}")

    recreated = await _create(client, cat["id"], leaf_slug="temp", text="back again")

    assert recreated.status_code == 201
    body = recreated.json()
    assert body["version"] == 3
    assert body["is_deleted"] is False


async def test_update_via_tombstones_own_id_resurrects_the_prompt(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"], leaf_slug="temp")).json()
    tombstone = (await client.delete(f"/prompt/{v1['id']}")).json()

    response = await client.post(f"/prompt/{tombstone['id']}", json={"text": "resurrected"})

    assert response.status_code == 200
    body = response.json()
    assert body["is_deleted"] is False
    assert body["version"] == 3


# --- Get by id ----------------------------------------------------------------


async def test_get_by_id_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/prompt/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# --- Get by slug --------------------------------------------------------------


async def test_get_by_slug_returns_live_version(client: AsyncClient) -> None:
    cat = await _make_category(client)
    created = (await _create(client, cat["id"])).json()

    response = await client.get("/prompt", params={"slug": created["slug"]})

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_by_slug_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/prompt", params={"slug": "/never/created"})
    assert response.status_code == 404


async def test_get_by_slug_with_version_pins_exact_version(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"])).json()
    await client.post(f"/prompt/{v1['id']}", json={"text": "v2 text"})

    response = await client.get("/prompt", params={"slug": v1["slug"], "version": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == v1["id"]
    assert body["version"] == 1


async def test_get_by_slug_with_unknown_version_returns_404(client: AsyncClient) -> None:
    cat = await _make_category(client)
    await _create(client, cat["id"])
    response = await client.get(
        "/prompt", params={"slug": "/sales/first-lead", "version": 99}
    )
    assert response.status_code == 404


# --- Slug derivation from nested category -------------------------------------


async def test_slug_reflects_nested_category_path(client: AsyncClient) -> None:
    root = await _make_category(client, "sales")
    child = (
        await client.post(
            "/categories", json={"slug_segment": "screening", "parent_id": root["id"]}
        )
    ).json()

    created = (await _create(client, child["id"], leaf_slug="first-lead")).json()

    assert created["slug"] == "/sales/screening/first-lead"


# --- List -----------------------------------------------------------------


async def test_list_prompts_returns_empty_list_when_none_exist(client: AsyncClient) -> None:
    response = await client.get("/prompts")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_prompts_returns_one_row_per_prompt_sorted_alphabetically(
    client: AsyncClient,
) -> None:
    cat = await _make_category(client)
    await _create(client, cat["id"], leaf_slug="zeta")
    await _create(client, cat["id"], leaf_slug="alpha")

    response = await client.get("/prompts")

    assert response.status_code == 200
    body = response.json()
    assert [p["slug"] for p in body] == ["/sales/alpha", "/sales/zeta"]
    assert "text" not in body[0]
    assert "is_deleted" not in body[0]


async def test_list_prompts_excludes_tombstoned_prompts(client: AsyncClient) -> None:
    cat = await _make_category(client)
    live = (await _create(client, cat["id"], leaf_slug="alive")).json()
    deleted = (await _create(client, cat["id"], leaf_slug="dead")).json()
    await client.delete(f"/prompt/{deleted['id']}")

    response = await client.get("/prompts")

    slugs = [p["slug"] for p in response.json()]
    assert slugs == ["/sales/alive"]


async def test_list_prompts_returns_only_the_latest_version(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"], leaf_slug="first-lead")).json()
    v2 = (await client.post(f"/prompt/{v1['id']}", json={"text": "v2"})).json()

    response = await client.get("/prompts")

    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == v2["id"]
    assert body[0]["version"] == 2


async def test_list_prompts_orders_by_full_slug_not_category_path_then_leaf_slug(
    client: AsyncClient,
) -> None:
    """"/ab-cd/y" sorts before "/ab/x" as a string (hyphen < slash in ASCII),
    even though the tuple (path, leaf_slug) would order "/ab" before "/ab-cd"."""
    cat_ab = await _make_category(client, "ab")
    cat_ab_cd = await _make_category(client, "ab-cd")
    await _create(client, cat_ab["id"], leaf_slug="x")
    await _create(client, cat_ab_cd["id"], leaf_slug="y")

    response = await client.get("/prompts")

    assert [p["slug"] for p in response.json()] == ["/ab-cd/y", "/ab/x"]


# --- Batch ----------------------------------------------------------------


async def test_batch_returns_full_content_in_request_order(client: AsyncClient) -> None:
    cat = await _make_category(client)
    await _create(client, cat["id"], leaf_slug="alpha", text="A {{ x }}", role="system")
    await _create(client, cat["id"], leaf_slug="zeta", text="Z {{ y }}", role="user")

    response = await client.post(
        "/prompts/batch", json={"slugs": ["/sales/zeta", "/sales/alpha"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["slug"] for item in body] == ["/sales/zeta", "/sales/alpha"]
    assert body[0]["prompt"]["text"] == "Z {{ y }}"
    assert body[0]["prompt"]["role"] == "user"
    assert body[1]["prompt"]["text"] == "A {{ x }}"
    assert body[1]["prompt"]["role"] == "system"


async def test_batch_marks_missing_slugs_with_null_prompt(client: AsyncClient) -> None:
    cat = await _make_category(client)
    await _create(client, cat["id"], leaf_slug="alpha")

    response = await client.post(
        "/prompts/batch",
        json={"slugs": ["/sales/alpha", "/sales/does-not-exist", "malformed-no-category"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["prompt"] is not None
    assert body[1]["prompt"] is None
    assert body[2]["prompt"] is None
    assert [item["slug"] for item in body] == [
        "/sales/alpha",
        "/sales/does-not-exist",
        "malformed-no-category",
    ]


async def test_batch_excludes_tombstoned_prompts(client: AsyncClient) -> None:
    cat = await _make_category(client)
    created = await _create(client, cat["id"], leaf_slug="alpha")
    deleted = created.json()
    await client.delete(f"/prompt/{deleted['id']}")

    response = await client.post("/prompts/batch", json={"slugs": ["/sales/alpha"]})

    assert response.json()[0]["prompt"] is None


async def test_batch_returns_only_the_latest_version(client: AsyncClient) -> None:
    cat = await _make_category(client)
    v1 = (await _create(client, cat["id"], leaf_slug="alpha")).json()
    v2 = (await client.post(f"/prompt/{v1['id']}", json={"text": "v2"})).json()

    response = await client.post("/prompts/batch", json={"slugs": ["/sales/alpha"]})

    prompt = response.json()[0]["prompt"]
    assert prompt["id"] == v2["id"]
    assert prompt["version"] == 2


async def test_batch_repeats_duplicate_slugs_as_separate_entries(client: AsyncClient) -> None:
    cat = await _make_category(client)
    await _create(client, cat["id"], leaf_slug="alpha")

    response = await client.post(
        "/prompts/batch", json={"slugs": ["/sales/alpha", "/sales/alpha"]}
    )

    body = response.json()
    assert len(body) == 2
    assert body[0]["prompt"]["slug"] == body[1]["prompt"]["slug"] == "/sales/alpha"


async def test_batch_empty_slugs_returns_422(client: AsyncClient) -> None:
    response = await client.post("/prompts/batch", json={"slugs": []})
    assert response.status_code == 422


async def test_batch_over_max_slugs_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/prompts/batch", json={"slugs": [f"/sales/p{i}" for i in range(501)]}
    )
    assert response.status_code == 422
