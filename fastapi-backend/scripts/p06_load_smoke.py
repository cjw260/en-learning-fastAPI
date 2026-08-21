"""Bounded black-box concurrency and latency smoke test for P06 acceptance."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import time
from dataclasses import asdict, dataclass

from httpx import AsyncClient, Limits


@dataclass(frozen=True)
class Result:
    endpoint: str
    requests: int
    concurrency: int
    errors: int
    p50_ms: float
    p95_ms: float
    max_ms: float


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]


async def benchmark(
    client: AsyncClient,
    endpoint: str,
    requests: int,
    concurrency: int,
    headers: dict[str, str],
) -> Result:
    semaphore = asyncio.Semaphore(concurrency)

    async def one_request() -> tuple[float, bool]:
        async with semaphore:
            started = time.perf_counter()
            try:
                response = await client.get(endpoint, headers=headers)
                success = response.status_code == 200
            except OSError:
                success = False
            elapsed_ms = (time.perf_counter() - started) * 1000
            return elapsed_ms, success

    samples = await asyncio.gather(*(one_request() for _ in range(requests)))
    latencies = [elapsed for elapsed, _ in samples]
    errors = sum(not success for _, success in samples)
    return Result(
        endpoint=endpoint,
        requests=requests,
        concurrency=concurrency,
        errors=errors,
        p50_ms=round(percentile(latencies, 0.50), 2),
        p95_ms=round(percentile(latencies, 0.95), 2),
        max_ms=round(max(latencies), 2),
    )


async def run(args: argparse.Namespace) -> int:
    limits = Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    headers = {"Authorization": f"Bearer {args.access_token}"} if args.access_token else {}
    targets = [
        f"{args.core_url.rstrip('/')}/api/v1/course/list",
        f"{args.core_url.rstrip('/')}/api/v1/word-book?page=1&pageSize=12",
    ]
    if args.access_token:
        targets.append(f"{args.ai_url.rstrip('/')}/ai/v1/prompt/list")

    async with AsyncClient(timeout=args.timeout, limits=limits) as client:
        results = [
            await benchmark(client, target, args.requests, args.concurrency, headers)
            for target in targets
        ]
    print(json.dumps({"results": [asdict(result) for result in results]}, indent=2))
    return int(any(result.errors or result.p95_ms > args.max_p95_ms for result in results))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-url", default="http://127.0.0.1:3000")
    parser.add_argument("--ai-url", default="http://127.0.0.1:3001")
    parser.add_argument("--access-token", default=os.environ.get("P06_ACCESS_TOKEN"))
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--max-p95-ms", type=float, default=500)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.concurrency > args.requests:
        parser.error("requests and concurrency must define a non-empty bounded run")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
