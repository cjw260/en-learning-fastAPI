import asyncio

from minio import Minio
from urllib3 import PoolManager, Timeout

from en_learning.common.config import Settings


class ObjectStorage:
    """Own a MinIO client and its HTTP pool without connecting during construction."""

    def __init__(self, settings: Settings) -> None:
        self._pool = PoolManager(
            timeout=Timeout(
                connect=settings.http_timeout_seconds,
                read=settings.http_timeout_seconds,
            )
        )
        self.client = Minio(
            settings.minio_host,
            access_key=settings.minio_access_key.get_secret_value(),
            secret_key=settings.minio_secret_key.get_secret_value(),
            secure=settings.minio_use_ssl,
            http_client=self._pool,
        )

    async def check(self) -> None:
        await asyncio.to_thread(self.client.list_buckets)

    async def close(self) -> None:
        await asyncio.to_thread(self._pool.clear)
