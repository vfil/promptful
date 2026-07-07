"""add prompt role

Revision ID: 5a138e1ec91d
Revises: b3f9c2d1e8a4
Create Date: 2026-07-07 17:25:53.775650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a138e1ec91d'
down_revision: Union[str, Sequence[str], None] = 'b3f9c2d1e8a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADR-0007: no real data to preserve; clear any dev/test rows rather than
    # backfilling a default for a column that's semantically required going forward.
    op.execute("TRUNCATE TABLE prompts")
    op.add_column('prompts', sa.Column('role', sa.String(), nullable=False))
    op.create_check_constraint(
        "ck_prompts_role_values",
        "prompts",
        "role IN ('system', 'user', 'assistant')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_prompts_role_values", "prompts", type_="check")
    op.drop_column('prompts', 'role')
