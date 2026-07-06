import re
import uuid
from datetime import datetime

import jinja2
from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.category import SLUG_SEGMENT_PATTERN, SLUG_SEGMENT_FORMAT_ERROR

# Leaf slug follows the same format as a Category Slug Segment.
LEAF_SLUG_PATTERN = SLUG_SEGMENT_PATTERN

LEAF_SLUG_FORMAT_ERROR = (
    "leaf_slug must be lowercase letters, digits and hyphens only, "
    "no slashes (e.g. 'first-lead')"
)


def validate_leaf_slug(value: str) -> str:
    if not LEAF_SLUG_PATTERN.match(value):
        raise ValueError(LEAF_SLUG_FORMAT_ERROR)
    return value


def validate_jinja2_text(value: str) -> str:
    try:
        jinja2.Environment().parse(value)
    except jinja2.TemplateSyntaxError as exc:
        raise ValueError(f"text is not a valid Jinja2 template: {exc}") from exc
    return value


class PromptCreate(BaseModel):
    leaf_slug: str
    category_id: uuid.UUID
    text: str

    @field_validator("leaf_slug")
    @classmethod
    def _validate_leaf_slug(cls, value: str) -> str:
        return validate_leaf_slug(value)

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        return validate_jinja2_text(value)


class PromptUpdate(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        return validate_jinja2_text(value)


class PromptVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str          # computed property on PromptVersion: category.path + "/" + leaf_slug
    leaf_slug: str
    category_id: uuid.UUID
    version: int
    text: str
    is_deleted: bool
    created_at: datetime


class PromptSummary(BaseModel):
    """One row per distinct Prompt (its Live Version), for list views. No `text`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    leaf_slug: str
    category_id: uuid.UUID
    version: int
    created_at: datetime
