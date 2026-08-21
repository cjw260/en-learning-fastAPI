from typing import Any

from taskiq import SimpleRetryMiddleware, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import (
    ListRedisScheduleSource,
    RedisAsyncResultBackend,
    RedisStreamBroker,
)

from en_learning.common.config import get_settings
from en_learning.services.resources import ResourceSet

settings = get_settings()

result_backend: RedisAsyncResultBackend[Any] = RedisAsyncResultBackend(
    redis_url=str(settings.redis_url),
    result_ex_time=3600,
)
broker = (
    RedisStreamBroker(
        url=str(settings.redis_url),
        queue_name="en-learning",
        consumer_group_name="en-learning-workers",
        idle_timeout=60_000,
    )
    .with_result_backend(result_backend)
    .with_middlewares(SimpleRetryMiddleware(default_retry_count=3))
)

schedule_source = ListRedisScheduleSource(
    url=str(settings.redis_url),
    prefix="en-learning:schedules",
)
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[schedule_source, LabelScheduleSource(broker)],
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_worker_resources(state: TaskiqState) -> None:
    state.en_learning_resources = ResourceSet(settings)


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_worker_resources(state: TaskiqState) -> None:
    resources: ResourceSet | None = getattr(state, "en_learning_resources", None)
    if resources is not None:
        await resources.close()
