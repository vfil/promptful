import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

SLUG_SEGMENT_REGEX = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class Category(Base):
    """A named hierarchical grouping for Prompts. See /CONTEXT.md."""

    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            f"slug_segment ~ '{SLUG_SEGMENT_REGEX}'",
            name="ck_categories_slug_segment_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sql_text("gen_random_uuid()"),
    )
    slug_segment: Mapped[str] = mapped_column(nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", name="fk_categories_parent_id"),
        nullable=True,
    )
    path: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sql_text("now()"),
    )

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", lazy="raise"
    )
