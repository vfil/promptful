"""add categories and migrate prompts to leaf_slug + category_id

Revision ID: b3f9c2d1e8a4
Revises: ea5751e59bee
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3f9c2d1e8a4"
down_revision: Union[str, Sequence[str], None] = "ea5751e59bee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Slug-segment regex: lowercase alphanumeric + hyphens, no slashes.
SLUG_SEGMENT_REGEX = r"^[a-z0-9]+(-[a-z0-9]+)*$"


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug_segment", sa.String(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"slug_segment ~ '{SLUG_SEGMENT_REGEX}'",
            name="ck_categories_slug_segment_format",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name="fk_categories_parent_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # NULLS NOT DISTINCT: two root categories (parent_id IS NULL) with the
    # same slug_segment are blocked — standard UNIQUE treats NULLs as distinct.
    op.create_index(
        "uq_categories_slug_segment_parent_id",
        "categories",
        ["slug_segment", "parent_id"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )

    # Prompts: no production data exists; clear any dev/test rows before changing schema.
    op.execute("TRUNCATE TABLE prompts")
    op.drop_constraint("uq_prompts_slug_version", "prompts", type_="unique")
    op.drop_constraint("ck_prompts_slug_format", "prompts", type_="check")
    op.drop_column("prompts", "slug")

    op.add_column(
        "prompts",
        sa.Column("leaf_slug", sa.String(), nullable=False),
    )
    op.add_column(
        "prompts",
        sa.Column("category_id", sa.UUID(), nullable=False),
    )
    op.create_check_constraint(
        "ck_prompts_leaf_slug_format",
        "prompts",
        f"leaf_slug ~ '{SLUG_SEGMENT_REGEX}'",
    )
    op.create_foreign_key(
        "fk_prompts_category_id",
        "prompts",
        "categories",
        ["category_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_prompts_leaf_slug_category_version",
        "prompts",
        ["leaf_slug", "category_id", "version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_prompts_leaf_slug_category_version", "prompts", type_="unique")
    op.drop_constraint("fk_prompts_category_id", "prompts", type_="foreignkey")
    op.drop_constraint("ck_prompts_leaf_slug_format", "prompts", type_="check")
    op.drop_column("prompts", "category_id")
    op.drop_column("prompts", "leaf_slug")

    op.add_column("prompts", sa.Column("slug", sa.String(), nullable=False))
    op.create_check_constraint(
        "ck_prompts_slug_format",
        "prompts",
        r"slug ~ '^(/[a-z0-9]+(-[a-z0-9]+)*)+$'",
    )
    op.create_unique_constraint(
        "uq_prompts_slug_version", "prompts", ["slug", "version"]
    )

    op.drop_index("uq_categories_slug_segment_parent_id", table_name="categories")
    op.drop_table("categories")
