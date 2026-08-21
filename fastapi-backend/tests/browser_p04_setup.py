"""Seed the isolated local services used by P04 browser acceptance."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from en_learning.bootstrap.courses import seed_course_assets, seed_courses
from en_learning.bootstrap.identifiers import stable_identifier
from en_learning.common.config import Settings
from en_learning.db.models import CourseRecord, PaymentRecord, User, WordBook
from en_learning.db.session import Database
from en_learning.services.object_storage import ObjectStorage
from en_learning.services.passwords import hash_password

USER_ID = "p04-browser-user"
PHONE = "13800000000"
PASSWORD = "browser123"
ASSETS = Path(__file__).resolve().parents[2] / "server" / "prisma" / "assets"


def public_avatar_policy(bucket: str) -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        },
        separators=(",", ":"),
    )


async def main() -> None:
    settings = Settings()
    database = Database(settings)
    storage = ObjectStorage(settings)
    try:
        await seed_courses(database.session_factory)
        await seed_course_assets(storage, settings, ASSETS)

        bucket = settings.minio_bucket
        if not await asyncio.to_thread(storage.client.bucket_exists, bucket):
            await asyncio.to_thread(storage.client.make_bucket, bucket)
        await asyncio.to_thread(
            storage.client.set_bucket_policy,
            bucket,
            public_avatar_policy(bucket),
        )

        now = datetime.now(UTC).replace(tzinfo=None)
        course_id = stable_identifier("course", "gk")
        password = hash_password(hashlib.md5(PASSWORD.encode()).hexdigest())
        async with database.session() as session, session.begin():
            user_statement = insert(User.__table__)  # type: ignore[arg-type]
            await session.execute(
                user_statement.values(
                    id=USER_ID,
                    name="P04 浏览器验收",
                    email="p04-browser@example.test",
                    phone=PHONE,
                    password=password,
                    refreshTokenVersion=0,
                    createdAt=now,
                    updatedAt=now,
                ).on_conflict_do_update(
                    index_elements=["id"],
                    set_={"password": password, "updatedAt": now},
                )
            )
            words = []
            for index in range(1, 16):
                word = f"browser-word-{index:02d}"
                words.append(
                    {
                        "id": stable_identifier("p04-browser-word", word),
                        "word": word,
                        "translation": f"浏览器验收词汇 {index}",
                        "frq": str(index),
                        "frqRank": index,
                        "gk": True,
                        "createdAt": now,
                        "updatedAt": now,
                    }
                )
            word_statement = insert(WordBook.__table__)  # type: ignore[arg-type]
            await session.execute(
                word_statement.values(words).on_conflict_do_update(
                    index_elements=["word"],
                    set_={
                        "translation": word_statement.excluded.translation,
                        "frq": word_statement.excluded.frq,
                        "frqRank": word_statement.excluded.frqRank,
                        "gk": True,
                        "updatedAt": now,
                    },
                )
            )
            payment_id = stable_identifier("p04-browser-payment", USER_ID)
            payment_statement = insert(PaymentRecord.__table__)  # type: ignore[arg-type]
            await session.execute(
                payment_statement.values(
                    id=payment_id,
                    userId=USER_ID,
                    outTradeNo="P04-BROWSER-ORDER",
                    amount=Decimal("100"),
                    subject="P04 browser course",
                    body="P04 browser acceptance",
                    tradeStatus="TRADE_SUCCESS",
                    createdAt=now,
                    updatedAt=now,
                ).on_conflict_do_update(
                    index_elements=["outTradeNo"],
                    set_={"tradeStatus": "TRADE_SUCCESS", "updatedAt": now},
                )
            )
            course_record_statement = insert(CourseRecord.__table__)  # type: ignore[arg-type]
            await session.execute(
                course_record_statement.values(
                    id=stable_identifier("p04-browser-course-record", USER_ID),
                    userId=USER_ID,
                    courseId=course_id,
                    isPurchased=True,
                    paymentRecordId=payment_id,
                    createdAt=now,
                    updatedAt=now,
                ).on_conflict_do_update(
                    index_elements=["userId", "courseId"],
                    set_={
                        "isPurchased": True,
                        "paymentRecordId": payment_id,
                        "updatedAt": now,
                    },
                )
            )
    finally:
        await storage.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
