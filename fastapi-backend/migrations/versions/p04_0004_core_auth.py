"""add refresh token rotation state

Revision ID: p04_0004
Revises: p03_0003
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p04_0004"
down_revision: str | None = "p03_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "User",
        sa.Column(
            "refreshTokenVersion",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("User", "refreshTokenVersion")
