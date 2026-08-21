from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from en_learning.bootstrap.identifiers import stable_identifier
from en_learning.bootstrap.source import sha256_file
from en_learning.common.config import Settings
from en_learning.db.models import Course
from en_learning.services.object_storage import ObjectStorage

COURSE_BUCKET = "course"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True, slots=True)
class CourseSeed:
    name: str
    value: str
    description: str
    teacher: str
    price: Decimal

    @property
    def url(self) -> str:
        return f"/{COURSE_BUCKET}/{self.value}.png"


COURSES: tuple[CourseSeed, ...] = (
    CourseSeed(
        "高考单词",
        "gk",
        "覆盖高考大纲核心词汇，按考频与题型分类，助力考前冲刺提分。",  # noqa: RUF001
        "小余同学",
        Decimal("100"),
    ),
    CourseSeed(
        "中考单词",
        "zk",
        "紧扣中考考纲，初中三年词汇一站式掌握，打好英语基础。",  # noqa: RUF001
        "小满zs",
        Decimal("35"),
    ),
    CourseSeed(
        "GRE单词",
        "gre",
        "GRE 核心词汇与同反义词拓展，适合留学备考与高阶阅读。",  # noqa: RUF001
        "初心哥",
        Decimal("80"),
    ),
    CourseSeed(
        "托福词汇",
        "toefl",
        "托福听说读写高频词 + 学术场景词汇，提升备考效率。",  # noqa: RUF001
        "枫竹",
        Decimal("80000"),
    ),
    CourseSeed(
        "雅思词汇",
        "ielts",
        "雅思考试常考词汇与同义替换，兼顾移民与留学需求。",  # noqa: RUF001
        "ouka",
        Decimal("7000"),
    ),
    CourseSeed(
        "大学英语六级单词",
        "cet6",
        "六级大纲词汇与真题高频词，配合阅读与写作场景记忆。",  # noqa: RUF001
        "章政",
        Decimal("5"),
    ),
    CourseSeed(
        "大学英语四级单词",
        "cet4",
        "四级核心词汇与考点搭配，适合在校生系统备考。",  # noqa: RUF001
        "小余同学",
        Decimal("8"),
    ),
    CourseSeed(
        "考研单词",
        "ky",
        "考研英语一/二通用词汇，结合真题与长难句场景记忆。",  # noqa: RUF001
        "远方",
        Decimal("9.99"),
    ),
)
COURSE_VALUES = tuple(course.value for course in COURSES)


@dataclass(slots=True)
class SeedCounts:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(slots=True)
class AssetCounts:
    bucket_created: bool = False
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    verified: int = 0

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "bucket": COURSE_BUCKET, "expected_objects": len(COURSES)}


class AssetVerificationError(RuntimeError):
    """Course assets or their public object-store representation are invalid."""


def validate_assets(assets_dir: Path, courses: Sequence[CourseSeed] = COURSES) -> None:
    for course in courses:
        path = assets_dir / f"{course.value}.png"
        if not path.is_file():
            raise AssetVerificationError(f"course asset is missing: {path}")
        with path.open("rb") as image:
            if image.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
                raise AssetVerificationError(f"course asset is not a PNG: {path}")


async def seed_courses(
    session_factory: async_sessionmaker[AsyncSession],
) -> SeedCounts:
    async with session_factory() as session, session.begin():
        result = await session.execute(select(Course).where(Course.value.in_(COURSE_VALUES)))
        existing = {course.value: course for course in result.scalars()}
        counts = SeedCounts()
        changed_rows: list[dict[str, Any]] = []
        now = datetime.now(UTC).replace(tzinfo=None)
        for seed in COURSES:
            row = {
                "id": stable_identifier("course", seed.value),
                "name": seed.name,
                "value": seed.value,
                "description": seed.description,
                "teacher": seed.teacher,
                "url": seed.url,
                "price": seed.price,
                "createdAt": now,
                "updatedAt": now,
            }
            current = existing.get(seed.value)
            if current is None:
                counts.inserted += 1
                changed_rows.append(row)
                continue
            if any(
                (getattr(current, field_name) if field_name != "price" else Decimal(current.price))
                != row[field_name]
                for field_name in ("name", "value", "description", "teacher", "url", "price")
            ):
                counts.updated += 1
                changed_rows.append(row)
            else:
                counts.skipped += 1

        if changed_rows:
            statement = postgres_insert(Course.__table__)  # type: ignore[arg-type]
            statement = statement.values(changed_rows)
            excluded = statement.excluded
            statement = statement.on_conflict_do_update(
                index_elements=[Course.__table__.c.value],
                set_={
                    field_name: getattr(excluded, field_name)
                    for field_name in (
                        "name",
                        "description",
                        "teacher",
                        "url",
                        "price",
                        "updatedAt",
                    )
                },
            )
            await session.execute(statement)
    return counts


def public_read_policy() -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "CourseReadObjects",
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{COURSE_BUCKET}/*"],
                }
            ],
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _put_asset(storage: ObjectStorage, path: Path, key: str, digest: str) -> None:
    with path.open("rb") as source:
        storage.client.put_object(
            COURSE_BUCKET,
            key,
            source,
            path.stat().st_size,
            content_type="image/png",
            metadata={"sha256": digest},
        )


async def seed_course_assets(
    storage: ObjectStorage,
    settings: Settings,
    assets_dir: Path,
) -> AssetCounts:
    validate_assets(assets_dir)
    counts = AssetCounts()
    bucket_exists = await asyncio.to_thread(storage.client.bucket_exists, COURSE_BUCKET)
    if not bucket_exists:
        await asyncio.to_thread(storage.client.make_bucket, COURSE_BUCKET)
        counts.bucket_created = True
    await asyncio.to_thread(storage.client.set_bucket_policy, COURSE_BUCKET, public_read_policy())

    for course in COURSES:
        path = assets_dir / f"{course.value}.png"
        key = path.name
        digest = sha256_file(path)
        existed = True
        try:
            before = await asyncio.to_thread(storage.client.stat_object, COURSE_BUCKET, key)
        except S3Error as error:
            if error.code not in {"NoSuchKey", "NoSuchObject", "NoSuchBucket", "NotFound"}:
                raise
            existed = False
            before = None

        metadata_digest = (
            before.metadata.get("x-amz-meta-sha256")
            if before is not None and before.metadata is not None
            else None
        )
        unchanged = (
            before is not None
            and before.size == path.stat().st_size
            and before.content_type == "image/png"
            and metadata_digest == digest
        )
        if unchanged:
            counts.skipped += 1
        else:
            await asyncio.to_thread(_put_asset, storage, path, key, digest)
            if existed:
                counts.updated += 1
            else:
                counts.inserted += 1

        current = await asyncio.to_thread(storage.client.stat_object, COURSE_BUCKET, key)
        current_digest = (
            current.metadata.get("x-amz-meta-sha256") if current.metadata is not None else None
        )
        if (
            current.size != path.stat().st_size
            or current.content_type != "image/png"
            or current_digest != digest
        ):
            raise AssetVerificationError(f"object metadata mismatch: {COURSE_BUCKET}/{key}")

    scheme = "https" if settings.minio_use_ssl else "http"
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        for course in COURSES:
            url = f"{scheme}://{settings.minio_host}/{COURSE_BUCKET}/{course.value}.png"
            response = await client.head(url)
            expected_size = (assets_dir / f"{course.value}.png").stat().st_size
            if (
                response.status_code != 200
                or response.headers.get("content-type") != "image/png"
                or response.headers.get("content-length") != str(expected_size)
            ):
                raise AssetVerificationError(
                    f"public HEAD failed for {COURSE_BUCKET}/{course.value}.png"
                )
            counts.verified += 1
    return counts
