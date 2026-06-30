import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Text, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Keep in sync with app.schemas.prompt.SLUG_PATTERN (ADR-0001/0002 in /docs/adr,
# Q7/Q13 in /product/ai-specs/add-prompt-endpoint.md) — the API-layer regex is the
# friendly error message, this CHECK is the defense-in-depth safety net.
SLUG_REGEX = r"^(/[a-z0-9]+(-[a-z0-9]+)*)+$"


class PromptVersion(Base):
    """One immutable Version row for a Prompt slug. See /CONTEXT.md."""

    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_prompts_slug_version"),
        CheckConstraint(f"slug ~ '{SLUG_REGEX}'", name="ck_prompts_slug_format"),
        CheckConstraint("version >= 1", name="ck_prompts_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sql_text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=sql_text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sql_text("now()"),
    )
