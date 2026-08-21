"""Create the legacy-compatible application schema.

Revision ID: p01_0001_initial
Revises: None
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p01_0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

timestamp = postgresql.TIMESTAMP(precision=3, timezone=False)
money = sa.Numeric(65, 30)
trade_status = postgresql.ENUM(
    "NOT_PAY",
    "WAIT_BUYER_PAY",
    "TRADE_CLOSED",
    "TRADE_SUCCESS",
    "TRADE_FINISHED",
    name="TradeStatus",
    create_type=False,
)


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "createdAt",
            timestamp,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updatedAt", timestamp, nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "NOT_PAY",
        "WAIT_BUYER_PAY",
        "TRADE_CLOSED",
        "TRADE_SUCCESS",
        "TRADE_FINISHED",
        name="TradeStatus",
    ).create(bind, checkfirst=True)

    op.create_table(
        "User",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("password", sa.Text(), nullable=False),
        sa.Column("avatar", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("isTimingTask", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "timingTaskTime",
            sa.Text(),
            server_default=sa.text("'00:00:00'"),
            nullable=False,
        ),
        sa.Column("wordNumber", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("dayNumber", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lastLoginAt", timestamp, nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="User_pkey"),
    )
    op.create_index("User_email_key", "User", ["email"], unique=True)
    op.create_index("User_phone_key", "User", ["phone"], unique=True)

    op.create_table(
        "WordBook",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("word", sa.Text(), nullable=False),
        sa.Column("phonetic", sa.Text(), nullable=True),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("translation", sa.Text(), nullable=True),
        sa.Column("pos", sa.Text(), nullable=True),
        sa.Column("collins", sa.Text(), nullable=True),
        sa.Column("oxford", sa.Text(), nullable=True),
        sa.Column("tag", sa.Text(), nullable=True),
        sa.Column("bnc", sa.Text(), nullable=True),
        sa.Column("frq", sa.Text(), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("gk", sa.Boolean(), nullable=True),
        sa.Column("zk", sa.Boolean(), nullable=True),
        sa.Column("gre", sa.Boolean(), nullable=True),
        sa.Column("toefl", sa.Boolean(), nullable=True),
        sa.Column("ielts", sa.Boolean(), nullable=True),
        sa.Column("cet6", sa.Boolean(), nullable=True),
        sa.Column("cet4", sa.Boolean(), nullable=True),
        sa.Column("ky", sa.Boolean(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="WordBook_pkey"),
    )
    op.create_index("WordBook_word_idx", "WordBook", ["word"], unique=False)
    op.create_index("WordBook_tag_idx", "WordBook", ["tag"], unique=False)
    op.create_index("WordBook_word_tag_idx", "WordBook", ["word", "tag"], unique=False)

    op.create_table(
        "Course",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("teacher", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("price", money, nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="Course_pkey"),
    )

    op.create_table(
        "PaymentRecord",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("userId", sa.Text(), nullable=False),
        sa.Column("tradeNo", sa.Text(), nullable=True),
        sa.Column("outTradeNo", sa.Text(), nullable=False),
        sa.Column("amount", money, nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "tradeStatus",
            trade_status,
            server_default=sa.text("'NOT_PAY'"),
            nullable=False,
        ),
        sa.Column("sendPayTime", timestamp, nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["userId"],
            ["User.id"],
            name="PaymentRecord_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="PaymentRecord_pkey"),
    )
    op.create_index(
        "PaymentRecord_outTradeNo_key",
        "PaymentRecord",
        ["outTradeNo"],
        unique=True,
    )
    op.create_index("PaymentRecord_tradeNo_idx", "PaymentRecord", ["tradeNo"], unique=False)

    op.create_table(
        "Visitor",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("anonymousId", sa.Text(), nullable=False),
        sa.Column("userId", sa.Text(), nullable=True),
        sa.Column("browser", sa.Text(), nullable=True),
        sa.Column("os", sa.Text(), nullable=True),
        sa.Column("device", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["userId"],
            ["User.id"],
            name="Visitor_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="Visitor_pkey"),
    )
    op.create_index("Visitor_anonymousId_key", "Visitor", ["anonymousId"], unique=True)
    op.create_index("Visitor_userId_idx", "Visitor", ["userId"], unique=False)
    op.create_index("Visitor_anonymousId_idx", "Visitor", ["anonymousId"], unique=False)

    op.create_table(
        "WordBookRecord",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("wordId", sa.Text(), nullable=False),
        sa.Column("isMaster", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("userId", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["userId"],
            ["User.id"],
            name="WordBookRecord_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["wordId"],
            ["WordBook.id"],
            name="WordBookRecord_wordId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="WordBookRecord_pkey"),
    )
    op.create_index(
        "WordBookRecord_userId_wordId_key",
        "WordBookRecord",
        ["userId", "wordId"],
        unique=True,
    )

    op.create_table(
        "CourseRecord",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("userId", sa.Text(), nullable=False),
        sa.Column("courseId", sa.Text(), nullable=False),
        sa.Column("isPurchased", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("paymentRecordId", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["paymentRecordId"],
            ["PaymentRecord.id"],
            name="CourseRecord_paymentRecordId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["userId"],
            ["User.id"],
            name="CourseRecord_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["courseId"],
            ["Course.id"],
            name="CourseRecord_courseId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="CourseRecord_pkey"),
    )
    op.create_index(
        "CourseRecord_userId_courseId_key",
        "CourseRecord",
        ["userId", "courseId"],
        unique=True,
    )

    op.create_table(
        "PageView",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("visitorId", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("path", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["visitorId"],
            ["Visitor.id"],
            name="PageView_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="PageView_pkey"),
    )
    op.create_index(
        "PageView_visitorId_createdAt_idx",
        "PageView",
        ["visitorId", "createdAt"],
        unique=False,
    )
    op.create_index(
        "PageView_path_createdAt_idx",
        "PageView",
        ["path", "createdAt"],
        unique=False,
    )

    op.create_table(
        "TrackEvent",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("visitorId", sa.Text(), nullable=False),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["visitorId"],
            ["Visitor.id"],
            name="TrackEvent_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="TrackEvent_pkey"),
    )
    op.create_index(
        "TrackEvent_visitorId_createdAt_idx",
        "TrackEvent",
        ["visitorId", "createdAt"],
        unique=False,
    )
    op.create_index(
        "TrackEvent_event_createdAt_idx",
        "TrackEvent",
        ["event", "createdAt"],
        unique=False,
    )

    op.create_table(
        "PerformanceEntry",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("visitorId", sa.Text(), nullable=False),
        sa.Column("fp", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("fcp", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("lcp", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("inp", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("cls", postgresql.DOUBLE_PRECISION(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["visitorId"],
            ["Visitor.id"],
            name="PerformanceEntry_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="PerformanceEntry_pkey"),
    )
    for metric in ("fp", "fcp", "lcp", "inp", "cls"):
        op.create_index(
            f"PerformanceEntry_{metric}_createdAt_idx",
            "PerformanceEntry",
            [metric, "createdAt"],
            unique=False,
        )
    op.create_index(
        "PerformanceEntry_fp_fcp_lcp_inp_cls_createdAt_idx",
        "PerformanceEntry",
        ["fp", "fcp", "lcp", "inp", "cls", "createdAt"],
        unique=False,
    )

    op.create_table(
        "ErrorEntry",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("visitorId", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("stack", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["visitorId"],
            ["Visitor.id"],
            name="ErrorEntry_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="ErrorEntry_pkey"),
    )
    op.create_index(
        "ErrorEntry_visitorId_createdAt_idx",
        "ErrorEntry",
        ["visitorId", "createdAt"],
        unique=False,
    )
    op.create_index(
        "ErrorEntry_error_createdAt_idx",
        "ErrorEntry",
        ["error", "createdAt"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("ErrorEntry")
    op.drop_table("PerformanceEntry")
    op.drop_table("TrackEvent")
    op.drop_table("PageView")
    op.drop_table("CourseRecord")
    op.drop_table("WordBookRecord")
    op.drop_table("Visitor")
    op.drop_table("PaymentRecord")
    op.drop_table("Course")
    op.drop_table("WordBook")
    op.drop_table("User")
    trade_status.drop(op.get_bind(), checkfirst=True)
