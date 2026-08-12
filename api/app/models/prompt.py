import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.category import Category

# Leaf slug: a single slug-safe segment, no slashes.
# Keep in sync with app.schemas.prompt.LEAF_SLUG_PATTERN and the migration CHECK.
LEAF_SLUG_REGEX = r"^[a-z0-9]+(-[a-z0-9]+)*$"

# Which LLM message position `text` fills. Fixed at creation, like leaf_slug/category_id
# (ADR-0007). Keep in sync with app.schemas.prompt.PROMPT_ROLES and the migration CHECK.
PROMPT_ROLES = ("system", "user", "assistant")


class PromptVersion(Base):
    """One immutable Version row for a Prompt. See /CONTEXT.md."""

    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint(
            "leaf_slug", "category_id", "version",
            name="uq_prompts_leaf_slug_category_version",
        ),
        CheckConstraint(
            f"leaf_slug ~ '{LEAF_SLUG_REGEX}'", name="ck_prompts_leaf_slug_format"
        ),
        CheckConstraint("version >= 1", name="ck_prompts_version_positive"),
        CheckConstraint(
            "role IN ('system', 'user', 'assistant')", name="ck_prompts_role_values"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sql_text("gen_random_uuid()"),
    )
    leaf_slug: Mapped[str] = mapped_column(nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", name="fk_prompts_category_id"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(nullable=False)
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

    category: Mapped[Category] = relationship("Category", lazy="raise")

    @property
    def slug(self) -> str:
        """Full address: Category Path + '/' + Leaf Slug. Requires category loaded."""
        return f"{self.category.path}/{self.leaf_slug}"
