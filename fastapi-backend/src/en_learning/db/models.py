from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from en_learning.db.base import Base


def utc_now_naive() -> datetime:
    """Return naive UTC to preserve the legacy Prisma TIMESTAMP(3) contract."""

    return datetime.now(UTC).replace(tzinfo=None)


timestamp_type = TIMESTAMP(timezone=False, precision=3)
money_type = Numeric(65, 30)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        timestamp_type,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        timestamp_type,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )


class TradeStatus(StrEnum):
    NOT_PAY = "NOT_PAY"
    WAIT_BUYER_PAY = "WAIT_BUYER_PAY"
    TRADE_CLOSED = "TRADE_CLOSED"
    TRADE_SUCCESS = "TRADE_SUCCESS"
    TRADE_FINISHED = "TRADE_FINISHED"


trade_status_type = Enum(TradeStatus, name="TradeStatus", native_enum=True)


class User(TimestampMixin, Base):
    __tablename__ = "User"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="User_pkey"),
        Index("User_email_key", "email", unique=True),
        Index("User_phone_key", "phone", unique=True),
    )

    id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    password: Mapped[str] = mapped_column(Text)
    avatar: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    is_timing_task: Mapped[bool] = mapped_column(
        "isTimingTask",
        Boolean,
        default=False,
        server_default=text("false"),
    )
    timing_task_time: Mapped[str] = mapped_column(
        "timingTaskTime",
        Text,
        default="00:00:00",
        server_default=text("'00:00:00'"),
    )
    word_number: Mapped[int] = mapped_column(
        "wordNumber",
        Integer,
        default=0,
        server_default=text("0"),
    )
    day_number: Mapped[int] = mapped_column(
        "dayNumber",
        Integer,
        default=0,
        server_default=text("0"),
    )
    last_login_at: Mapped[datetime | None] = mapped_column("lastLoginAt", timestamp_type)
    refresh_token_version: Mapped[int] = mapped_column(
        "refreshTokenVersion",
        Integer,
        default=0,
        server_default=text("0"),
    )

    word_book_records: Mapped[list[WordBookRecord]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    payment_records: Mapped[list[PaymentRecord]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    course_records: Mapped[list[CourseRecord]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    visitors: Mapped[list[Visitor]] = relationship(
        back_populates="user",
        cascade="all",
        passive_deletes=True,
    )
    ai_chat_threads: Mapped[list[AIChatThread]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AIChatThread(TimestampMixin, Base):
    __tablename__ = "AIChatThread"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="AIChatThread_pkey"),
        Index("AIChatThread_userId_role_key", "userId", "role", unique=True),
        CheckConstraint(
            "role IN ('normal', 'master', 'business', 'qilinge', 'xiaoman')",
            name="role_values",
        ),
    )

    id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(
        "userId",
        Text,
        ForeignKey(
            "User.id",
            name="AIChatThread_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    role: Mapped[str] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="ai_chat_threads")
    messages: Mapped[list[AIChatMessage]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AIChatMessage.position",
    )


class AIChatMessage(TimestampMixin, Base):
    __tablename__ = "AIChatMessage"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="AIChatMessage_pkey"),
        Index("AIChatMessage_threadId_position_key", "threadId", "position", unique=True),
        Index("AIChatMessage_threadId_createdAt_idx", "threadId", "createdAt"),
        CheckConstraint("role IN ('human', 'ai')", name="role_values"),
    )

    id: Mapped[str] = mapped_column(Text)
    thread_id: Mapped[str] = mapped_column(
        "threadId",
        Text,
        ForeignKey(
            "AIChatThread.id",
            name="AIChatMessage_threadId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text)

    thread: Mapped[AIChatThread] = relationship(back_populates="messages")


class WordBookRecord(TimestampMixin, Base):
    __tablename__ = "WordBookRecord"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="WordBookRecord_pkey"),
        Index("WordBookRecord_userId_wordId_key", "userId", "wordId", unique=True),
    )

    id: Mapped[str] = mapped_column(Text)
    word_id: Mapped[str] = mapped_column(
        "wordId",
        Text,
        ForeignKey(
            "WordBook.id",
            name="WordBookRecord_wordId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    is_master: Mapped[bool] = mapped_column(
        "isMaster",
        Boolean,
        default=False,
        server_default=text("false"),
    )
    user_id: Mapped[str] = mapped_column(
        "userId",
        Text,
        ForeignKey(
            "User.id",
            name="WordBookRecord_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )

    user: Mapped[User] = relationship(back_populates="word_book_records")
    word: Mapped[WordBook] = relationship(back_populates="word_book_records")


class WordBook(TimestampMixin, Base):
    __tablename__ = "WordBook"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="WordBook_pkey"),
        Index("WordBook_word_key", "word", unique=True),
        Index("WordBook_tag_idx", "tag"),
        Index("WordBook_word_tag_idx", "word", "tag"),
        Index("WordBook_frqRank_word_id_idx", "frqRank", "word", "id"),
    )

    id: Mapped[str] = mapped_column(Text)
    word: Mapped[str] = mapped_column(Text)
    phonetic: Mapped[str | None] = mapped_column(Text)
    definition: Mapped[str | None] = mapped_column(Text)
    translation: Mapped[str | None] = mapped_column(Text)
    pos: Mapped[str | None] = mapped_column(Text)
    collins: Mapped[str | None] = mapped_column(Text)
    oxford: Mapped[str | None] = mapped_column(Text)
    tag: Mapped[str | None] = mapped_column(Text)
    bnc: Mapped[str | None] = mapped_column(Text)
    frq: Mapped[str | None] = mapped_column(Text)
    frq_rank: Mapped[int | None] = mapped_column("frqRank", Integer)
    exchange: Mapped[str | None] = mapped_column(Text)
    gk: Mapped[bool | None] = mapped_column(Boolean)
    zk: Mapped[bool | None] = mapped_column(Boolean)
    gre: Mapped[bool | None] = mapped_column(Boolean)
    toefl: Mapped[bool | None] = mapped_column(Boolean)
    ielts: Mapped[bool | None] = mapped_column(Boolean)
    cet6: Mapped[bool | None] = mapped_column(Boolean)
    cet4: Mapped[bool | None] = mapped_column(Boolean)
    ky: Mapped[bool | None] = mapped_column(Boolean)

    word_book_records: Mapped[list[WordBookRecord]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PaymentRecord(TimestampMixin, Base):
    __tablename__ = "PaymentRecord"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="PaymentRecord_pkey"),
        Index("PaymentRecord_outTradeNo_key", "outTradeNo", unique=True),
        Index("PaymentRecord_tradeNo_idx", "tradeNo"),
    )

    id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(
        "userId",
        Text,
        ForeignKey(
            "User.id",
            name="PaymentRecord_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    trade_no: Mapped[str | None] = mapped_column("tradeNo", Text)
    out_trade_no: Mapped[str] = mapped_column("outTradeNo", Text)
    amount: Mapped[Decimal] = mapped_column(money_type)
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    trade_status: Mapped[TradeStatus] = mapped_column(
        "tradeStatus",
        trade_status_type,
        default=TradeStatus.NOT_PAY,
        server_default=text("'NOT_PAY'"),
    )
    send_pay_time: Mapped[datetime | None] = mapped_column("sendPayTime", timestamp_type)

    user: Mapped[User] = relationship(back_populates="payment_records")
    course_records: Mapped[list[CourseRecord]] = relationship(
        back_populates="payment_record",
        cascade="all",
        passive_deletes=True,
    )


class CourseRecord(TimestampMixin, Base):
    __tablename__ = "CourseRecord"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="CourseRecord_pkey"),
        Index("CourseRecord_userId_courseId_key", "userId", "courseId", unique=True),
    )

    id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(
        "userId",
        Text,
        ForeignKey(
            "User.id",
            name="CourseRecord_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    course_id: Mapped[str] = mapped_column(
        "courseId",
        Text,
        ForeignKey(
            "Course.id",
            name="CourseRecord_courseId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    is_purchased: Mapped[bool] = mapped_column(
        "isPurchased",
        Boolean,
        default=False,
        server_default=text("false"),
    )
    payment_record_id: Mapped[str | None] = mapped_column(
        "paymentRecordId",
        Text,
        ForeignKey(
            "PaymentRecord.id",
            name="CourseRecord_paymentRecordId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )

    payment_record: Mapped[PaymentRecord | None] = relationship(back_populates="course_records")
    user: Mapped[User] = relationship(back_populates="course_records")
    course: Mapped[Course] = relationship(back_populates="course_records")


class Course(TimestampMixin, Base):
    __tablename__ = "Course"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="Course_pkey"),
        Index("Course_value_key", "value", unique=True),
    )

    id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    teacher: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(money_type)

    course_records: Mapped[list[CourseRecord]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Visitor(TimestampMixin, Base):
    __tablename__ = "Visitor"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="Visitor_pkey"),
        Index("Visitor_anonymousId_key", "anonymousId", unique=True),
        Index("Visitor_userId_idx", "userId"),
        Index("Visitor_anonymousId_idx", "anonymousId"),
    )

    id: Mapped[str] = mapped_column(Text)
    anonymous_id: Mapped[str] = mapped_column("anonymousId", Text)
    user_id: Mapped[str | None] = mapped_column(
        "userId",
        Text,
        ForeignKey(
            "User.id",
            name="Visitor_userId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    browser: Mapped[str | None] = mapped_column(Text)
    os: Mapped[str | None] = mapped_column(Text)
    device: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User | None] = relationship(back_populates="visitors")
    page_views: Mapped[list[PageView]] = relationship(
        back_populates="visitor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    track_events: Mapped[list[TrackEvent]] = relationship(
        back_populates="visitor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    performance_entries: Mapped[list[PerformanceEntry]] = relationship(
        back_populates="visitor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    error_entries: Mapped[list[ErrorEntry]] = relationship(
        back_populates="visitor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PageView(TimestampMixin, Base):
    __tablename__ = "PageView"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="PageView_pkey"),
        Index("PageView_visitorId_createdAt_idx", "visitorId", "createdAt"),
        Index("PageView_path_createdAt_idx", "path", "createdAt"),
    )

    id: Mapped[str] = mapped_column(Text)
    visitor_id: Mapped[str] = mapped_column(
        "visitorId",
        Text,
        ForeignKey(
            "Visitor.id",
            name="PageView_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    url: Mapped[str] = mapped_column(Text)
    referrer: Mapped[str | None] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)

    visitor: Mapped[Visitor] = relationship(back_populates="page_views")


class TrackEvent(TimestampMixin, Base):
    __tablename__ = "TrackEvent"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="TrackEvent_pkey"),
        Index("TrackEvent_visitorId_createdAt_idx", "visitorId", "createdAt"),
        Index("TrackEvent_event_createdAt_idx", "event", "createdAt"),
    )

    id: Mapped[str] = mapped_column(Text)
    visitor_id: Mapped[str] = mapped_column(
        "visitorId",
        Text,
        ForeignKey(
            "Visitor.id",
            name="TrackEvent_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    event: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    url: Mapped[str | None] = mapped_column(Text)

    visitor: Mapped[Visitor] = relationship(back_populates="track_events")


class PerformanceEntry(TimestampMixin, Base):
    __tablename__ = "PerformanceEntry"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="PerformanceEntry_pkey"),
        Index("PerformanceEntry_fp_createdAt_idx", "fp", "createdAt"),
        Index("PerformanceEntry_fcp_createdAt_idx", "fcp", "createdAt"),
        Index("PerformanceEntry_lcp_createdAt_idx", "lcp", "createdAt"),
        Index("PerformanceEntry_inp_createdAt_idx", "inp", "createdAt"),
        Index("PerformanceEntry_cls_createdAt_idx", "cls", "createdAt"),
        Index(
            "PerformanceEntry_fp_fcp_lcp_inp_cls_createdAt_idx",
            "fp",
            "fcp",
            "lcp",
            "inp",
            "cls",
            "createdAt",
        ),
    )

    id: Mapped[str] = mapped_column(Text)
    visitor_id: Mapped[str] = mapped_column(
        "visitorId",
        Text,
        ForeignKey(
            "Visitor.id",
            name="PerformanceEntry_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    fp: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    fcp: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    lcp: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    inp: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    cls: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)

    visitor: Mapped[Visitor] = relationship(back_populates="performance_entries")


class ErrorEntry(TimestampMixin, Base):
    __tablename__ = "ErrorEntry"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="ErrorEntry_pkey"),
        Index("ErrorEntry_visitorId_createdAt_idx", "visitorId", "createdAt"),
        Index("ErrorEntry_error_createdAt_idx", "error", "createdAt"),
    )

    id: Mapped[str] = mapped_column(Text)
    visitor_id: Mapped[str] = mapped_column(
        "visitorId",
        Text,
        ForeignKey(
            "Visitor.id",
            name="ErrorEntry_visitorId_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    error: Mapped[str] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    stack: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)

    visitor: Mapped[Visitor] = relationship(back_populates="error_entries")
