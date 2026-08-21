"""add isolated AI chat history

Revision ID: p03_0003
Revises: p02_0002_bootstrap_keys
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p03_0003"
down_revision: str | None = "p02_0002_bootstrap_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "AIChatThread",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("userId", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "createdAt",
            postgresql.TIMESTAMP(precision=3, timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updatedAt",
            postgresql.TIMESTAMP(precision=3, timezone=False),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('normal', 'master', 'business', 'qilinge', 'xiaoman')",
            name="role_values",
        ),
        sa.ForeignKeyConstraint(
            ["userId"],
            ["User.id"],
            name="AIChatThread_userId_fkey",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="AIChatThread_pkey"),
    )
    op.create_index(
        "AIChatThread_userId_role_key",
        "AIChatThread",
        ["userId", "role"],
        unique=True,
    )
    op.create_table(
        "AIChatMessage",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("threadId", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column(
            "createdAt",
            postgresql.TIMESTAMP(precision=3, timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updatedAt",
            postgresql.TIMESTAMP(precision=3, timezone=False),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('human', 'ai')",
            name="role_values",
        ),
        sa.ForeignKeyConstraint(
            ["threadId"],
            ["AIChatThread.id"],
            name="AIChatMessage_threadId_fkey",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="AIChatMessage_pkey"),
    )
    op.create_index(
        "AIChatMessage_threadId_createdAt_idx",
        "AIChatMessage",
        ["threadId", "createdAt"],
        unique=False,
    )
    op.create_index(
        "AIChatMessage_threadId_position_key",
        "AIChatMessage",
        ["threadId", "position"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("AIChatMessage_threadId_position_key", table_name="AIChatMessage")
    op.drop_index("AIChatMessage_threadId_createdAt_idx", table_name="AIChatMessage")
    op.drop_table("AIChatMessage")
    op.drop_index("AIChatThread_userId_role_key", table_name="AIChatThread")
    op.drop_table("AIChatThread")
