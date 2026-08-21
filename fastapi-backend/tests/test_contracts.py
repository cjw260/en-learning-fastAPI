import asyncio
import io
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import pytest
from fastapi import Query
from httpx import ASGITransport, AsyncClient

from en_learning.ai.router import router as ai_router
from en_learning.api.router import router as core_router
from en_learning.common.application import ServiceKind, create_http_application
from en_learning.common.config import Settings
from en_learning.common.logging import JsonFormatter


class FakeResources:
    def __init__(self, checks: dict[str, bool]) -> None:
        self.checks = checks
        self.closed = False

    def readiness_checks(self) -> dict[str, Callable[[], Awaitable[None]]]:
        result: dict[str, Callable[[], Awaitable[None]]] = {}
        for name, available in self.checks.items():

            async def check(is_available: bool = available) -> None:
                if not is_available:
                    raise ConnectionError

            result[name] = check
        return result

    async def close(self) -> None:
        self.closed = True


@asynccontextmanager
async def request_client(
    settings: Settings,
    resources: FakeResources,
) -> AsyncIterator[tuple[object, AsyncClient]]:
    app = create_http_application(
        ServiceKind.CORE,
        settings=settings,
        resource_factory=lambda _: resources,
    )
    app.include_router(core_router)

    @app.get("/_test/validate")
    async def validation_probe(limit: int = Query(gt=0)) -> dict[str, int]:
        return {"limit": limit}

    @app.get("/_test/error")
    async def error_probe() -> None:
        raise RuntimeError("do-not-log-this-sensitive-value")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield app, client


@pytest.mark.asyncio
async def test_root_and_live_contract(settings: Settings) -> None:
    resources = FakeResources({"postgresql": True, "redis": True, "minio": True})
    async with request_client(settings, resources) as (_, client):
        root = await client.get("/api/v1/")
        assert root.status_code == 200
        assert root.json().keys() == {
            "timestamp",
            "path",
            "message",
            "code",
            "success",
            "data",
        }
        assert root.json() | {"timestamp": "ignored"} == {
            "timestamp": "ignored",
            "path": "/api/v1/",
            "message": "请求成功",
            "code": 200,
            "success": True,
            "data": None,
        }

        live = await client.get("/health/live", headers={"X-Request-ID": "contract-123"})
        assert live.status_code == 200
        assert live.headers["X-Request-ID"] == "contract-123"
        assert live.json()["message"] == "请求成功"
        assert live.json()["code"] == 200
        assert live.json()["data"] == {"status": "alive", "service": "core-api"}
    assert resources.closed


@pytest.mark.asyncio
async def test_ready_reports_each_dependency(settings: Settings) -> None:
    resources = FakeResources({"postgresql": True, "redis": False, "minio": True})
    async with request_client(settings, resources) as (_, client):
        response = await client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["success"] is False
        assert response.json()["details"] == {
            "checks": {"postgresql": "up", "redis": "down", "minio": "up"}
        }
        assert "data" not in response.json()


@pytest.mark.asyncio
async def test_ready_success(settings: Settings) -> None:
    resources = FakeResources({"postgresql": True, "redis": True, "minio": True})
    async with request_client(settings, resources) as (_, client):
        response = await client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["message"] == "请求成功"
        assert response.json()["code"] == 200
        assert response.json()["data"] == {
            "status": "ready",
            "service": "core-api",
            "checks": {"postgresql": "up", "redis": "up", "minio": "up"},
        }


@pytest.mark.asyncio
async def test_ready_timeout_is_reported_without_internal_details(settings: Settings) -> None:
    class TimeoutResources(FakeResources):
        def readiness_checks(self) -> dict[str, Callable[[], Awaitable[None]]]:
            async def slow_check() -> None:
                await asyncio.sleep(1)

            return {"postgresql": slow_check}

    resources = TimeoutResources({})
    async with request_client(settings, resources) as (_, client):
        response = await client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["details"] == {"checks": {"postgresql": "down"}}


@pytest.mark.asyncio
async def test_validation_and_http_errors_use_failure_envelope(settings: Settings) -> None:
    resources = FakeResources({})
    async with request_client(settings, resources) as (_, client):
        validation = await client.get("/_test/validate?limit=0")
        assert validation.status_code == 422
        body = validation.json()
        assert body["path"] == "/_test/validate?limit=0"
        assert body["message"] == "Validation failed"
        assert body["code"] == 422
        assert body["success"] is False
        assert "data" not in body
        assert body["details"]["errors"][0].keys() == {"location", "message", "type"}

        missing = await client.get("/missing")
        assert missing.status_code == 404
        assert missing.json()["success"] is False
        assert missing.json()["message"] == "Not Found"
        assert "data" not in missing.json()


@pytest.mark.asyncio
async def test_unexpected_error_is_generic_and_log_safe(settings: Settings) -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    app_logger = logging.getLogger("en_learning")
    app_logger.addHandler(handler)
    try:
        async with request_client(settings, FakeResources({})) as (_, client):
            response = await client.get("/_test/error")
    finally:
        app_logger.removeHandler(handler)

    assert response.status_code == 500
    assert response.json()["message"] == "Internal server error"
    assert response.json()["code"] == 500
    assert response.json()["success"] is False
    assert "details" not in response.json()
    assert "do-not-log-this-sensitive-value" not in stream.getvalue()
    assert '"exceptionType":"RuntimeError"' in stream.getvalue()


def test_openapi_contains_only_p01_service_boundaries(settings: Settings) -> None:
    for service, router, root_path in (
        (ServiceKind.CORE, core_router, "/api/v1/"),
        (ServiceKind.AI, ai_router, "/ai/v1/"),
    ):
        app = create_http_application(
            service,
            settings=settings,
            resource_factory=lambda _: FakeResources({}),
        )
        app.include_router(router)
        assert set(app.openapi()["paths"]) == {root_path, "/health/live", "/health/ready"}


@pytest.mark.asyncio
async def test_unsafe_request_id_is_replaced(settings: Settings) -> None:
    resources = FakeResources({})
    async with request_client(settings, resources) as (_, client):
        response = await client.get("/health/live", headers={"X-Request-ID": "bad id value"})
        generated = response.headers["X-Request-ID"]
        assert generated != "bad id value"
        assert len(generated) == 32
