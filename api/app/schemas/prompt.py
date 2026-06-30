import re
import uuid
from datetime import datetime

import jinja2
from pydantic import BaseModel, ConfigDict, field_validator

# Keep in sync with app.models.prompt.SLUG_REGEX (DB-level CHECK constraint).
SLUG_PATTERN = re.compile(r"^(/[a-z0-9]+(-[a-z0-9]+)*)+$")

SLUG_FORMAT_ERROR = (
    "slug must look like a URL path: lowercase letters, digits and hyphens per segment, "
    "segments separated by '/', leading '/' required, no trailing or double slashes "
    "(e.g. /sales/screening/first-lead)"
)


def validate_slug(value: str) -> str:
    if not SLUG_PATTERN.match(value):
        raise ValueError(SLUG_FORMAT_ERROR)
    return value


def validate_jinja2_text(value: str) -> str:
    try:
        jinja2.Environment().parse(value)
    except jinja2.TemplateSyntaxError as exc:
        raise ValueError(f"text is not a valid Jinja2 template: {exc}") from exc
    return value


class PromptCreate(BaseModel):
    slug: str
    text: str

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str) -> str:
        return validate_slug(value)

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
    slug: str
    version: int
    text: str
    is_deleted: bool
    created_at: datetime
