import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg

from tests.conftest import PROJECT_ROOT

APPLICATION_TABLES = {
    "User",
    "WordBookRecord",
    "WordBook",
    "PaymentRecord",
    "CourseRecord",
    "Course",
    "Visitor",
    "PageView",
    "TrackEvent",
    "PerformanceEntry",
    "ErrorEntry",
    "AIChatThread",
    "AIChatMessage",
}


def run_alembic(database_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    executable = Path(sys.executable).with_name("alembic")
    result = subprocess.run(
        [str(executable), *arguments],
        cwd=PROJECT_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"alembic {' '.join(arguments)} failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


async def inspect_database(database_url: str) -> tuple[set[str], list[str], tuple[int, int], str]:
    connection = await asyncpg.connect(database_url.replace("+asyncpg", ""))
    try:
        tables = {
            row["tablename"]
            for row in await connection.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        }
        enum_values = [
            row["enumlabel"]
            for row in await connection.fetch(
                """
                SELECT enumlabel
                FROM pg_enum
                JOIN pg_type ON pg_type.oid = pg_enum.enumtypid
                WHERE typname = 'TradeStatus'
                ORDER BY enumsortorder
                """
            )
        ]
        amount = await connection.fetchrow(
            """
            SELECT numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'PaymentRecord' AND column_name = 'amount'
            """
        )
        created_at = await connection.fetchval(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'User' AND column_name = 'createdAt'
            """
        )
        precision = (amount["numeric_precision"], amount["numeric_scale"]) if amount else (0, 0)
        return tables, enum_values, precision, created_at
    finally:
        await connection.close()


def test_alembic_upgrade_downgrade_upgrade_and_metadata_check(postgres_url: str) -> None:
    run_alembic(postgres_url, "upgrade", "head")
    tables, enum_values, precision, created_at = asyncio.run(inspect_database(postgres_url))
    assert APPLICATION_TABLES <= tables
    assert enum_values == [
        "NOT_PAY",
        "WAIT_BUYER_PAY",
        "TRADE_CLOSED",
        "TRADE_SUCCESS",
        "TRADE_FINISHED",
    ]
    assert precision == (65, 30)
    assert created_at == "timestamp without time zone"
    check = run_alembic(postgres_url, "check")
    assert "No new upgrade operations detected" in check.stdout

    run_alembic(postgres_url, "downgrade", "base")
    tables, enum_values, _, _ = asyncio.run(inspect_database(postgres_url))
    assert APPLICATION_TABLES.isdisjoint(tables)
    assert enum_values == []

    run_alembic(postgres_url, "upgrade", "head")
    tables, enum_values, _, _ = asyncio.run(inspect_database(postgres_url))
    assert APPLICATION_TABLES <= tables
    assert enum_values
