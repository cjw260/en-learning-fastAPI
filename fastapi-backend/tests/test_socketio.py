from __future__ import annotations

import asyncio
import signal
import subprocess
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import socketio

from en_learning.common.auth import encode_token
from en_learning.common.config import Settings
from en_learning.realtime.socketio import SocketPublisher
from tests.conftest import free_port, settings_environment, settings_values, wait_for_port

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def running_core_api(port: int, redis_url: str, channel: str) -> Iterator[subprocess.Popen[str]]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "en_learning.api.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=PROJECT_ROOT,
        env=settings_environment(
            REDIS_URL=redis_url,
            SOCKET_REDIS_CHANNEL=channel,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_port(port, process)
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def access_token(settings: Settings, user_id: str) -> str:
    return encode_token(
        settings,
        user_id=user_id,
        name="Socket Tester",
        email="socket@example.test",
        token_type="access",
        refresh_version=1,
    )


async def connect_client(
    port: int,
    token: str,
    user_id: str,
) -> tuple[socketio.AsyncClient, asyncio.Queue[str]]:
    client = socketio.AsyncClient(reconnection=False)
    messages: asyncio.Queue[str] = asyncio.Queue()

    @client.on("paymentSuccess")  # type: ignore[untyped-decorator]
    async def payment_success(data: str) -> None:
        await messages.put(data)

    await client.connect(
        f"http://127.0.0.1:{port}?userId={user_id}",
        auth={"token": token},
        socketio_path="socket.io",
        transports=["websocket"],
    )
    return client, messages


@pytest.mark.asyncio
async def test_socketio_auth_multi_process_broadcast_and_reconnect(redis_url: str) -> None:
    first_port = free_port()
    second_port = free_port()
    channel = f"en-learning:test:{uuid.uuid4().hex}"
    settings = Settings(
        _env_file=None,
        **settings_values(redis_url=redis_url, socket_redis_channel=channel),
    )
    user_id = uuid.uuid4().hex
    other_user_id = uuid.uuid4().hex
    token = access_token(settings, user_id)
    other_token = access_token(settings, other_user_id)

    with running_core_api(first_port, redis_url, channel) as first_process:
        with running_core_api(second_port, redis_url, channel) as second_process:
            first_client, first_messages = await connect_client(first_port, token, user_id)
            second_client, second_messages = await connect_client(second_port, token, user_id)
            other_client, other_messages = await connect_client(
                second_port,
                other_token,
                other_user_id,
            )
            publisher = SocketPublisher(settings)
            try:
                await publisher.payment_success(user_id)
                assert await asyncio.wait_for(first_messages.get(), timeout=3) == user_id
                assert await asyncio.wait_for(second_messages.get(), timeout=3) == user_id
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(other_messages.get(), timeout=0.2)

                await second_client.disconnect()
                reconnected, reconnected_messages = await connect_client(
                    second_port,
                    token,
                    user_id,
                )
                try:
                    await publisher.payment_success(user_id)
                    assert await asyncio.wait_for(first_messages.get(), timeout=3) == user_id
                    assert await asyncio.wait_for(reconnected_messages.get(), timeout=3) == user_id
                finally:
                    await reconnected.disconnect()

                unauthenticated = socketio.AsyncClient(reconnection=False)
                with pytest.raises(socketio.exceptions.ConnectionError):
                    await unauthenticated.connect(
                        f"http://127.0.0.1:{first_port}?userId={user_id}",
                        socketio_path="socket.io",
                        transports=["websocket"],
                    )
                await unauthenticated.shutdown()

                mismatched = socketio.AsyncClient(reconnection=False)
                with pytest.raises(socketio.exceptions.ConnectionError):
                    await mismatched.connect(
                        f"http://127.0.0.1:{first_port}?userId={other_user_id}",
                        auth={"token": token},
                        socketio_path="socket.io",
                        transports=["websocket"],
                    )
                await mismatched.shutdown()
            finally:
                await publisher.close()
                if first_client.connected:
                    await first_client.disconnect()
                if second_client.connected:
                    await second_client.disconnect()
                if other_client.connected:
                    await other_client.disconnect()

        assert second_process.returncode == -signal.SIGTERM
    assert first_process.returncode == -signal.SIGTERM
