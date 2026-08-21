import importlib
import sys

import pytest
from taskiq import InMemoryBroker, SimpleRetryMiddleware, SmartRetryMiddleware
from taskiq_redis import RedisStreamBroker

from en_learning.common.config import get_settings
from tests.conftest import settings_environment


def test_worker_uses_acknowledged_redis_stream_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in settings_environment().items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    sys.modules.pop("en_learning.worker.broker", None)
    worker = importlib.import_module("en_learning.worker.broker")
    assert isinstance(worker.broker, RedisStreamBroker)
    assert worker.broker.queue_name == "en-learning"
    assert worker.broker.consumer_group_name == "en-learning-workers"
    assert any(isinstance(item, SmartRetryMiddleware) for item in worker.broker.middlewares)
    assert len(worker.scheduler.sources) == 2


@pytest.mark.asyncio
async def test_retry_middleware_retries_an_explicitly_labeled_failure() -> None:
    attempts = 0
    broker = InMemoryBroker(await_inplace=True).with_middlewares(
        SimpleRetryMiddleware(default_retry_count=3)
    )

    @broker.task(retry_on_error=True, max_retries=3)
    async def flaky_probe() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("expected probe failure")

    await broker.startup()
    try:
        await flaky_probe.kiq()
        await broker.wait_all()
    finally:
        await broker.shutdown()
    assert attempts == 2
