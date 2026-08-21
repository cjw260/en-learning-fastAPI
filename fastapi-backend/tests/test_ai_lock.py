import uuid

import pytest
from redis.asyncio import Redis

from en_learning.ai.locks import ConversationLock
from en_learning.common.errors import AppError
from en_learning.schemas.chat import ChatRole


@pytest.mark.asyncio
async def test_real_redis_lock_coordinates_clients_and_releases(redis_url: str) -> None:
    first_redis = Redis.from_url(redis_url, decode_responses=True)
    second_redis = Redis.from_url(redis_url, decode_responses=True)
    user_id = uuid.uuid4().hex
    first = ConversationLock(first_redis, ttl_seconds=30)
    second = ConversationLock(second_redis, ttl_seconds=30)
    try:
        lease = await first.acquire(user_id, ChatRole.NORMAL)
        with pytest.raises(AppError) as conflict:
            await second.acquire(user_id, ChatRole.NORMAL)
        assert conflict.value.status_code == 409

        await first.release(lease)
        second_lease = await second.acquire(user_id, ChatRole.NORMAL)
        await second.release(second_lease)
    finally:
        await first_redis.aclose()
        await second_redis.aclose()
