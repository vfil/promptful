import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

SLUG_SEGMENT_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

SLUG_SEGMENT_FORMAT_ERROR = (
    "slug_segment must be lowercase letters, digits and hyphens only, "
    "no slashes, no leading/trailing hyphens (e.g. 'sales', 'first-lead')"
)


class CategoryCreate(BaseModel):
    slug_segment: str
    parent_id: uuid.UUID | None = None

    @field_validator("slug_segment")
    @classmethod
    def _validate_slug_segment(cls, value: str) -> str:
        if not SLUG_SEGMENT_PATTERN.match(value):
            raise ValueError(SLUG_SEGMENT_FORMAT_ERROR)
        return value


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug_segment: str
    parent_id: uuid.UUID | None
    path: str
    created_at: datetime
