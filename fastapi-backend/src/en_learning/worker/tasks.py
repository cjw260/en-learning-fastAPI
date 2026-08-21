from __future__ import annotations

import asyncio
import html
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from redis.asyncio import Redis
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from taskiq import Context, TaskiqDepends

from en_learning.common.config import Settings
from en_learning.db.models import (
    BackgroundJob,
    CourseRecord,
    PaymentRecord,
    TradeStatus,
    User,
    WordBook,
    WordBookRecord,
    utc_now_naive,
)
from en_learning.db.session import Database
from en_learning.realtime.socketio import SocketPublisher
from en_learning.services.email import EmailSender
from en_learning.worker.broker import broker
from en_learning.worker.broker import settings as broker_settings

logger = logging.getLogger("en_learning.worker.tasks")
TASKIQ_CONTEXT: Any = TaskiqDepends()


class WorkerResources(Protocol):
    database: Database
    redis: Redis
    socket_publisher: SocketPublisher
    email_sender: EmailSender


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: str
    kind: str
    user_id: str
    payment_record_id: str | None
    payload: dict[str, object]
    attempt: int
    max_attempts: int


def _day_bounds(local_date: date, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(local_date, time.min, timezone)
    end = start + timedelta(days=1)
    return (
        start.astimezone(UTC).replace(tzinfo=None),
        end.astimezone(UTC).replace(tzinfo=None),
    )


async def _claim_job(
    job_id: str,
    resources: WorkerResources,
    settings: Settings,
) -> ClaimedJob | None:
    now = utc_now_naive()
    async with resources.database.session() as session:
        async with session.begin():
            job = await session.scalar(
                select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update()
            )
            if job is None or job.status == "COMPLETED":
                return None
            if job.status == "PROCESSING" and job.locked_until is not None:
                if job.locked_until > now:
                    return None
            if job.status == "FAILED" and job.attempts >= job.max_attempts:
                return None
            if job.scheduled_for > now:
                return None
            job.status = "PROCESSING"
            job.attempts += 1
            job.locked_until = now + timedelta(seconds=settings.worker_job_lock_seconds)
            job.last_error_code = None
            await session.flush()
            return ClaimedJob(
                id=job.id,
                kind=job.kind,
                user_id=job.user_id,
                payment_record_id=job.payment_record_id,
                payload=dict(job.payload),
                attempt=job.attempts,
                max_attempts=job.max_attempts,
            )


async def _complete_job(job_id: str, resources: WorkerResources) -> None:
    async with resources.database.session() as session:
        async with session.begin():
            job = await session.scalar(
                select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update()
            )
            if job is not None and job.status == "PROCESSING":
                job.status = "COMPLETED"
                job.completed_at = utc_now_naive()
                job.locked_until = None


async def _fail_job(
    claimed: ClaimedJob,
    resources: WorkerResources,
    settings: Settings,
    exception: BaseException,
) -> None:
    async with resources.database.session() as session:
        async with session.begin():
            job = await session.scalar(
                select(BackgroundJob).where(BackgroundJob.id == claimed.id).with_for_update()
            )
            if job is None or job.status != "PROCESSING":
                return
            job.last_error_code = type(exception).__name__[:64]
            job.locked_until = None
            if job.attempts >= job.max_attempts:
                job.status = "FAILED"
            else:
                job.status = "PENDING"
                delay = min(
                    settings.worker_retry_delay_seconds * (2 ** max(job.attempts - 1, 0)),
                    300,
                )
                job.scheduled_for = utc_now_naive() + timedelta(seconds=delay)


async def _deliver_payment(claimed: ClaimedJob, resources: WorkerResources) -> None:
    if claimed.payment_record_id is None:
        raise ValueError("payment job has no payment record")
    async with resources.database.session() as session:
        payment = await session.scalar(
            select(PaymentRecord).where(PaymentRecord.id == claimed.payment_record_id)
        )
        if payment is None or payment.trade_status not in {
            TradeStatus.TRADE_SUCCESS,
            TradeStatus.TRADE_FINISHED,
        }:
            raise ValueError("payment is not successful")
        course_id = claimed.payload.get("courseId")
        if not isinstance(course_id, str):
            raise ValueError("payment job has no course")
        purchased = await session.scalar(
            select(CourseRecord.id).where(
                CourseRecord.course_id == course_id,
                CourseRecord.user_id == claimed.user_id,
                CourseRecord.is_purchased.is_(True),
            )
        )
        if purchased is None:
            raise ValueError("payment entitlement is missing")
    await resources.socket_publisher.payment_success(claimed.user_id)


def _digest_html(name: str, total: int, words: list[str]) -> str:
    items = "".join(f"<li>{html.escape(word)}</li>" for word in words)
    return (
        "<!doctype html><html><body>"
        f"<h1>{html.escape(name)} 的每日单词记忆报告</h1>"
        f"<p>今日学习 {len(words)} 个单词, 累计掌握 {total} 个。</p>"
        f"<ul>{items}</ul>"
        "</body></html>"
    )


async def _deliver_digest(
    claimed: ClaimedJob,
    resources: WorkerResources,
    settings: Settings,
) -> None:
    raw_date = claimed.payload.get("date")
    if not isinstance(raw_date, str):
        raise ValueError("digest job has no date")
    local_date = date.fromisoformat(raw_date)
    start, end = _day_bounds(local_date, ZoneInfo(settings.digest_timezone))
    async with resources.database.session() as session:
        user = await session.scalar(select(User).where(User.id == claimed.user_id))
        if user is None or user.email is None or not user.is_timing_task:
            return
        words = list(
            (
                await session.scalars(
                    select(WordBook.word)
                    .join(WordBookRecord, WordBookRecord.word_id == WordBook.id)
                    .where(
                        WordBookRecord.user_id == user.id,
                        WordBookRecord.created_at >= start,
                        WordBookRecord.created_at < end,
                    )
                    .order_by(WordBookRecord.created_at, WordBook.word)
                )
            ).all()
        )
        if not words:
            return
        recipient = user.email
        name = user.name
        total = user.word_number
    await resources.email_sender.send_html(
        to=recipient,
        subject="每日单词记忆报告",
        html=_digest_html(name, total, words),
        message_id=claimed.id,
    )


async def run_background_job(
    job_id: str,
    resources: WorkerResources,
    settings: Settings,
) -> bool:
    claimed = await _claim_job(job_id, resources, settings)
    if claimed is None:
        return False
    try:
        async with asyncio.timeout(settings.worker_job_timeout_seconds):
            if claimed.kind == "PAYMENT_SUCCESS":
                await _deliver_payment(claimed, resources)
            elif claimed.kind == "EMAIL_DIGEST":
                await _deliver_digest(claimed, resources, settings)
            else:
                raise ValueError("unsupported background job kind")
    except BaseException as exception:
        await _fail_job(claimed, resources, settings, exception)
        logger.warning(
            "worker.job_failed",
            extra={
                "jobKind": claimed.kind,
                "attempt": claimed.attempt,
                "failureType": type(exception).__name__,
            },
        )
        raise
    await _complete_job(claimed.id, resources)
    logger.info("worker.job_completed", extra={"jobKind": claimed.kind})
    return True


@broker.task(
    retry_on_error=True,
    max_retries=broker_settings.worker_job_max_attempts - 1,
    delay=broker_settings.worker_retry_delay_seconds,
)
async def execute_background_job(
    job_id: str,
    context: Context = TASKIQ_CONTEXT,
) -> bool:
    resources: WorkerResources = context.state.en_learning_resources
    settings: Settings = context.state.en_learning_settings
    return await run_background_job(job_id, resources, settings)


async def scan_digest_jobs(
    resources: WorkerResources,
    settings: Settings,
    enqueue: Callable[[str], Awaitable[object]],
    *,
    now: datetime | None = None,
) -> int:
    timezone = ZoneInfo(settings.digest_timezone)
    local_now = now.astimezone(timezone) if now is not None else datetime.now(timezone)
    minute_key = local_now.strftime("%Y%m%d%H%M")
    if not await resources.redis.set(
        f"en-learning:digest-scan:{minute_key}",
        uuid.uuid4().hex,
        ex=120,
        nx=True,
    ):
        return 0
    local_date = local_now.date()
    start, end = _day_bounds(local_date, timezone)
    current_time = local_now.strftime("%H:%M:%S")
    async with resources.database.session() as session:
        user_ids = list(
            (
                await session.scalars(
                    select(User.id).where(
                        User.is_timing_task.is_(True),
                        User.email.is_not(None),
                        User.timing_task_time <= current_time,
                        exists(
                            select(WordBookRecord.id).where(
                                WordBookRecord.user_id == User.id,
                                WordBookRecord.created_at >= start,
                                WordBookRecord.created_at < end,
                            )
                        ),
                    )
                )
            ).all()
        )
        if user_ids:
            now_naive = utc_now_naive()
            statement = (
                insert(BackgroundJob.__table__)  # type: ignore[arg-type]
                .values(
                    [
                        {
                            "id": uuid.uuid4().hex,
                            "taskKey": f"email-digest:{local_date.isoformat()}:{user_id}",
                            "kind": "EMAIL_DIGEST",
                            "status": "PENDING",
                            "userId": user_id,
                            "payload": {"date": local_date.isoformat()},
                            "attempts": 0,
                            "maxAttempts": settings.worker_job_max_attempts,
                            "scheduledFor": now_naive,
                            "createdAt": now_naive,
                            "updatedAt": now_naive,
                        }
                        for user_id in user_ids
                    ]
                )
                .on_conflict_do_nothing(index_elements=["taskKey"])
            )
            await session.execute(statement)
            await session.commit()
        jobs = list(
            (
                await session.scalars(
                    select(BackgroundJob).where(
                        BackgroundJob.kind == "EMAIL_DIGEST",
                        BackgroundJob.status == "PENDING",
                        BackgroundJob.task_key.startswith(
                            f"email-digest:{local_date.isoformat()}:"
                        ),
                    )
                )
            ).all()
        )
    for job in jobs:
        await enqueue(job.id)
    return len(jobs)


@broker.task(
    schedule=[{"cron": "* * * * *"}],
    retry_on_error=True,
    max_retries=broker_settings.worker_job_max_attempts - 1,
    delay=broker_settings.worker_retry_delay_seconds,
)
async def schedule_daily_digests(context: Context = TASKIQ_CONTEXT) -> int:
    resources: WorkerResources = context.state.en_learning_resources
    settings: Settings = context.state.en_learning_settings

    async def enqueue(job_id: str) -> object:
        return await execute_background_job.kiq(job_id)

    return await scan_digest_jobs(resources, settings, enqueue)


async def replay_due_jobs(
    resources: WorkerResources,
    enqueue: Callable[[str], Awaitable[object]],
    *,
    include_failed: bool = False,
    limit: int = 100,
) -> int:
    now = utc_now_naive()
    status_condition = or_(
        BackgroundJob.status == "PENDING",
        and_(
            BackgroundJob.status == "PROCESSING",
            BackgroundJob.locked_until < now,
        ),
    )
    if include_failed:
        status_condition = or_(status_condition, BackgroundJob.status == "FAILED")
    async with resources.database.session() as session:
        async with session.begin():
            jobs = list(
                (
                    await session.scalars(
                        select(BackgroundJob)
                        .where(
                            status_condition,
                            BackgroundJob.scheduled_for <= now,
                        )
                        .order_by(BackgroundJob.scheduled_for, BackgroundJob.id)
                        .limit(limit)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            for job in jobs:
                if job.status in {"FAILED", "PROCESSING"}:
                    job.status = "PENDING"
                    job.locked_until = None
                    if include_failed and job.attempts >= job.max_attempts:
                        job.attempts = 0
    for job in jobs:
        await enqueue(job.id)
    return len(jobs)


@broker.task(
    schedule=[{"cron": "* * * * *"}],
    retry_on_error=True,
    max_retries=broker_settings.worker_job_max_attempts - 1,
    delay=broker_settings.worker_retry_delay_seconds,
)
async def recover_due_background_jobs(context: Context = TASKIQ_CONTEXT) -> int:
    resources: WorkerResources = context.state.en_learning_resources

    async def enqueue(job_id: str) -> object:
        return await execute_background_job.kiq(job_id)

    return await replay_due_jobs(resources, enqueue)
