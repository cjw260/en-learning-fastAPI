import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

import httpx
from redis.asyncio import Redis

from en_learning.common.config import Settings
from en_learning.db.session import Database
from en_learning.realtime.socketio import SocketPublisher
from en_learning.services.email import EmailSender
from en_learning.services.object_storage import ObjectStorage

ReadinessCheck = Callable[[], Awaitable[None]]
logger = logging.getLogger("en_learning.resources")


class ManagedResources(Protocol):
    async def close(self) -> None: ...

    def readiness_checks(self) -> dict[str, ReadinessCheck]: ...


class AIResources(Protocol):
    database: Database
    redis: Redis
    http: httpx.AsyncClient
    llm_http: httpx.AsyncClient


class CoreResources(Protocol):
    database: Database
    redis: Redis
    object_storage: ObjectStorage


class ResourceSet:
    """Process-level clients, created in lifespan and closed in reverse order."""

    def __init__(self, settings: Settings) -> None:
        timeout = httpx.Timeout(settings.http_timeout_seconds)
        llm_timeout = httpx.Timeout(
            connect=settings.llm_connect_timeout_seconds,
            read=None,
            write=settings.http_timeout_seconds,
            pool=settings.llm_connect_timeout_seconds,
        )
        self.database = Database(settings)
        self.redis = Redis.from_url(str(settings.redis_url), decode_responses=True)
        self.object_storage = ObjectStorage(settings)
        self.socket_publisher = SocketPublisher(settings)
        self.email_sender = EmailSender(settings)
        self.http = httpx.AsyncClient(timeout=timeout, follow_redirects=False)
        self.llm_http = httpx.AsyncClient(
            base_url=str(settings.deepseek_base_url),
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key.get_secret_value()}",
            },
            timeout=llm_timeout,
            follow_redirects=False,
        )

    async def _check_redis(self) -> None:
        await self.redis.ping()

    def readiness_checks(self) -> dict[str, ReadinessCheck]:
        return {
            "postgresql": self.database.check,
            "redis": self._check_redis,
            "minio": self.object_storage.check,
        }

    async def close(self) -> None:
        results = await asyncio.gather(
            self.llm_http.aclose(),
            self.http.aclose(),
            self.object_storage.close(),
            self.socket_publisher.close(),
            self.redis.aclose(),
            self.database.close(),
            return_exceptions=True,
        )
        if failures := sum(isinstance(result, BaseException) for result in results):
            logger.warning("resources.close_failed", extra={"failureCount": failures})
