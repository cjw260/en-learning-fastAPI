from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

import en_learning.bootstrap.ecdict as ecdict_module
from en_learning.bootstrap.ecdict import (
    ECDICT_FIELDS,
    BatchImportError,
    frq_ordering,
    import_ecdict,
    normalize_frq,
    normalize_row,
)
from en_learning.common.config import Settings
from en_learning.db.models import WordBook
from en_learning.db.session import Database
from tests.conftest import settings_values


def write_ecdict(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=ECDICT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def row(word: str, *, frq: str = "", tag: str = "") -> dict[str, str]:
    return {
        "word": word,
        "phonetic": "phonetic",
        "definition": "definition",
        "translation": "翻译",
        "pos": "n:100",
        "collins": "3",
        "oxford": "1",
        "tag": tag,
        "bnc": "42",
        "frq": frq,
        "exchange": "s:words",
        "detail": "",
        "audio": "",
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", ("1", 1)),
        (" 9 ", ("9", 9)),
        ("0", ("0", None)),
        ("x", ("x", None)),
        ("", (None, None)),
    ],
)
def test_frq_normalization(raw: str, expected: tuple[str | None, int | None]) -> None:
    assert normalize_frq(raw) == expected


def test_field_mapping_and_exam_tags() -> None:
    normalized = normalize_row(row("example", frq="7", tag="gk cet4/toefl"))
    assert normalized["word"] == "example"
    assert normalized["frq"] == "7"
    assert normalized["frqRank"] == 7
    assert normalized["gk"] is True
    assert normalized["cet4"] is True
    assert normalized["toefl"] is True
    assert normalized["zk"] is False


async def import_twice_and_inspect(
    settings: Settings,
    source: Path,
    rejects: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[WordBook]]:
    database = Database(settings)
    try:
        first = await import_ecdict(source, rejects, database.session_factory, batch_size=10)
        second = await import_ecdict(source, rejects, database.session_factory, batch_size=10)
        async with database.session() as session:
            result = await session.execute(
                select(WordBook).where(WordBook.word.like("p02-order-%")).order_by(*frq_ordering())
            )
            words = list(result.scalars())
        return first.to_dict(), second.to_dict(), words
    finally:
        await database.close()


def test_import_is_auditable_idempotent_and_stably_sorted(
    migrated_postgres_url: str,
    tmp_path: Path,
) -> None:
    source = tmp_path / "ecdict.csv"
    rejects = tmp_path / "rejects.jsonl"
    missing = row("", frq="3")
    duplicate = row("p02-order-alpha", frq="2", tag="gk cet4")
    write_ecdict(
        source,
        [
            duplicate,
            row("p02-order-beta", frq="1"),
            row("p02-order-invalid", frq="not-a-number"),
            row("p02-order-zero", frq="0"),
            missing,
            duplicate,
        ],
    )
    settings = Settings(
        _env_file=None,
        **settings_values(database_url=migrated_postgres_url),
    )
    first, second, words = asyncio.run(import_twice_and_inspect(settings, source, rejects))

    assert first == {
        "rows_read": 6,
        "inserted": 4,
        "updated": 0,
        "skipped": 0,
        "rejected": 2,
        "committed_batches": 1,
        "rejection_reasons": {"duplicate_word_in_batch": 1, "missing_word": 1},
        "accepted": 4,
    }
    assert second["inserted"] == 0
    assert second["updated"] == 0
    assert second["skipped"] == 4
    assert [word.word for word in words] == [
        "p02-order-beta",
        "p02-order-alpha",
        "p02-order-invalid",
        "p02-order-zero",
    ]
    assert [word.frq_rank for word in words] == [1, 2, None, None]
    rejection_rows = [json.loads(line) for line in rejects.read_text().splitlines()]
    assert {item["reason"] for item in rejection_rows} == {
        "duplicate_word_in_batch",
        "missing_word",
    }


def test_batch_failure_keeps_committed_work_and_is_rerunnable(
    migrated_postgres_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "recover.csv"
    rejects = tmp_path / "recover-rejects.jsonl"
    write_ecdict(source, [row(f"p02-recover-{index}", frq=str(index + 1)) for index in range(4)])
    settings = Settings(
        _env_file=None,
        **settings_values(database_url=migrated_postgres_url),
    )
    original = ecdict_module.upsert_word_batch
    calls = 0

    async def fail_second_batch(*args: Any, **kwargs: Any) -> tuple[int, int, int]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected batch failure")
        return await original(*args, **kwargs)

    async def exercise_recovery() -> None:
        database = Database(settings)
        monkeypatch.setattr(ecdict_module, "upsert_word_batch", fail_second_batch)
        try:
            with pytest.raises(BatchImportError) as failure:
                await import_ecdict(source, rejects, database.session_factory, batch_size=2)
            assert failure.value.counts.committed_batches == 1
            monkeypatch.setattr(ecdict_module, "upsert_word_batch", original)
            rerun = await import_ecdict(source, rejects, database.session_factory, batch_size=2)
            assert rerun.inserted == 2
            assert rerun.skipped == 2
        finally:
            await database.close()

    asyncio.run(exercise_recovery())
