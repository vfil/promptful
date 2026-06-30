"""Unit tests: Pydantic-layer validation only, no database involved."""

import pytest
from pydantic import ValidationError

from app.schemas.prompt import PromptCreate, PromptUpdate

VALID_SLUGS = [
    "/sales",
    "/sales/screening/first-lead",
    "/a/b-c/d-e-f",
]

INVALID_SLUGS = [
    "sales",  # missing leading slash
    "/Sales",  # uppercase
    "/sales/",  # trailing slash
    "/sales//screening",  # double slash
    "/sales_screening",  # underscore not allowed
    "/sales/-screening",  # segment can't start with hyphen
    "",
]


@pytest.mark.parametrize("slug", VALID_SLUGS)
def test_prompt_create_accepts_valid_slug(slug: str) -> None:
    prompt = PromptCreate(slug=slug, text="hello {{ name }}")
    assert prompt.slug == slug


@pytest.mark.parametrize("slug", INVALID_SLUGS)
def test_prompt_create_rejects_invalid_slug(slug: str) -> None:
    with pytest.raises(ValidationError):
        PromptCreate(slug=slug, text="hello {{ name }}")


def test_prompt_create_accepts_jinja2_syntax() -> None:
    prompt = PromptCreate(slug="/sales/first-lead", text="Hi {{ name }}, {% if vip %}VIP{% endif %}")
    assert "{{ name }}" in prompt.text


def test_prompt_create_rejects_malformed_jinja2() -> None:
    with pytest.raises(ValidationError):
        PromptCreate(slug="/sales/first-lead", text="Hi {{ name")


def test_prompt_update_accepts_jinja2_syntax() -> None:
    update = PromptUpdate(text="Hi {{ name }}")
    assert update.text == "Hi {{ name }}"


def test_prompt_update_rejects_malformed_jinja2() -> None:
    with pytest.raises(ValidationError):
        PromptUpdate(text="{% for x in items %}")
