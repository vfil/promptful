"""Unit tests: Pydantic-layer validation only, no database involved."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.category import CategoryCreate
from app.schemas.prompt import PromptCreate, PromptUpdate

CATEGORY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

VALID_LEAF_SLUGS = [
    "sales",
    "first-lead",
    "a-b-c",
    "abc123",
]

INVALID_LEAF_SLUGS = [
    "Sales",           # uppercase
    "sales/screening", # slashes not allowed in leaf slug
    "-sales",          # leading hyphen
    "sales-",          # trailing hyphen
    "",
    "/sales",          # leading slash not allowed
]


@pytest.mark.parametrize("leaf_slug", VALID_LEAF_SLUGS)
def test_prompt_create_accepts_valid_leaf_slug(leaf_slug: str) -> None:
    prompt = PromptCreate(
        leaf_slug=leaf_slug, category_id=CATEGORY_ID, role="user", text="hello {{ name }}"
    )
    assert prompt.leaf_slug == leaf_slug


@pytest.mark.parametrize("leaf_slug", INVALID_LEAF_SLUGS)
def test_prompt_create_rejects_invalid_leaf_slug(leaf_slug: str) -> None:
    with pytest.raises(ValidationError):
        PromptCreate(
            leaf_slug=leaf_slug, category_id=CATEGORY_ID, role="user", text="hello {{ name }}"
        )


def test_prompt_create_accepts_jinja2_syntax() -> None:
    prompt = PromptCreate(
        leaf_slug="first-lead",
        category_id=CATEGORY_ID,
        role="user",
        text="Hi {{ name }}, {% if vip %}VIP{% endif %}",
    )
    assert "{{ name }}" in prompt.text


def test_prompt_create_rejects_malformed_jinja2() -> None:
    with pytest.raises(ValidationError):
        PromptCreate(
            leaf_slug="first-lead", category_id=CATEGORY_ID, role="user", text="Hi {{ name"
        )


# --- role -----------------------------------------------------------------


@pytest.mark.parametrize("role", ["system", "user", "assistant"])
def test_prompt_create_accepts_valid_role(role: str) -> None:
    prompt = PromptCreate(leaf_slug="first-lead", category_id=CATEGORY_ID, role=role, text="hi")
    assert prompt.role == role


def test_prompt_create_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        PromptCreate(
            leaf_slug="first-lead", category_id=CATEGORY_ID, role="narrator", text="hi"
        )


def test_prompt_update_accepts_jinja2_syntax() -> None:
    update = PromptUpdate(text="Hi {{ name }}")
    assert update.text == "Hi {{ name }}"


def test_prompt_update_rejects_malformed_jinja2() -> None:
    with pytest.raises(ValidationError):
        PromptUpdate(text="{% for x in items %}")


# --- Category schema unit tests -----------------------------------------------

VALID_SLUG_SEGMENTS = ["sales", "first-lead", "a-b-c", "abc123"]
INVALID_SLUG_SEGMENTS = ["Sales", "sales/sub", "-sales", "sales-", "", "/sales"]


@pytest.mark.parametrize("segment", VALID_SLUG_SEGMENTS)
def test_category_create_accepts_valid_slug_segment(segment: str) -> None:
    cat = CategoryCreate(slug_segment=segment)
    assert cat.slug_segment == segment


@pytest.mark.parametrize("segment", INVALID_SLUG_SEGMENTS)
def test_category_create_rejects_invalid_slug_segment(segment: str) -> None:
    with pytest.raises(ValidationError):
        CategoryCreate(slug_segment=segment)
