from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from en_learning.bootstrap.courses import validate_assets
from en_learning.bootstrap.ecdict import BatchImportError
from en_learning.bootstrap.manifest import ECDICT_SOURCE
from en_learning.bootstrap.reporting import write_report
from en_learning.bootstrap.runner import BootstrapStepError, run_data_bootstrap, run_migrations
from en_learning.bootstrap.source import ensure_source
from en_learning.common.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = BACKEND_ROOT.parent
DEFAULT_CACHE = BACKEND_ROOT / ".bootstrap"


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="en-learning-bootstrap",
        description="Migrate and deterministically rebuild P02 development data.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_CACHE / "sources" / f"ecdict-{ECDICT_SOURCE.tag}.csv",
        help="Pinned ECDICT CSV path; downloaded from the fixed commit when absent.",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Fail instead of downloading the pinned source when --source is absent.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=REPOSITORY_ROOT / "server" / "prisma" / "assets",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_CACHE / "reports" / "bootstrap-report.json",
    )
    parser.add_argument(
        "--rejects",
        type=Path,
        default=DEFAULT_CACHE / "reports" / "ecdict-rejects.jsonl",
    )
    parser.add_argument("--batch-size", type=int, default=1_000)
    return parser


def safe_failure(error: BaseException) -> dict[str, object]:
    if isinstance(error, BatchImportError):
        return {
            "type": type(error).__name__,
            "message": str(error),
            "word_import": error.counts.to_dict(),
        }
    if isinstance(error, BootstrapStepError):
        return {"type": type(error).__name__, "message": str(error), "step": error.step}
    if isinstance(error, (ValueError, RuntimeError)):
        return {"type": type(error).__name__, "message": str(error)}
    return {
        "type": type(error).__name__,
        "message": "unexpected bootstrap failure; inspect local stderr",
    }


def main(arguments: list[str] | None = None) -> int:
    args = build_parser().parse_args(arguments)
    started_at = utc_timestamp()
    started_clock = time.monotonic()
    report: dict[str, Any] = {
        "phase": "P02",
        "status": "failed",
        "started_at": started_at,
        "environment": "unknown",
    }
    try:
        if args.batch_size < 1:
            raise ValueError("--batch-size must be positive")
        settings = Settings()
        report["environment"] = settings.environment
        if settings.environment == "production":
            raise RuntimeError("P02 bootstrap is disabled when ENVIRONMENT=production")
        source = ensure_source(
            args.source.resolve(),
            ECDICT_SOURCE,
            download_missing=not args.no_download,
        )
        validate_assets(args.assets_dir.resolve())
        report["source"] = source
        run_migrations(BACKEND_ROOT)
        result = asyncio.run(
            run_data_bootstrap(
                settings,
                source_path=args.source.resolve(),
                rejects_path=args.rejects.resolve(),
                assets_dir=args.assets_dir.resolve(),
                batch_size=args.batch_size,
            )
        )
        report.update(result)
        report["status"] = "success"
    except Exception as error:
        if isinstance(error, BootstrapStepError):
            report.update(error.partial_report)
        report["error"] = safe_failure(error)
        print(f"P02 bootstrap failed: {report['error']['message']}", file=sys.stderr)
    finally:
        report["finished_at"] = utc_timestamp()
        report["duration_ms"] = round((time.monotonic() - started_clock) * 1000)
        write_report(args.report.resolve(), report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
