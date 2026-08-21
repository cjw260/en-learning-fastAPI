import asyncio
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import asyncpg
import pytest

from en_learning.common.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def settings_values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "environment": "test",
        "log_level": "INFO",
        "database_url": "postgresql+asyncpg://test:test@127.0.0.1:1/en_learning",
        "redis_url": "redis://127.0.0.1:1/0",
        "jwt_secret": "test-jwt-secret",
        "minio_endpoint": "127.0.0.1",
        "minio_port": 1,
        "minio_use_ssl": False,
        "minio_access_key": "test-access-key",
        "minio_secret_key": "test-secret-key",
        "minio_bucket": "test-bucket",
        "deepseek_base_url": "https://example.invalid",
        "deepseek_api_key": "test-llm-key",
        "http_timeout_seconds": 0.2,
        "health_check_timeout_seconds": 0.1,
    }
    values.update(overrides)
    return values


def settings_environment(**overrides: str) -> dict[str, str]:
    values = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:1/en_learning",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "SECRET_KEY": "test-jwt-secret",
        "MINIO_ENDPOINT": "127.0.0.1",
        "MINIO_PORT": "1",
        "MINIO_USE_SSL": "false",
        "MINIO_ACCESS_KEY": "test-access-key",
        "MINIO_SECRET_KEY": "test-secret-key",
        "MINIO_BUCKET": "test-bucket",
        "DEEPSEEK_BASE_URL": "https://example.invalid",
        "DEEPSEEK_API_KEY": "test-llm-key",
        "HTTP_TIMEOUT_SECONDS": "0.2",
        "HEALTH_CHECK_TIMEOUT_SECONDS": "0.1",
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    }
    values.update(overrides)
    return {**os.environ, **values}


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, **settings_values())


def find_executable(name: str, formula: str) -> str:
    if executable := shutil.which(name):
        return executable
    for prefix in (Path("/opt/homebrew/opt"), Path("/usr/local/opt")):
        candidate = prefix / formula / "bin" / name
        if candidate.is_file():
            return str(candidate)
    pytest.fail(f"Required local executable not found: {name}")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_port(port: int, process: subprocess.Popen[str], timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            pytest.fail(f"Process exited before opening port {port}:\n{output}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    pytest.fail(f"Timed out waiting for port {port}")


@pytest.fixture(scope="session")
def redis_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    redis_server = find_executable("redis-server", "redis")
    port = free_port()
    data_dir = tmp_path_factory.mktemp("redis-data")
    process = subprocess.Popen(
        [
            redis_server,
            "--bind",
            "127.0.0.1",
            "--port",
            str(port),
            "--dir",
            str(data_dir),
            "--save",
            "",
            "--appendonly",
            "no",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_port(port, process)
        yield f"redis://127.0.0.1:{port}/0"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture(scope="session")
def postgres_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    initdb = find_executable("initdb", "postgresql@17")
    pg_ctl = find_executable("pg_ctl", "postgresql@17")
    createdb = find_executable("createdb", "postgresql@17")
    data_dir = tmp_path_factory.mktemp("postgres-data")
    log_file = data_dir / "postgres.log"
    port = free_port()

    subprocess.run(
        [initdb, "-D", str(data_dir), "-A", "trust", "--no-locale", "--encoding=UTF8"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            pg_ctl,
            "-D",
            str(data_dir),
            "-l",
            str(log_file),
            "-o",
            f"-F -p {port} -k /tmp",
            "-w",
            "start",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        subprocess.run(
            [createdb, "-h", "127.0.0.1", "-p", str(port), "en_learning_test"],
            check=True,
            capture_output=True,
            text=True,
        )
        yield f"postgresql+asyncpg://127.0.0.1:{port}/en_learning_test"
    finally:
        subprocess.run(
            [pg_ctl, "-D", str(data_dir), "-m", "fast", "-w", "stop"],
            check=True,
            capture_output=True,
            text=True,
        )


@pytest.fixture
def migrated_postgres_url(postgres_url: str) -> str:
    alembic = Path(sys.executable).with_name("alembic")
    subprocess.run(
        [str(alembic), "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "DATABASE_URL": postgres_url},
        check=True,
        capture_output=True,
        text=True,
    )
    return postgres_url


@pytest.fixture
def isolated_postgres_url(postgres_url: str) -> Iterator[str]:
    database_name = f"en_learning_{uuid.uuid4().hex}"
    base_url = postgres_url.rsplit("/", maxsplit=1)[0]
    admin_url = f"{base_url}/postgres".replace("+asyncpg", "")

    async def create_database() -> None:
        connection = await asyncpg.connect(admin_url)
        try:
            await connection.execute(f'CREATE DATABASE "{database_name}"')
        finally:
            await connection.close()

    async def drop_database() -> None:
        connection = await asyncpg.connect(admin_url)
        try:
            await connection.execute(f'DROP DATABASE "{database_name}" WITH (FORCE)')
        finally:
            await connection.close()

    asyncio.run(create_database())
    try:
        yield f"{base_url}/{database_name}"
    finally:
        asyncio.run(drop_database())


@pytest.fixture
def minio_values(tmp_path: Path) -> Iterator[dict[str, Any]]:
    minio = find_executable("minio", "minio")
    api_port = free_port()
    console_port = free_port()
    data_dir = tmp_path / "minio-data"
    data_dir.mkdir()
    access_key = "p02-test-access"
    secret_key = "p02-test-secret-key"
    process = subprocess.Popen(
        [
            minio,
            "server",
            "--quiet",
            "--address",
            f"127.0.0.1:{api_port}",
            "--console-address",
            f"127.0.0.1:{console_port}",
            str(data_dir),
        ],
        env={
            **os.environ,
            "MINIO_ROOT_USER": access_key,
            "MINIO_ROOT_PASSWORD": secret_key,
            "MINIO_BROWSER": "off",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_port(api_port, process)
        yield {
            "minio_endpoint": "127.0.0.1",
            "minio_port": api_port,
            "minio_use_ssl": False,
            "minio_access_key": access_key,
            "minio_secret_key": secret_key,
            "minio_bucket": "avatar",
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
