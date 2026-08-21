from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path

from minio import Minio
from sqlalchemy import select

from en_learning.bootstrap.courses import COURSE_BUCKET, COURSES, seed_course_assets, seed_courses
from en_learning.common.config import Settings
from en_learning.db.models import Course
from en_learning.db.session import Database
from en_learning.services.object_storage import ObjectStorage
from tests.conftest import PROJECT_ROOT, settings_values


async def seed_courses_twice(
    settings: Settings,
) -> tuple[dict[str, int], dict[str, int], list[Course]]:
    database = Database(settings)
    try:
        first = await seed_courses(database.session_factory)
        second = await seed_courses(database.session_factory)
        async with database.session() as session:
            result = await session.execute(select(Course).order_by(Course.value))
            courses = list(result.scalars())
        return first.to_dict(), second.to_dict(), courses
    finally:
        await database.close()


def test_course_seed_preserves_legacy_values_and_is_idempotent(
    migrated_postgres_url: str,
) -> None:
    settings = Settings(
        _env_file=None,
        **settings_values(database_url=migrated_postgres_url),
    )
    first, second, courses = asyncio.run(seed_courses_twice(settings))

    assert first["inserted"] + first["updated"] + first["skipped"] == 8
    assert second == {"inserted": 0, "updated": 0, "skipped": 8}
    assert {course.value for course in courses} >= {seed.value for seed in COURSES}
    expected = {seed.value: seed for seed in COURSES}
    for course in courses:
        if course.value not in expected:
            continue
        seed = expected[course.value]
        assert course.name == seed.name
        assert course.description == seed.description
        assert course.teacher == seed.teacher
        assert Decimal(course.price) == seed.price
        assert course.url == f"/course/{course.value}.png"


async def seed_assets_twice(
    settings: Settings,
    assets_dir: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    storage = ObjectStorage(settings)
    try:
        first = await seed_course_assets(storage, settings, assets_dir)
        second = await seed_course_assets(storage, settings, assets_dir)
        return first.to_dict(), second.to_dict()
    finally:
        await storage.close()


def test_minio_course_assets_are_public_mime_correct_and_idempotent(
    minio_values: dict[str, object],
) -> None:
    settings = Settings(_env_file=None, **settings_values(**minio_values))
    assets_dir = PROJECT_ROOT.parent / "server" / "prisma" / "assets"
    first, second = asyncio.run(seed_assets_twice(settings, assets_dir))

    assert first["inserted"] == 8
    assert first["verified"] == 8
    assert second["inserted"] == 0
    assert second["updated"] == 0
    assert second["skipped"] == 8
    assert second["verified"] == 8

    client = Minio(
        settings.minio_host,
        access_key=settings.minio_access_key.get_secret_value(),
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=False,
    )
    objects = list(client.list_objects(COURSE_BUCKET, recursive=True))
    assert {item.object_name for item in objects} == {f"{seed.value}.png" for seed in COURSES}
    for seed in COURSES:
        stat = client.stat_object(COURSE_BUCKET, f"{seed.value}.png")
        assert stat.content_type == "image/png"
        assert stat.size > 0
