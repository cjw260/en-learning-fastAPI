from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from en_learning.bootstrap.courses import (
    COURSE_VALUES,
    seed_course_assets,
    seed_courses,
)
from en_learning.bootstrap.ecdict import BatchImportError, import_ecdict
from en_learning.common.config import Settings
from en_learning.db.models import (
    Course,
    CourseRecord,
    ErrorEntry,
    PageView,
    PaymentRecord,
    PerformanceEntry,
    TrackEvent,
    User,
    Visitor,
    WordBook,
    WordBookRecord,
)
from en_learning.db.session import Database
from en_learning.services.object_storage import ObjectStorage

PROTECTED_MODELS = (
    User,
    WordBookRecord,
    PaymentRecord,
    CourseRecord,
    Visitor,
    PageView,
    TrackEvent,
    PerformanceEntry,
    ErrorEntry,
)


class BootstrapVerificationError(RuntimeError):
    """The final state differs from the deterministic P02 contract."""


class BootstrapStepError(RuntimeError):
    def __init__(self, step: str, partial_report: dict[str, Any]) -> None:
        super().__init__(f"bootstrap step failed: {step}; completed steps are safe to rerun")
        self.step = step
        self.partial_report = partial_report


def run_migrations(backend_root: Path) -> None:
    configuration = Config(str(backend_root / "alembic.ini"))
    configuration.set_main_option("script_location", str(backend_root / "migrations"))
    command.upgrade(configuration, "head")


async def protected_counts(database: Database) -> dict[str, int]:
    async with database.session() as session:
        counts: dict[str, int] = {}
        for model in PROTECTED_MODELS:
            counts[model.__tablename__] = int(
                await session.scalar(select(func.count()).select_from(model)) or 0
            )
        return counts


async def scalar_count(database: Database, model: Any) -> int:
    async with database.session() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def seeded_course_values(database: Database) -> list[str]:
    async with database.session() as session:
        result = await session.scalars(
            select(Course.value).where(Course.value.in_(COURSE_VALUES)).order_by(Course.value)
        )
        return list(result)


async def run_data_bootstrap(
    settings: Settings,
    *,
    source_path: Path,
    rejects_path: Path,
    assets_dir: Path,
    batch_size: int,
) -> dict[str, Any]:
    database = Database(settings)
    storage = ObjectStorage(settings)
    partial: dict[str, Any] = {}
    try:
        before_protected = await protected_counts(database)
        partial["protected_business_rows_before"] = before_protected
        partial["rejects_path"] = str(rejects_path)
        try:
            word_counts = await import_ecdict(
                source_path,
                rejects_path,
                database.session_factory,
                batch_size=batch_size,
            )
            word_total = await scalar_count(database, WordBook)
            partial["words"] = {**word_counts.to_dict(), "database_total": word_total}
        except BatchImportError:
            raise
        except Exception as error:
            raise BootstrapStepError("words", partial) from error
        try:
            course_counts = await seed_courses(database.session_factory)
            course_total = await scalar_count(database, Course)
            partial["courses"] = {**course_counts.to_dict(), "database_total": course_total}
        except Exception as error:
            raise BootstrapStepError("courses", partial) from error
        try:
            asset_counts = await seed_course_assets(storage, settings, assets_dir)
            partial["objects"] = asset_counts.to_dict()
        except Exception as error:
            raise BootstrapStepError("objects", partial) from error
        try:
            after_protected = await protected_counts(database)
            partial["protected_business_rows_after"] = after_protected
            if after_protected != before_protected:
                raise BootstrapVerificationError(
                    "bootstrap modified protected business-data tables"
                )
            course_values = await seeded_course_values(database)
            if course_values != sorted(COURSE_VALUES):
                raise BootstrapVerificationError("the eight deterministic courses are incomplete")
        except Exception as error:
            raise BootstrapStepError("verification", partial) from error
        return partial
    finally:
        try:
            await storage.close()
        finally:
            await database.close()
