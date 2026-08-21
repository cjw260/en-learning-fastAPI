from sqlalchemy import Enum, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import configure_mappers

from en_learning.db import Base

EXPECTED_TABLES = {
    "User",
    "WordBookRecord",
    "WordBook",
    "PaymentRecord",
    "CourseRecord",
    "Course",
    "Visitor",
    "PageView",
    "TrackEvent",
    "PerformanceEntry",
    "ErrorEntry",
    "AIChatThread",
    "AIChatMessage",
}

EXPECTED_COLUMNS = {
    "User": {
        "id",
        "name",
        "email",
        "phone",
        "address",
        "password",
        "avatar",
        "bio",
        "isTimingTask",
        "timingTaskTime",
        "wordNumber",
        "dayNumber",
        "lastLoginAt",
        "refreshTokenVersion",
        "createdAt",
        "updatedAt",
    },
    "WordBookRecord": {"id", "wordId", "isMaster", "userId", "createdAt", "updatedAt"},
    "WordBook": {
        "id",
        "word",
        "phonetic",
        "definition",
        "translation",
        "pos",
        "collins",
        "oxford",
        "tag",
        "bnc",
        "frq",
        "frqRank",
        "exchange",
        "gk",
        "zk",
        "gre",
        "toefl",
        "ielts",
        "cet6",
        "cet4",
        "ky",
        "createdAt",
        "updatedAt",
    },
    "PaymentRecord": {
        "id",
        "userId",
        "tradeNo",
        "outTradeNo",
        "amount",
        "subject",
        "body",
        "tradeStatus",
        "sendPayTime",
        "createdAt",
        "updatedAt",
    },
    "CourseRecord": {
        "id",
        "userId",
        "courseId",
        "isPurchased",
        "paymentRecordId",
        "createdAt",
        "updatedAt",
    },
    "Course": {
        "id",
        "name",
        "value",
        "description",
        "teacher",
        "url",
        "price",
        "createdAt",
        "updatedAt",
    },
    "Visitor": {
        "id",
        "anonymousId",
        "userId",
        "browser",
        "os",
        "device",
        "createdAt",
        "updatedAt",
    },
    "PageView": {"id", "visitorId", "url", "referrer", "path", "createdAt", "updatedAt"},
    "TrackEvent": {
        "id",
        "visitorId",
        "event",
        "payload",
        "url",
        "createdAt",
        "updatedAt",
    },
    "PerformanceEntry": {
        "id",
        "visitorId",
        "fp",
        "fcp",
        "lcp",
        "inp",
        "cls",
        "createdAt",
        "updatedAt",
    },
    "ErrorEntry": {
        "id",
        "visitorId",
        "error",
        "message",
        "stack",
        "url",
        "createdAt",
        "updatedAt",
    },
    "AIChatThread": {"id", "userId", "role", "createdAt", "updatedAt"},
    "AIChatMessage": {
        "id",
        "threadId",
        "position",
        "role",
        "content",
        "reasoning",
        "createdAt",
        "updatedAt",
    },
}

EXPECTED_NULLABLE_COLUMNS = {
    "User": {"email", "address", "avatar", "bio", "lastLoginAt"},
    "WordBookRecord": set(),
    "WordBook": {
        "phonetic",
        "definition",
        "translation",
        "pos",
        "collins",
        "oxford",
        "tag",
        "bnc",
        "frq",
        "frqRank",
        "exchange",
        "gk",
        "zk",
        "gre",
        "toefl",
        "ielts",
        "cet6",
        "cet4",
        "ky",
    },
    "PaymentRecord": {"tradeNo", "sendPayTime"},
    "CourseRecord": {"paymentRecordId"},
    "Course": {"description"},
    "Visitor": {"userId", "browser", "os", "device"},
    "PageView": {"referrer"},
    "TrackEvent": {"payload", "url"},
    "PerformanceEntry": {"fp", "fcp", "lcp", "inp", "cls"},
    "ErrorEntry": {"message", "stack", "url"},
    "AIChatThread": set(),
    "AIChatMessage": {"reasoning"},
}


def test_metadata_matches_legacy_tables_and_special_types() -> None:
    configure_mappers()
    assert set(Base.metadata.tables) == EXPECTED_TABLES

    payment = Base.metadata.tables["PaymentRecord"]
    assert isinstance(payment.c.amount.type, Numeric)
    assert payment.c.amount.type.precision == 65
    assert payment.c.amount.type.scale == 30
    assert isinstance(payment.c.tradeStatus.type, Enum)
    assert payment.c.tradeStatus.type.name == "TradeStatus"
    assert payment.c.tradeStatus.type.enums == [
        "NOT_PAY",
        "WAIT_BUYER_PAY",
        "TRADE_CLOSED",
        "TRADE_SUCCESS",
        "TRADE_FINISHED",
    ]

    track_event = Base.metadata.tables["TrackEvent"]
    assert isinstance(track_event.c.payload.type, JSONB)

    user = Base.metadata.tables["User"]
    assert isinstance(user.c.createdAt.type, TIMESTAMP)
    assert user.c.createdAt.type.timezone is False
    assert user.c.createdAt.type.precision == 3

    word_book = Base.metadata.tables["WordBook"]
    assert isinstance(word_book.c.frqRank.type, Integer)


def test_metadata_preserves_all_columns_nullability_and_primary_keys() -> None:
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        table = Base.metadata.tables[table_name]
        assert set(table.c.keys()) == expected_columns
        assert {column.name for column in table.c if column.nullable} == (
            EXPECTED_NULLABLE_COLUMNS[table_name]
        )
        assert table.primary_key.name == f"{table_name}_pkey"
        assert {column.name for column in table.primary_key.columns} == {"id"}


def test_metadata_preserves_index_names_and_uniqueness() -> None:
    expected = {
        "User": {"User_email_key": True, "User_phone_key": True},
        "WordBookRecord": {"WordBookRecord_userId_wordId_key": True},
        "WordBook": {
            "WordBook_word_key": True,
            "WordBook_tag_idx": False,
            "WordBook_word_tag_idx": False,
            "WordBook_frqRank_word_id_idx": False,
        },
        "PaymentRecord": {
            "PaymentRecord_outTradeNo_key": True,
            "PaymentRecord_tradeNo_idx": False,
        },
        "CourseRecord": {"CourseRecord_userId_courseId_key": True},
        "Course": {"Course_value_key": True},
        "Visitor": {
            "Visitor_anonymousId_key": True,
            "Visitor_userId_idx": False,
            "Visitor_anonymousId_idx": False,
        },
        "PageView": {
            "PageView_visitorId_createdAt_idx": False,
            "PageView_path_createdAt_idx": False,
        },
        "TrackEvent": {
            "TrackEvent_visitorId_createdAt_idx": False,
            "TrackEvent_event_createdAt_idx": False,
        },
        "PerformanceEntry": {
            "PerformanceEntry_fp_createdAt_idx": False,
            "PerformanceEntry_fcp_createdAt_idx": False,
            "PerformanceEntry_lcp_createdAt_idx": False,
            "PerformanceEntry_inp_createdAt_idx": False,
            "PerformanceEntry_cls_createdAt_idx": False,
            "PerformanceEntry_fp_fcp_lcp_inp_cls_createdAt_idx": False,
        },
        "ErrorEntry": {
            "ErrorEntry_visitorId_createdAt_idx": False,
            "ErrorEntry_error_createdAt_idx": False,
        },
        "AIChatThread": {"AIChatThread_userId_role_key": True},
        "AIChatMessage": {
            "AIChatMessage_threadId_position_key": True,
            "AIChatMessage_threadId_createdAt_idx": False,
        },
    }
    for table_name, indexes in expected.items():
        actual = {index.name: index.unique for index in Base.metadata.tables[table_name].indexes}
        assert actual == indexes


def test_all_foreign_keys_keep_cascade_semantics() -> None:
    foreign_keys = [
        foreign_key
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_key_constraints
    ]
    assert len(foreign_keys) == 13
    actual = {
        (
            foreign_key.name,
            foreign_key.table.name,
            tuple(column.name for column in foreign_key.columns),
            tuple(element.target_fullname for element in foreign_key.elements),
        )
        for foreign_key in foreign_keys
    }
    assert actual == {
        ("WordBookRecord_userId_fkey", "WordBookRecord", ("userId",), ("User.id",)),
        ("WordBookRecord_wordId_fkey", "WordBookRecord", ("wordId",), ("WordBook.id",)),
        ("PaymentRecord_userId_fkey", "PaymentRecord", ("userId",), ("User.id",)),
        (
            "CourseRecord_paymentRecordId_fkey",
            "CourseRecord",
            ("paymentRecordId",),
            ("PaymentRecord.id",),
        ),
        ("CourseRecord_userId_fkey", "CourseRecord", ("userId",), ("User.id",)),
        ("CourseRecord_courseId_fkey", "CourseRecord", ("courseId",), ("Course.id",)),
        ("Visitor_userId_fkey", "Visitor", ("userId",), ("User.id",)),
        ("PageView_visitorId_fkey", "PageView", ("visitorId",), ("Visitor.id",)),
        ("TrackEvent_visitorId_fkey", "TrackEvent", ("visitorId",), ("Visitor.id",)),
        (
            "PerformanceEntry_visitorId_fkey",
            "PerformanceEntry",
            ("visitorId",),
            ("Visitor.id",),
        ),
        ("ErrorEntry_visitorId_fkey", "ErrorEntry", ("visitorId",), ("Visitor.id",)),
        ("AIChatThread_userId_fkey", "AIChatThread", ("userId",), ("User.id",)),
        (
            "AIChatMessage_threadId_fkey",
            "AIChatMessage",
            ("threadId",),
            ("AIChatThread.id",),
        ),
    }
    for foreign_key in foreign_keys:
        assert foreign_key.ondelete == "CASCADE"
        assert foreign_key.onupdate == "CASCADE"


def test_relationships_have_explicit_delete_orphan_cascade() -> None:
    configure_mappers()
    collection_relationships = [
        relationship
        for mapper in Base.registry.mappers
        for relationship in mapper.relationships
        if relationship.uselist
    ]
    assert len(collection_relationships) == 13
    for relationship in collection_relationships:
        assert relationship.passive_deletes is True
    without_delete_orphan = {
        f"{relationship.parent.class_.__name__}.{relationship.key}"
        for relationship in collection_relationships
        if "delete-orphan" not in relationship.cascade
    }
    assert without_delete_orphan == {"User.visitors", "PaymentRecord.course_records"}
