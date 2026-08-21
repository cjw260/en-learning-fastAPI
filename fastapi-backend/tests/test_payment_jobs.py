from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import func, select

from en_learning.api.payments import _next_trade_status
from en_learning.api.router import router
from en_learning.common.application import ServiceKind, create_http_application
from en_learning.common.auth import encode_token
from en_learning.common.config import Settings, get_settings
from en_learning.db.models import (
    BackgroundJob,
    Course,
    CourseRecord,
    PaymentRecord,
    TradeStatus,
    User,
    WordBook,
    WordBookRecord,
    utc_now_naive,
)
from en_learning.db.session import Database
from en_learning.services.alipay import AlipayGateway, signature_content
from tests.conftest import settings_environment, settings_values

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_migrated_url(isolated_postgres_url: str) -> str:
    alembic = Path(sys.executable).with_name("alembic")
    result = subprocess.run(
        [str(alembic), "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "DATABASE_URL": isolated_postgres_url},
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return isolated_postgres_url


def payment_settings(database_url: str, **overrides: Any) -> Settings:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return Settings(
        _env_file=None,
        **settings_values(
            database_url=database_url,
            alipay_private_key=private_pem,
            alipay_public_key=public_pem,
            **overrides,
        ),
    )


class FakeSocketPublisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.users: list[str] = []

    async def payment_success(self, user_id: str) -> None:
        if self.fail:
            raise ConnectionError("socket unavailable")
        self.users.append(user_id)


class FakeEmailSender:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[dict[str, str]] = []

    async def send_html(self, **values: str) -> None:
        if self.fail:
            raise ConnectionError("smtp unavailable")
        self.messages.append(values)


class NullStorage:
    async def close(self) -> None:
        return None


class PaymentResources:
    def __init__(
        self,
        settings: Settings,
        *,
        redis: Redis | None = None,
        socket_publisher: FakeSocketPublisher | None = None,
        email_sender: FakeEmailSender | None = None,
    ) -> None:
        self.database = Database(settings)
        self.redis = redis or Redis.from_url(str(settings.redis_url), decode_responses=True)
        self.object_storage = NullStorage()
        self.socket_publisher = socket_publisher or FakeSocketPublisher()
        self.email_sender = email_sender or FakeEmailSender()

    def readiness_checks(self) -> dict[str, Callable[[], Awaitable[None]]]:
        return {}

    async def close(self) -> None:
        await self.redis.aclose()
        await self.database.close()


def create_payment_app(
    settings: Settings,
    resources: PaymentResources,
    enqueued: list[str],
) -> FastAPI:
    app = create_http_application(
        ServiceKind.CORE,
        settings=settings,
        resource_factory=lambda _: resources,
    )
    app.include_router(router)

    async def enqueue(job_id: str) -> None:
        enqueued.append(job_id)

    app.state.enqueue_background_job = enqueue
    return app


@asynccontextmanager
async def payment_client(
    settings: Settings,
    resources: PaymentResources,
    enqueued: list[str],
) -> AsyncIterator[AsyncClient]:
    app = create_payment_app(settings, resources, enqueued)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            yield client


async def seed_user_course(database: Database) -> tuple[User, Course]:
    user = User(
        id=uuid.uuid4().hex,
        name="Payment Tester",
        phone=f"13{uuid.uuid4().int % 1_000_000_000:09d}",
        email="payment-tester@example.test",
        password="unused",
        refresh_token_version=1,
    )
    course = Course(
        id=uuid.uuid4().hex,
        name="Trusted Course",
        value=f"course-{uuid.uuid4().hex}",
        description="Trusted description",
        teacher="Trusted Teacher",
        url="/course/test.png",
        price=Decimal("88.50"),
    )
    async with database.session() as session:
        session.add_all([user, course])
        await session.commit()
    return user, course


def access_headers(settings: Settings, user: User) -> dict[str, str]:
    token = encode_token(
        settings,
        user_id=user.id,
        name=user.name,
        email=user.email,
        token_type="access",
        refresh_version=user.refresh_token_version,
    )
    return {"Authorization": f"Bearer {token}"}


def signed_notification(
    settings: Settings,
    *,
    out_trade_no: str,
    amount: str = "88.50",
    status: str = "TRADE_SUCCESS",
    trade_no: str = "20260821000001",
    app_id: str | None = None,
    seller_id: str | None = None,
) -> dict[str, str]:
    parameters = {
        "app_id": app_id or settings.alipay_app_id,
        "seller_id": seller_id or settings.alipay_seller_id,
        "out_trade_no": out_trade_no,
        "trade_no": trade_no,
        "trade_status": status,
        "total_amount": amount,
        "gmt_payment": "2026-08-21 12:00:00",
        "body": json.dumps({"courseId": "ignored-for-new-orders", "userId": "ignored"}),
        "sign_type": "RSA2",
    }
    parameters["sign"] = AlipayGateway(settings).sign(signature_content(parameters))
    return parameters


@pytest.mark.asyncio
async def test_payment_facts_signature_idempotency_and_status(
    isolated_migrated_url: str,
) -> None:
    settings = payment_settings(isolated_migrated_url)
    resources = PaymentResources(settings)
    user, course = await seed_user_course(resources.database)
    enqueued: list[str] = []
    headers = access_headers(settings, user)

    async with payment_client(settings, resources, enqueued) as client:
        unauthenticated = await client.post(
            "/api/v1/pay/create",
            json={
                "subject": "Forged",
                "body": "Forged",
                "total_amount": "0.01",
                "courseId": course.id,
            },
        )
        assert unauthenticated.status_code == 401

        created = await client.post(
            "/api/v1/pay/create",
            headers=headers,
            json={
                "subject": "Forged subject",
                "body": "Forged body",
                "total_amount": "0.01",
                "courseId": course.id,
            },
        )
        assert created.status_code == 200, created.text
        result = created.json()["data"]
        query = parse_qs(urlparse(result["payUrl"]).query)
        biz_content = json.loads(query["biz_content"][0])
        assert biz_content["total_amount"] == "88.50"
        assert biz_content["subject"] == "Trusted Course"
        assert result["timeExpire"] > int(datetime.now(UTC).timestamp() * 1000)

        async with resources.database.session() as session:
            payment = await session.scalar(select(PaymentRecord))
            assert payment is not None
            assert payment.user_id == user.id
            assert payment.course_id == course.id
        assert payment.amount == Decimal("88.500000000000000000000000000000")
        assert payment.subject == "Trusted Course"
        out_trade_no = payment.out_trade_no
        assert result["outTradeNo"] == out_trade_no == biz_content["out_trade_no"]

        invalid_signature = signed_notification(settings, out_trade_no=out_trade_no)
        invalid_signature["sign"] = "not-a-signature"
        rejected = await client.post("/api/v1/pay/notify", data=invalid_signature)
        assert rejected.status_code == 400
        assert rejected.text == "failure"

        wrong_amount = signed_notification(settings, out_trade_no=out_trade_no, amount="0.01")
        rejected = await client.post("/api/v1/pay/notify", data=wrong_amount)
        assert rejected.status_code == 400

        unknown = signed_notification(settings, out_trade_no="UNKNOWN")
        rejected = await client.post("/api/v1/pay/notify", data=unknown)
        assert rejected.status_code == 400

        wrong_merchant = signed_notification(
            settings,
            out_trade_no=out_trade_no,
            app_id="other-app",
            seller_id="other-seller",
        )
        rejected = await client.post("/api/v1/pay/notify", data=wrong_merchant)
        assert rejected.status_code == 400

        valid = signed_notification(settings, out_trade_no=out_trade_no)
        accepted, duplicate = await asyncio.gather(
            client.post("/api/v1/pay/notify", data=valid),
            client.post("/api/v1/pay/notify", data=valid),
        )
        stale = signed_notification(
            settings,
            out_trade_no=out_trade_no,
            status="TRADE_CLOSED",
        )
        stale_result = await client.post("/api/v1/pay/notify", data=stale)
        assert accepted.status_code == duplicate.status_code == stale_result.status_code == 200
        assert accepted.text == duplicate.text == stale_result.text == "success"
        assert len(enqueued) == 1

        status = await client.get(f"/api/v1/pay/status/{out_trade_no}", headers=headers)
        assert status.status_code == 200
        assert status.json()["data"] == {
            "outTradeNo": out_trade_no,
            "tradeStatus": "TRADE_SUCCESS",
            "isPurchased": True,
        }

    database = Database(settings)
    async with database.session() as session:
        assert await session.scalar(select(func.count(CourseRecord.id))) == 1
        assert await session.scalar(select(func.count(BackgroundJob.id))) == 1
    await database.close()


@pytest.mark.asyncio
async def test_payment_commit_survives_immediate_queue_failure(
    isolated_migrated_url: str,
) -> None:
    settings = payment_settings(isolated_migrated_url)
    resources = PaymentResources(settings)
    user, course = await seed_user_course(resources.database)
    app = create_payment_app(settings, resources, [])

    async def unavailable_queue(_: str) -> None:
        raise ConnectionError("queue unavailable")

    app.state.enqueue_background_job = unavailable_queue
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/api/v1/pay/create",
                headers=access_headers(settings, user),
                json={"courseId": course.id},
            )
            assert created.status_code == 200
            async with resources.database.session() as session:
                payment = await session.scalar(select(PaymentRecord))
                assert payment is not None
            accepted = await client.post(
                "/api/v1/pay/notify",
                data=signed_notification(settings, out_trade_no=payment.out_trade_no),
            )
            assert accepted.status_code == 200
            status = await client.get(
                f"/api/v1/pay/status/{payment.out_trade_no}",
                headers=access_headers(settings, user),
            )
            assert status.json()["data"]["isPurchased"] is True

    database = Database(settings)
    async with database.session() as session:
        job = await session.scalar(select(BackgroundJob))
        assert job is not None
        assert job.status == "PENDING"
    await database.close()


@pytest.mark.parametrize(
    ("current", "incoming", "expected", "rejects"),
    [
        (TradeStatus.NOT_PAY, TradeStatus.WAIT_BUYER_PAY, TradeStatus.WAIT_BUYER_PAY, False),
        (TradeStatus.WAIT_BUYER_PAY, TradeStatus.TRADE_SUCCESS, TradeStatus.TRADE_SUCCESS, False),
        (TradeStatus.TRADE_SUCCESS, TradeStatus.TRADE_CLOSED, None, False),
        (TradeStatus.TRADE_FINISHED, TradeStatus.WAIT_BUYER_PAY, None, False),
        (TradeStatus.TRADE_CLOSED, TradeStatus.TRADE_SUCCESS, None, True),
    ],
)
def test_payment_status_machine_rejects_or_ignores_out_of_order_callbacks(
    current: TradeStatus,
    incoming: TradeStatus,
    expected: TradeStatus | None,
    rejects: bool,
) -> None:
    if rejects:
        with pytest.raises(ValueError, match="closed order"):
            _next_trade_status(current, incoming)
    else:
        assert _next_trade_status(current, incoming) == expected


@pytest.mark.asyncio
async def test_payment_job_is_claimed_once_and_failed_delivery_is_replayable(
    isolated_migrated_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in settings_environment(DATABASE_URL=isolated_migrated_url).items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    from en_learning.worker.tasks import replay_due_jobs, run_background_job

    settings = payment_settings(
        isolated_migrated_url,
        worker_job_max_attempts=2,
        worker_retry_delay_seconds=1,
    )
    socket_publisher = FakeSocketPublisher()
    resources = PaymentResources(settings, socket_publisher=socket_publisher)
    user, course = await seed_user_course(resources.database)
    payment = PaymentRecord(
        id=uuid.uuid4().hex,
        user_id=user.id,
        course_id=course.id,
        out_trade_no=f"CJW-{uuid.uuid4().hex[:12]}",
        amount=course.price,
        subject=course.name,
        body=course.description or "",
        trade_status=TradeStatus.TRADE_SUCCESS,
    )
    course_record = CourseRecord(
        id=uuid.uuid4().hex,
        user_id=user.id,
        course_id=course.id,
        is_purchased=True,
        payment_record_id=payment.id,
    )
    job = BackgroundJob(
        id=uuid.uuid4().hex,
        task_key=f"payment:{payment.id}:success",
        kind="PAYMENT_SUCCESS",
        user_id=user.id,
        payment_record_id=payment.id,
        payload={"courseId": course.id},
        max_attempts=2,
    )
    async with resources.database.session() as session:
        session.add(payment)
        await session.flush()
        session.add_all([course_record, job])
        await session.commit()

    results = await asyncio.gather(
        run_background_job(job.id, resources, settings),
        run_background_job(job.id, resources, settings),
    )
    assert sorted(results) == [False, True]
    assert socket_publisher.users == [user.id]

    failing_socket = FakeSocketPublisher(fail=True)
    resources.socket_publisher = failing_socket
    failed_job = BackgroundJob(
        id=uuid.uuid4().hex,
        task_key=f"payment:{payment.id}:retry",
        kind="PAYMENT_SUCCESS",
        user_id=user.id,
        payment_record_id=payment.id,
        payload={"courseId": course.id},
        max_attempts=2,
    )
    async with resources.database.session() as session:
        session.add(failed_job)
        await session.commit()
    for attempt in range(2):
        if attempt:
            async with resources.database.session() as session:
                stored = await session.get(BackgroundJob, failed_job.id)
                assert stored is not None
                stored.scheduled_for = utc_now_naive()
                await session.commit()
        with pytest.raises(ConnectionError):
            await run_background_job(failed_job.id, resources, settings)
    async with resources.database.session() as session:
        stored = await session.get(BackgroundJob, failed_job.id)
        assert stored is not None
        assert stored.status == "FAILED"
        assert stored.attempts == 2
        assert stored.last_error_code == "ConnectionError"

    resources.socket_publisher = socket_publisher
    enqueued: list[str] = []

    async def enqueue(job_id: str) -> object:
        enqueued.append(job_id)
        return object()

    assert await replay_due_jobs(resources, enqueue, include_failed=True) == 1
    assert enqueued == [failed_job.id]
    assert await run_background_job(failed_job.id, resources, settings)
    assert socket_publisher.users == [user.id, user.id]
    await resources.close()


@pytest.mark.asyncio
async def test_digest_schedule_lock_restart_recovery_and_email_idempotency(
    isolated_migrated_url: str,
    redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in settings_environment(
        DATABASE_URL=isolated_migrated_url,
        REDIS_URL=redis_url,
    ).items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    from en_learning.worker.tasks import _day_bounds, run_background_job, scan_digest_jobs

    settings = payment_settings(isolated_migrated_url, redis_url=redis_url)
    redis = Redis.from_url(redis_url, decode_responses=True)
    email_sender = FakeEmailSender()
    resources = PaymentResources(settings, redis=redis, email_sender=email_sender)
    user, _ = await seed_user_course(resources.database)
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    word = WordBook(id=uuid.uuid4().hex, word="resilient")
    record = WordBookRecord(
        id=uuid.uuid4().hex,
        user_id=user.id,
        word_id=word.id,
        is_master=True,
        created_at=now.replace(tzinfo=None),
    )
    async with resources.database.session() as session:
        stored_user = await session.get(User, user.id)
        assert stored_user is not None
        stored_user.is_timing_task = True
        stored_user.timing_task_time = "00:00:00"
        stored_user.word_number = 1
        session.add_all([word, record])
        await session.commit()

    enqueued: list[str] = []

    async def enqueue(job_id: str) -> object:
        enqueued.append(job_id)
        return object()

    timezone = ZoneInfo(settings.digest_timezone)
    start, end = _day_bounds(now.astimezone(timezone).date(), timezone)
    async with resources.database.session() as session:
        stored_record = await session.get(WordBookRecord, record.id)
        assert stored_record is not None
        assert start <= stored_record.created_at < end
        scheduled_user = await session.scalar(
            select(User.id).where(
                User.id == user.id,
                User.is_timing_task.is_(True),
                User.email.is_not(None),
                User.timing_task_time <= "20:00:00",
            )
        )
        assert scheduled_user == user.id
    assert await scan_digest_jobs(resources, settings, enqueue, now=now) == 1
    assert await scan_digest_jobs(resources, settings, enqueue, now=now) == 0
    assert len(enqueued) == 1

    restarted = PaymentResources(
        settings,
        redis=Redis.from_url(redis_url, decode_responses=True),
        email_sender=email_sender,
    )
    assert await run_background_job(enqueued[0], restarted, settings)
    assert not await run_background_job(enqueued[0], restarted, settings)
    assert len(email_sender.messages) == 1
    message = email_sender.messages[0]
    assert message["to"] == user.email
    assert "resilient" in message["html"]

    failed_digest = BackgroundJob(
        id=uuid.uuid4().hex,
        task_key=f"email-digest-retry:{user.id}",
        kind="EMAIL_DIGEST",
        user_id=user.id,
        payload={"date": "2026-08-21"},
        max_attempts=2,
    )
    async with resources.database.session() as session:
        session.add(failed_digest)
        await session.commit()
    restarted.email_sender = FakeEmailSender(fail=True)
    with pytest.raises(ConnectionError):
        await run_background_job(failed_digest.id, restarted, settings)
    async with resources.database.session() as session:
        stored = await session.get(BackgroundJob, failed_digest.id)
        assert stored is not None
        assert stored.status == "PENDING"
        assert stored.attempts == 1
        stored.scheduled_for = utc_now_naive()
        await session.commit()
    restarted.email_sender = email_sender
    assert await run_background_job(failed_digest.id, restarted, settings)
    assert len(email_sender.messages) == 2
    await resources.close()
    await restarted.close()
