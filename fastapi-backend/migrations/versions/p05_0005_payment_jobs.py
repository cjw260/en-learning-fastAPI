"""add trusted payment metadata and durable background jobs

Revision ID: p05_0005
Revises: p04_0004
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p05_0005"
down_revision: str | None = "p04_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("PaymentRecord", sa.Column("courseId", sa.Text(), nullable=True))
    op.add_column(
        "PaymentRecord",
        sa.Column(
            "expiresAt",
            postgresql.TIMESTAMP(timezone=False, precision=3),
            nullable=True,
        ),
    )
    op.add_column("PaymentRecord", sa.Column("appId", sa.Text(), nullable=True))
    op.add_column("PaymentRecord", sa.Column("sellerId", sa.Text(), nullable=True))
    op.create_foreign_key(
        "PaymentRecord_courseId_fkey",
        "PaymentRecord",
        "Course",
        ["courseId"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.create_index(
        "PaymentRecord_userId_courseId_idx",
        "PaymentRecord",
        ["userId", "courseId"],
        unique=False,
    )

    op.create_table(
        "BackgroundJob",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("taskKey", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("userId", sa.Text(), nullable=False),
        sa.Column("paymentRecordId", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("maxAttempts", sa.Integer(), server_default=sa.text("4"), nullable=False),
        sa.Column(
            "scheduledFor",
            postgresql.TIMESTAMP(timezone=False, precision=3),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("lockedUntil", postgresql.TIMESTAMP(timezone=False, precision=3), nullable=True),
        sa.Column("completedAt", postgresql.TIMESTAMP(timezone=False, precision=3), nullable=True),
        sa.Column("lastErrorCode", sa.Text(), nullable=True),
        sa.Column(
            "createdAt",
            postgresql.TIMESTAMP(timezone=False, precision=3),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updatedAt", postgresql.TIMESTAMP(timezone=False, precision=3), nullable=False),
        sa.CheckConstraint(
            "kind IN ('PAYMENT_SUCCESS', 'EMAIL_DIGEST')", name="BackgroundJob_kind_values"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="BackgroundJob_status_values",
        ),
        sa.CheckConstraint('attempts >= 0 AND "maxAttempts" > 0', name="BackgroundJob_attempts"),
        sa.ForeignKeyConstraint(
            ["paymentRecordId"],
            ["PaymentRecord.id"],
            name="BackgroundJob_paymentRecordId_fkey",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["userId"],
            ["User.id"],
            name="BackgroundJob_userId_fkey",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="BackgroundJob_pkey"),
    )
    op.create_index("BackgroundJob_taskKey_key", "BackgroundJob", ["taskKey"], unique=True)
    op.create_index(
        "BackgroundJob_status_scheduledFor_idx",
        "BackgroundJob",
        ["status", "scheduledFor"],
        unique=False,
    )
    op.create_index("BackgroundJob_kind_idx", "BackgroundJob", ["kind"], unique=False)


def downgrade() -> None:
    op.drop_table("BackgroundJob")
    op.drop_index("PaymentRecord_userId_courseId_idx", table_name="PaymentRecord")
    op.drop_constraint("PaymentRecord_courseId_fkey", "PaymentRecord", type_="foreignkey")
    op.drop_column("PaymentRecord", "sellerId")
    op.drop_column("PaymentRecord", "appId")
    op.drop_column("PaymentRecord", "expiresAt")
    op.drop_column("PaymentRecord", "courseId")
