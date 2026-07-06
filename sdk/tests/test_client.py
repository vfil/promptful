import httpx
import pytest

from promptful import Client, Prompt, PromptNotFoundError, PromptSummary


def _make_category(base_url: str, slug_segment: str = "sales") -> dict:
    response = httpx.post(f"{base_url}/categories", json={"slug_segment": slug_segment})
    assert response.status_code == 201, response.text
    return response.json()


def _create_prompt(
    base_url: str,
    category_id: str,
    leaf_slug: str = "first-lead",
    text: str = "Hi {{ name }}",
) -> dict:
    response = httpx.post(
        f"{base_url}/prompt/create",
        json={"leaf_slug": leaf_slug, "category_id": category_id, "text": text},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_get_prompt_returns_raw_text_by_slug(live_base_url: str) -> None:
    category = _make_category(live_base_url)
    _create_prompt(live_base_url, category["id"])

    with Client(base_url=live_base_url) as client:
        prompt = client.get_prompt("/sales/first-lead")

    assert isinstance(prompt, Prompt)
    assert prompt.slug == "/sales/first-lead"
    assert prompt.leaf_slug == "first-lead"
    assert prompt.version == 1
    assert prompt.text == "Hi {{ name }}"
    assert prompt.is_deleted is False


def test_get_prompt_unknown_slug_raises_not_found(live_base_url: str) -> None:
    with Client(base_url=live_base_url) as client:
        with pytest.raises(PromptNotFoundError) as exc_info:
            client.get_prompt("/sales/does-not-exist")

    assert exc_info.value.slug == "/sales/does-not-exist"


def test_get_prompt_deleted_prompt_raises_not_found(live_base_url: str) -> None:
    category = _make_category(live_base_url)
    created = _create_prompt(live_base_url, category["id"])
    delete_response = httpx.delete(f"{live_base_url}/prompt/{created['id']}")
    assert delete_response.status_code == 200, delete_response.text

    with Client(base_url=live_base_url) as client:
        with pytest.raises(PromptNotFoundError):
            client.get_prompt("/sales/first-lead")


def test_list_prompts_returns_live_versions_only(live_base_url: str) -> None:
    category = _make_category(live_base_url)
    _create_prompt(live_base_url, category["id"], leaf_slug="first-lead")
    deleted = _create_prompt(live_base_url, category["id"], leaf_slug="gone")
    httpx.delete(f"{live_base_url}/prompt/{deleted['id']}")

    with Client(base_url=live_base_url) as client:
        summaries = client.list_prompts()

    assert [s.slug for s in summaries] == ["/sales/first-lead"]
    assert isinstance(summaries[0], PromptSummary)


def test_client_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROMPTFUL_BASE_URL", raising=False)
    with pytest.raises(ValueError):
        Client()


def test_client_falls_back_to_env_var(live_base_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMPTFUL_BASE_URL", live_base_url)
    category = _make_category(live_base_url)
    _create_prompt(live_base_url, category["id"])

    with Client() as client:
        prompt = client.get_prompt("/sales/first-lead")

    assert prompt.text == "Hi {{ name }}"


def test_get_prompts_returns_results_aligned_to_input_order(live_base_url: str) -> None:
    category = _make_category(live_base_url)
    _create_prompt(live_base_url, category["id"], leaf_slug="alpha", text="A")
    _create_prompt(live_base_url, category["id"], leaf_slug="zeta", text="Z")

    with Client(base_url=live_base_url) as client:
        results = client.get_prompts(["/sales/zeta", "/sales/does-not-exist", "/sales/alpha"])

    assert len(results) == 3
    assert isinstance(results[0], Prompt) and results[0].text == "Z"
    assert results[1] is None
    assert isinstance(results[2], Prompt) and results[2].text == "A"


def test_get_prompts_repeats_duplicate_slugs_as_separate_entries(live_base_url: str) -> None:
    category = _make_category(live_base_url)
    _create_prompt(live_base_url, category["id"], leaf_slug="alpha")

    with Client(base_url=live_base_url) as client:
        results = client.get_prompts(["/sales/alpha", "/sales/alpha"])

    assert len(results) == 2
    assert results[0] is not None and results[1] is not None
    assert results[0].slug == results[1].slug == "/sales/alpha"
