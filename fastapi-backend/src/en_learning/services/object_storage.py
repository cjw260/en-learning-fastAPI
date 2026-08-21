import asyncio
import io
from dataclasses import dataclass

from minio import Minio
from urllib3 import PoolManager, Timeout

from en_learning.common.config import Settings


@dataclass(frozen=True, slots=True)
class StoredObject:
    object_name: str
    preview_url: str
    database_url: str


class ObjectStorage:
    """Own a MinIO client and its HTTP pool without connecting during construction."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
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

    async def put_avatar(
        self,
        *,
        user_id: str,
        object_id: str,
        extension: str,
        content_type: str,
        content: bytes,
    ) -> StoredObject:
        bucket = self._settings.minio_bucket
        object_name = f"users/{user_id}/{object_id}.{extension}"
        exists = await asyncio.to_thread(self.client.bucket_exists, bucket)
        if not exists:
            raise RuntimeError("avatar bucket unavailable")
        await asyncio.to_thread(
            self.client.put_object,
            bucket,
            object_name,
            io.BytesIO(content),
            len(content),
            content_type=content_type,
        )
        scheme = "https" if self._settings.minio_use_ssl else "http"
        database_url = f"/{bucket}/{object_name}"
        return StoredObject(
            object_name=object_name,
            preview_url=f"{scheme}://{self._settings.minio_host}{database_url}",
            database_url=database_url,
        )

    async def remove(self, object_name: str) -> None:
        await asyncio.to_thread(
            self.client.remove_object,
            self._settings.minio_bucket,
            object_name,
        )

    async def close(self) -> None:
        await asyncio.to_thread(self._pool.clear)
