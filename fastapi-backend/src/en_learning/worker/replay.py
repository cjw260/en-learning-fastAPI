from __future__ import annotations

import argparse
import asyncio

from en_learning.common.config import get_settings
from en_learning.services.resources import ResourceSet
from en_learning.worker.broker import broker
from en_learning.worker.tasks import execute_background_job, replay_due_jobs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay durable en-learning background jobs")
    parser.add_argument("--include-failed", action="store_true")
    parser.add_argument("--limit", type=int, default=100, choices=range(1, 1001))
    return parser


async def _run(include_failed: bool, limit: int) -> int:
    settings = get_settings()
    resources = ResourceSet(settings)
    await broker.startup()
    try:

        async def enqueue(job_id: str) -> object:
            return await execute_background_job.kiq(job_id)

        return await replay_due_jobs(
            resources,
            enqueue,
            include_failed=include_failed,
            limit=limit,
        )
    finally:
        await resources.close()
        await broker.shutdown()


def main() -> None:
    arguments = _parser().parse_args()
    count = asyncio.run(_run(arguments.include_failed, arguments.limit))
    print(f"queued {count} durable job(s)")
