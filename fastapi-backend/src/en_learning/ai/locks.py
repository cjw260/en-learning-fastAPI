from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from en_learning.common.errors import AppError
from en_learning.schemas.chat import ChatRole

logger = logging.getLogger("en_learning.ai.locks")
RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


@dataclass(frozen=True, slots=True)
class ConversationLease:
    key: str
    token: str


class ConversationLock:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def acquire(self, user_id: str, role: ChatRole) -> ConversationLease:
        identity = hashlib.sha256(f"{user_id}\0{role.value}".encode()).hexdigest()
        key = f"en-learning:ai:conversation:{identity}"
        token = secrets.token_urlsafe(24)
        try:
            acquired = await self._redis.set(key, token, ex=self._ttl_seconds, nx=True)
        except RedisError as exception:
            logger.warning("ai.redis_unavailable", extra={"operation": "lock-acquire"})
            raise AppError("AI 会话服务暂时不可用", status_code=503) from exception
        if not acquired:
            raise AppError("当前对话正在生成中", status_code=409)
        return ConversationLease(key=key, token=token)

    async def release(self, lease: ConversationLease) -> None:
        try:
            await self._redis.eval(RELEASE_SCRIPT, 1, lease.key, lease.token)
        except RedisError:
            logger.warning("ai.redis_unavailable", extra={"operation": "lock-release"})
