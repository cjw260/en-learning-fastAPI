import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from redis import Redis
from redis.exceptions import ResponseError

from en_learning.common.application import ServiceKind, create_http_application
from en_learning.common.config import Settings
from en_learning.services.resources import ResourceSet
from tests.conftest import PROJECT_ROOT, free_port, settings_environment


class TrackingResources:
    def __init__(self) -> None:
        self.closed = False

    def readiness_checks(self):
        return {}

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_lifespan_releases_resources(settings: Settings) -> None:
    resources = TrackingResources()
    app = create_http_application(
        ServiceKind.CORE,
        settings=settings,
        resource_factory=lambda _: resources,
    )
    async with app.router.lifespan_context(app):
        assert app.state.resources is resources
        assert not resources.closed
    assert resources.closed


@pytest.mark.asyncio
async def test_resource_construction_and_close_do_not_connect(settings: Settings) -> None:
    resources = ResourceSet(settings)
    assert not resources.http.is_closed
    assert not resources.llm_http.is_closed
    await resources.close()
    assert resources.http.is_closed
    assert resources.llm_http.is_closed


def test_imports_have_no_external_connection_side_effects() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import en_learning.api.main; "
                "import en_learning.ai.main; "
                "import en_learning.worker.broker"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=settings_environment(),
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert completed.returncode == 0, completed.stderr


def wait_for_http(port: int, process: subprocess.Popen[str], timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            pytest.fail(f"HTTP process exited early:\n{output}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/health/live", timeout=0.2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    pytest.fail("HTTP process did not become live")


def wait_for_worker_consumer_group(
    redis_url: str,
    process: subprocess.Popen[str],
    timeout: float = 10,
) -> None:
    client = Redis.from_url(redis_url, decode_responses=True)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                pytest.fail(f"Worker exited early:\n{output}")
            try:
                groups = client.xinfo_groups("en-learning")
            except ResponseError:
                groups = []
            if any(group["name"] == "en-learning-workers" for group in groups):
                return
            time.sleep(0.05)
    finally:
        client.close()
    pytest.fail("Worker did not create its Redis consumer group")


@pytest.mark.parametrize(
    "factory",
    ["en_learning.api.main:create_app", "en_learning.ai.main:create_app"],
)
def test_http_processes_start_and_stop_cleanly(factory: str) -> None:
    port = free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            factory,
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=PROJECT_ROOT,
        env=settings_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_http(port, process)
        process.terminate()
        output, _ = process.communicate(timeout=10)
    except BaseException:
        process.kill()
        process.wait(timeout=5)
        raise
    assert process.returncode == -signal.SIGTERM, output
    assert '"message":"service.stopped"' in output
    assert '"message":"resources.close_failed"' not in output


def test_worker_process_starts_and_stops_cleanly(redis_url: str) -> None:
    taskiq = Path(sys.executable).with_name("taskiq")
    env = settings_environment(REDIS_URL=redis_url)
    process = subprocess.Popen(
        [
            str(taskiq),
            "worker",
            "en_learning.worker.broker:broker",
            "--workers",
            "1",
            "--max-async-tasks",
            "2",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_worker_consumer_group(redis_url, process)
        process.terminate()
        output, _ = process.communicate(timeout=10)
    except BaseException:
        process.kill()
        process.wait(timeout=5)
        raise
    assert process.returncode == 0, output
    assert "Shutting down the broker." in output
    assert "resources.close_failed" not in output
