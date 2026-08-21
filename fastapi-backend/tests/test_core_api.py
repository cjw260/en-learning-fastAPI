from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import func, select

from en_learning.api.router import router
from en_learning.common.application import ServiceKind, create_http_application
from en_learning.common.config import Settings
from en_learning.db.models import (
    Course,
    CourseRecord,
    PaymentRecord,
    TrackEvent,
    TradeStatus,
    User,
    Visitor,
    WordBook,
    WordBookRecord,
)
from en_learning.db.session import Database
from en_learning.services.object_storage import ObjectStorage, StoredObject
from tests.conftest import settings_values

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_migrated_url(isolated_postgres_url: str) -> str:
    alembic = Path(sys.executable).with_name("alembic")
    subprocess.run(
        [str(alembic), "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "DATABASE_URL": isolated_postgres_url},
        check=True,
        capture_output=True,
        text=True,
    )
    return isolated_postgres_url


class MemoryRedis:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.counts: dict[str, int] = {}

    async def eval(
        self,
        _script: str,
        _num_keys: int,
        key: str,
        _window: int,
    ) -> int:
        if not self.available:
            raise RedisError("unavailable")
        current = self.counts.get(key, 0) + 1
        self.counts[key] = current
        return current


class FakeStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.puts: list[dict[str, Any]] = []
        self.removed: list[str] = []

    async def put_avatar(self, **values: Any) -> StoredObject:
        self.puts.append(values)
        if self.fail:
            raise RuntimeError("storage unavailable")
        object_name = f"users/{values['user_id']}/{values['object_id']}.{values['extension']}"
        return StoredObject(
            object_name=object_name,
            preview_url=f"http://minio.test/avatar/{object_name}",
            database_url=f"/avatar/{object_name}",
        )

    async def remove(self, object_name: str) -> None:
        self.removed.append(object_name)


class CoreResources:
    def __init__(
        self,
        settings: Settings,
        *,
        redis: MemoryRedis | Redis | None = None,
        storage: FakeStorage | ObjectStorage | None = None,
    ) -> None:
        self.database = Database(settings)
        self.redis = redis or MemoryRedis()
        self.object_storage = storage or FakeStorage()

    def readiness_checks(self) -> dict[str, Callable[[], Awaitable[None]]]:
        return {}

    async def close(self) -> None:
        if isinstance(self.redis, Redis):
            await self.redis.aclose()
        if isinstance(self.object_storage, ObjectStorage):
            await self.object_storage.close()
        await self.database.close()


def create_core_app(settings: Settings, resources: CoreResources) -> FastAPI:
    app = create_http_application(
        ServiceKind.CORE,
        settings=settings,
        resource_factory=lambda _: resources,
    )
    app.include_router(router)
    return app


@asynccontextmanager
async def core_client(settings: Settings, resources: CoreResources) -> AsyncIterator[AsyncClient]:
    app = create_core_app(settings, resources)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            yield client


def phone() -> str:
    return f"13{uuid.uuid4().int % 1_000_000_000:09d}"


async def register_user(
    client: AsyncClient, *, password: str = "md5-compatible-value"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/user/register",
        json={
            "name": "Core Tester",
            "phone": phone(),
            "email": f"{uuid.uuid4().hex}@example.test",
            "password": password,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def authorization(user: dict[str, Any], token: str = "accessToken") -> dict[str, str]:
    return {"Authorization": f"Bearer {user['token'][token]}"}


@pytest.mark.asyncio
async def test_user_password_jwt_rotation_and_profile_contract(
    isolated_migrated_url: str,
) -> None:
    settings = Settings(_env_file=None, **settings_values(database_url=isolated_migrated_url))
    resources = CoreResources(settings)
    async with core_client(settings, resources) as client:
        user = await register_user(client)
        other = await register_user(client)
        assert "password" not in user
        assert user["createdAt"].endswith("Z")
        assert user["email"].endswith("@example.test")

        duplicate = await client.post(
            "/api/v1/user/register",
            json={
                "name": "Duplicate",
                "phone": user["phone"],
                "password": "another-value",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["success"] is False
        assert "data" not in duplicate.json()

        refresh_token = user["token"]["refreshToken"]
        refreshed = await client.post(
            "/api/v1/user/refresh-token",
            json={"refreshToken": refresh_token},
        )
        replay = await client.post(
            "/api/v1/user/refresh-token",
            json={"refreshToken": refresh_token},
        )
        wrong_type = await client.post(
            "/api/v1/user/refresh-token",
            json={"refreshToken": user["token"]["accessToken"]},
        )
        assert refreshed.status_code == 200
        assert replay.status_code == 401
        assert wrong_type.status_code == 401

        new_tokens = refreshed.json()["data"]
        conflict = await client.post(
            "/api/v1/user/update-user",
            headers={"Authorization": f"Bearer {new_tokens['accessToken']}"},
            json={"name": "Updated Tester", "email": other["email"]},
        )
        update = await client.post(
            "/api/v1/user/update-user",
            headers={"Authorization": f"Bearer {new_tokens['accessToken']}"},
            json={
                "name": "Updated Tester",
                "email": None,
                "address": None,
                "avatar": None,
                "bio": "updated",
                "isTimingTask": False,
                "timingTaskTime": "00:00:00",
                "id": other["id"],
                "phone": other["phone"],
                "wordNumber": 999,
                "token": other["token"],
            },
        )
        refresh_as_access = await client.get(
            "/api/v1/course/my",
            headers={"Authorization": f"Bearer {new_tokens['refreshToken']}"},
        )
        signed_content, signature = new_tokens["accessToken"].rsplit(".", 1)
        tampered = f"{signed_content}.{'A' if signature[0] != 'A' else 'B'}{signature[1:]}"
        forged = await client.get(
            "/api/v1/course/my",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert conflict.status_code == 409
        assert update.status_code == 200
        assert update.json()["data"]["name"] == "Updated Tester"
        assert refresh_as_access.status_code == 401
        assert forged.status_code == 401

        rotations = await asyncio.gather(
            *(
                client.post(
                    "/api/v1/user/refresh-token",
                    json={"refreshToken": new_tokens["refreshToken"]},
                )
                for _ in range(2)
            )
        )
        assert sorted(response.status_code for response in rotations) == [200, 401]

        async with resources.database.session() as session:
            stored = await session.scalar(select(User).where(User.id == user["id"]))
            assert stored is not None
            assert stored.password.startswith("scrypt$1$")
            assert stored.password != "md5-compatible-value"
            assert stored.refresh_token_version == 3
            assert stored.phone == user["phone"]
            assert stored.word_number == 0


@pytest.mark.asyncio
async def test_legacy_password_is_upgraded_on_first_successful_login(
    isolated_migrated_url: str,
) -> None:
    settings = Settings(_env_file=None, **settings_values(database_url=isolated_migrated_url))
    resources = CoreResources(settings)
    legacy_phone = phone()
    async with resources.database.session() as session, session.begin():
        session.add(
            User(
                id=uuid.uuid4().hex,
                name="Legacy User",
                phone=legacy_phone,
                email=None,
                password="legacy-md5",
            )
        )

    async with core_client(settings, resources) as client:
        bad = await client.post(
            "/api/v1/user/login",
            json={"phone": legacy_phone, "password": "wrong"},
        )
        login = await client.post(
            "/api/v1/user/login",
            json={"phone": legacy_phone, "password": "legacy-md5"},
        )
        assert bad.status_code == 401
        assert login.status_code == 200
        async with resources.database.session() as session:
            stored = await session.scalar(select(User).where(User.phone == legacy_phone))
            assert stored is not None
            assert stored.password.startswith("scrypt$1$")


@pytest.mark.asyncio
async def test_avatar_requires_identity_and_isolates_validated_objects(
    isolated_migrated_url: str,
) -> None:
    settings = Settings(
        _env_file=None,
        **settings_values(database_url=isolated_migrated_url, avatar_max_bytes=1024),
    )
    storage = FakeStorage()
    resources = CoreResources(settings, storage=storage)
    png = b"\x89PNG\r\n\x1a\n" + b"safe-image"
    async with core_client(settings, resources) as client:
        user = await register_user(client)
        unauthorized = await client.post(
            "/api/v1/user/upload-avatar",
            files={"file": ("avatar.png", png, "image/png")},
        )
        dangerous = await client.post(
            "/api/v1/user/upload-avatar",
            headers=authorization(user),
            files={"file": ("avatar.php", png, "image/png")},
        )
        mismatch = await client.post(
            "/api/v1/user/upload-avatar",
            headers=authorization(user),
            files={"file": ("avatar.png", b"not-png", "image/png")},
        )
        valid = await client.post(
            "/api/v1/user/upload-avatar",
            headers=authorization(user),
            files={"file": ("../../avatar.png", png, "image/png")},
        )
        second = await client.post(
            "/api/v1/user/upload-avatar",
            headers=authorization(user),
            files={"file": ("avatar.png", png, "image/png")},
        )
        oversized = await client.post(
            "/api/v1/user/upload-avatar",
            headers=authorization(user),
            files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\n" + b"x" * 1024, "image/png")},
        )

        assert unauthorized.status_code == 401
        assert dangerous.status_code == 422
        assert mismatch.status_code == 422
        assert valid.status_code == 200
        assert second.status_code == 200
        assert oversized.status_code == 413
        first_url = valid.json()["data"]["databaseUrl"]
        second_url = second.json()["data"]["databaseUrl"]
        assert first_url.startswith(f"/avatar/users/{user['id']}/")
        assert ".." not in first_url
        assert ".php" not in first_url
        assert first_url != second_url


@pytest.mark.asyncio
async def test_avatar_storage_failure_is_controlled_and_cleaned(
    isolated_migrated_url: str,
) -> None:
    settings = Settings(_env_file=None, **settings_values(database_url=isolated_migrated_url))
    storage = FakeStorage(fail=True)
    resources = CoreResources(settings, storage=storage)
    async with core_client(settings, resources) as client:
        user = await register_user(client)
        response = await client.post(
            "/api/v1/user/upload-avatar",
            headers=authorization(user),
            files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
        )
        assert response.status_code == 503
        assert response.json()["message"] == "头像存储服务暂时不可用"
        assert len(storage.removed) == 1


@pytest.mark.asyncio
async def test_avatar_upload_uses_real_minio_with_safe_metadata(
    isolated_migrated_url: str,
    minio_values: dict[str, Any],
) -> None:
    settings = Settings(
        _env_file=None,
        **settings_values(database_url=isolated_migrated_url, **minio_values),
    )
    storage = ObjectStorage(settings)
    await asyncio.to_thread(storage.client.make_bucket, settings.minio_bucket)
    resources = CoreResources(settings, storage=storage)
    content = b"\x89PNG\r\n\x1a\nreal-minio-image"
    async with core_client(settings, resources) as client:
        user = await register_user(client)
        response = await client.post(
            "/api/v1/user/upload-avatar",
            headers=authorization(user),
            files={"file": ("avatar.png", content, "image/png")},
        )
        assert response.status_code == 200
        object_name = response.json()["data"]["databaseUrl"].removeprefix("/avatar/")
        stat = await asyncio.to_thread(
            storage.client.stat_object,
            settings.minio_bucket,
            object_name,
        )
        assert object_name.startswith(f"users/{user['id']}/")
        assert stat.content_type == "image/png"
        assert stat.size == len(content)


@pytest.mark.asyncio
async def test_course_wordbook_and_learning_transactions_are_compatible_and_idempotent(
    isolated_migrated_url: str,
) -> None:
    settings = Settings(_env_file=None, **settings_values(database_url=isolated_migrated_url))
    resources = CoreResources(settings)
    async with core_client(settings, resources) as client:
        user = await register_user(client)
        course_id = uuid.uuid4().hex
        other_course_id = uuid.uuid4().hex
        word_ids = [uuid.uuid4().hex for _ in range(4)]
        async with resources.database.session() as session, session.begin():
            session.add_all(
                [
                    Course(
                        id=course_id,
                        name="高考英语",
                        value="gk",
                        description=None,
                        teacher="Teacher",
                        url="/course/gk.png",
                        price=Decimal("12.3"),
                    ),
                    Course(
                        id=other_course_id,
                        name="中考英语",
                        value="zk",
                        description="Other",
                        teacher="Teacher",
                        url="/course/zk.png",
                        price=Decimal("8"),
                    ),
                    WordBook(id=word_ids[0], word="alpha", frq="1", frq_rank=1, gk=True),
                    WordBook(id=word_ids[1], word="beta", frq="2", frq_rank=2, gk=True),
                    WordBook(id=word_ids[2], word="omega", frq=None, frq_rank=None, gk=True),
                    WordBook(id=word_ids[3], word="zeta", frq="0", frq_rank=None, zk=True),
                ]
            )
            payment = PaymentRecord(
                id=uuid.uuid4().hex,
                user_id=user["id"],
                out_trade_no=uuid.uuid4().hex,
                amount=Decimal("12.3"),
                subject="course",
                body="course",
                trade_status=TradeStatus.TRADE_SUCCESS,
            )
            session.add(payment)
            session.add(
                CourseRecord(
                    id=uuid.uuid4().hex,
                    user_id=user["id"],
                    course_id=course_id,
                    is_purchased=True,
                    payment_record_id=payment.id,
                )
            )

        courses = await client.get("/api/v1/course/list")
        mine = await client.get("/api/v1/course/my", headers=authorization(user))
        words = await client.get("/api/v1/word-book?page=1&pageSize=10&gk=true")
        empty_search = await client.get("/api/v1/word-book?page=1&pageSize=10&word=&gk=true")
        second_page = await client.get("/api/v1/word-book?page=2&pageSize=1&gk=true")
        learn = await client.get(f"/api/v1/learn/word/{course_id}", headers=authorization(user))
        forbidden = await client.get(
            f"/api/v1/learn/word/{other_course_id}", headers=authorization(user)
        )

        assert courses.status_code == 200
        course_result = next(item for item in courses.json()["data"] if item["id"] == course_id)
        assert course_result["price"] == "12.30"
        assert course_result["description"] is None
        assert mine.json()["data"][0]["id"] == course_id
        assert [item["word"] for item in words.json()["data"]["list"]] == [
            "alpha",
            "beta",
            "omega",
        ]
        assert empty_search.status_code == 200
        assert empty_search.json()["data"]["total"] == 3
        assert second_page.json()["data"]["list"][0]["word"] == "beta"
        assert [item["word"] for item in learn.json()["data"]] == [
            "alpha",
            "beta",
            "omega",
        ]
        assert forbidden.status_code == 403

        first_master = await client.post(
            "/api/v1/learn/word/master",
            headers=authorization(user),
            json={"wordIds": [word_ids[0], word_ids[0]]},
        )
        repeated = await client.post(
            "/api/v1/learn/word/master",
            headers=authorization(user),
            json={"wordIds": [word_ids[0]]},
        )
        concurrent = await asyncio.gather(
            *(
                client.post(
                    "/api/v1/learn/word/master",
                    headers=authorization(user),
                    json={"wordIds": [word_ids[1]]},
                )
                for _ in range(2)
            )
        )
        unauthorized_word = await client.post(
            "/api/v1/learn/word/master",
            headers=authorization(user),
            json={"wordIds": [word_ids[3]]},
        )
        assert first_master.json()["data"] == {"wordNumber": 1}
        assert repeated.json()["data"] == {"wordNumber": 1}
        assert all(response.status_code == 200 for response in concurrent)
        assert unauthorized_word.status_code == 403

        async with resources.database.session() as session:
            record_count = await session.scalar(
                select(func.count())
                .select_from(WordBookRecord)
                .where(WordBookRecord.user_id == user["id"])
            )
            stored_user = await session.scalar(select(User).where(User.id == user["id"]))
            assert record_count == 2
            assert stored_user is not None
            assert stored_user.word_number == 2


@pytest.mark.asyncio
async def test_tracker_boundaries_privacy_rate_limit_and_failures(
    isolated_migrated_url: str,
) -> None:
    settings = Settings(
        _env_file=None,
        **settings_values(
            database_url=isolated_migrated_url,
            tracker_max_body_bytes=1024,
            tracker_rate_limit=100,
        ),
    )
    resources = CoreResources(settings)
    async with core_client(settings, resources) as client:
        user = await register_user(client)
        other = await register_user(client)
        anonymous_id = uuid.uuid4().hex
        uv = await client.post(
            "/api/v1/tracker/uv",
            json={
                "anonymousId": anonymous_id,
                "browser": "Chrome",
                "os": "macOS",
                "device": "desktop",
            },
        )
        visitor_id = uv.json()["data"]
        spoof = await client.post(
            "/api/v1/tracker/uv",
            json={"anonymousId": uuid.uuid4().hex, "userId": user["id"]},
        )
        unauthenticated_update = await client.post(
            "/api/v1/tracker/update-uv",
            json={"visitorId": visitor_id, "userId": user["id"]},
        )
        mismatch = await client.post(
            "/api/v1/tracker/update-uv",
            headers=authorization(user),
            json={"visitorId": visitor_id, "userId": "someone-else"},
        )
        bound = await client.post(
            "/api/v1/tracker/update-uv",
            headers=authorization(user),
            json={"visitorId": visitor_id, "userId": user["id"]},
        )
        rebind = await client.post(
            "/api/v1/tracker/uv",
            headers=authorization(other),
            json={"anonymousId": anonymous_id, "userId": other["id"]},
        )
        event = await client.post(
            "/api/v1/tracker/event",
            json={
                "visitorId": visitor_id,
                "event": "click",
                "payload": {
                    "password": "do-not-store",
                    "text": "Bearer abc.def.ghi person@example.test 13800138000",
                },
                "url": "https://example.test/page?token=secret&view=ok",
            },
        )
        performance = await client.post(
            "/api/v1/tracker/performance",
            json={
                "visitorId": visitor_id,
                "fp": 1,
                "fcp": 2,
                "lcp": 3,
                "inp": 4,
                "cls": 0.1,
            },
        )
        page_view = await client.post(
            "/api/v1/tracker/pv",
            json={
                "visitorId": visitor_id,
                "url": "https://example.test",
                "referrer": "",
                "path": "/home",
            },
        )
        error = await client.post(
            "/api/v1/tracker/error",
            json={
                "visitorId": visitor_id,
                "error": "promise",
                "message": "Bearer abc.def.ghi",
                "stack": "person@example.test 13800138000",
                "url": "https://example.test/error?token=secret",
            },
        )
        unknown = await client.post(
            "/api/v1/tracker/pv",
            json={
                "visitorId": "missing",
                "url": "https://example.test",
                "referrer": "",
                "path": "/",
            },
        )
        invalid = await client.post(
            "/api/v1/tracker/performance",
            json={
                "visitorId": visitor_id,
                "fp": -1,
                "fcp": 0,
                "lcp": 0,
                "inp": 0,
                "cls": 0,
            },
        )
        oversized = await client.post(
            "/api/v1/tracker/event",
            content=json.dumps(
                {
                    "visitorId": visitor_id,
                    "event": "click",
                    "payload": {"text": "x" * 2000},
                    "url": "https://example.test",
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        async def chunked_body() -> AsyncIterator[bytes]:
            yield (
                b'{"visitorId":"' + visitor_id.encode() + b'","event":"click","payload":{"text":"'
            )
            yield b"x" * 2000 + b'"}}'

        chunked = await client.post(
            "/api/v1/tracker/event",
            content=chunked_body(),
            headers={"Content-Type": "application/json"},
        )

        assert uv.status_code == 200
        assert spoof.status_code == 401
        assert unauthenticated_update.status_code == 401
        assert mismatch.status_code == 403
        assert bound.status_code == 200
        assert rebind.status_code == 403
        assert event.status_code == 200
        assert performance.status_code == 200
        assert page_view.status_code == 200
        assert error.status_code == 200
        assert unknown.status_code == 404
        assert invalid.status_code == 422
        assert oversized.status_code == 413
        assert chunked.status_code == 413

        async with resources.database.session() as session:
            visitor = await session.scalar(select(Visitor).where(Visitor.id == visitor_id))
            stored_event = await session.scalar(
                select(TrackEvent).where(TrackEvent.visitor_id == visitor_id)
            )
            assert visitor is not None
            assert visitor.user_id == user["id"]
            assert stored_event is not None
            serialized = json.dumps(stored_event.payload)
            assert "do-not-store" not in serialized
            assert "abc.def.ghi" not in serialized
            assert "person@example.test" not in serialized
            assert "13800138000" not in serialized
            assert stored_event.url == ("https://example.test/page?token=%5BREDACTED%5D&view=ok")

    limited_settings = Settings(
        _env_file=None,
        **settings_values(
            database_url=isolated_migrated_url,
            tracker_rate_limit=2,
        ),
    )
    limited_resources = CoreResources(limited_settings)
    async with core_client(limited_settings, limited_resources) as client:
        body = {"anonymousId": uuid.uuid4().hex}
        assert (await client.post("/api/v1/tracker/uv", json=body)).status_code == 200
        body["anonymousId"] = uuid.uuid4().hex
        assert (await client.post("/api/v1/tracker/uv", json=body)).status_code == 200
        body["anonymousId"] = uuid.uuid4().hex
        limited = await client.post("/api/v1/tracker/uv", json=body)
        assert limited.status_code == 429

    unavailable_resources = CoreResources(
        limited_settings,
        redis=MemoryRedis(available=False),
    )
    async with core_client(limited_settings, unavailable_resources) as client:
        unavailable = await client.post(
            "/api/v1/tracker/uv",
            json={"anonymousId": uuid.uuid4().hex},
        )
        assert unavailable.status_code == 503
        assert "unavailable" not in unavailable.text


@pytest.mark.asyncio
async def test_tracker_real_redis_rate_limit(
    isolated_migrated_url: str,
    redis_url: str,
) -> None:
    settings = Settings(
        _env_file=None,
        **settings_values(
            database_url=isolated_migrated_url,
            redis_url=redis_url,
            tracker_rate_limit=2,
        ),
    )
    redis = Redis.from_url(redis_url, decode_responses=True)
    await redis.flushdb()
    resources = CoreResources(settings, redis=redis)
    async with core_client(settings, resources) as client:
        statuses = []
        for _ in range(3):
            response = await client.post(
                "/api/v1/tracker/uv",
                json={"anonymousId": uuid.uuid4().hex},
            )
            statuses.append(response.status_code)
    assert statuses == [200, 200, 429]


@pytest.mark.asyncio
async def test_database_failure_is_a_safe_service_error() -> None:
    settings = Settings(_env_file=None, **settings_values())
    resources = CoreResources(settings)
    async with core_client(settings, resources) as client:
        response = await client.get("/api/v1/course/list")
    assert response.status_code == 503
    assert response.json()["message"] == "数据库服务暂时不可用"
    assert "127.0.0.1" not in response.text
