from __future__ import annotations

import csv
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from en_learning.bootstrap.identifiers import stable_identifier
from en_learning.db.models import WordBook

ECDICT_FIELDS = (
    "word",
    "phonetic",
    "definition",
    "translation",
    "pos",
    "collins",
    "oxford",
    "tag",
    "bnc",
    "frq",
    "exchange",
    "detail",
    "audio",
)
MAPPED_FIELDS = (
    "word",
    "phonetic",
    "definition",
    "translation",
    "pos",
    "collins",
    "oxford",
    "tag",
    "bnc",
    "frq",
    "exchange",
    "frqRank",
    "gk",
    "zk",
    "gre",
    "toefl",
    "ielts",
    "cet6",
    "cet4",
    "ky",
)
EXAM_TAGS = ("gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky")
MAX_WORD_LENGTH = 512
MAX_FIELD_LENGTH = 4 * 1024 * 1024


class RejectedRow(ValueError):
    def __init__(self, reason: str, word: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.word = word


class InvalidSourceFormat(RuntimeError):
    """The CSV cannot be interpreted using the pinned ECDICT schema."""


@dataclass(slots=True)
class ImportCounts:
    rows_read: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    rejected: int = 0
    committed_batches: int = 0
    rejection_reasons: Counter[str] = field(default_factory=Counter)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["rejection_reasons"] = dict(sorted(self.rejection_reasons.items()))
        data["accepted"] = self.inserted + self.updated + self.skipped
        return data


class BatchImportError(RuntimeError):
    def __init__(self, counts: ImportCounts) -> None:
        super().__init__(
            f"word import failed after {counts.committed_batches} committed batches; rerun is safe"
        )
        self.counts = counts


class RejectWriter:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file = path.open("w", encoding="utf-8")

    def record(self, *, line: int, reason: str, word: str | None = None) -> None:
        payload = {"line": line, "reason": reason}
        if word is not None:
            payload["word"] = word[:MAX_WORD_LENGTH]
        self._file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> RejectWriter:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_FIELD_LENGTH:
        raise RejectedRow("field_too_long")
    return normalized


def normalize_frq(value: str | None) -> tuple[str | None, int | None]:
    normalized = optional_text(value)
    if normalized is None:
        return None, None
    try:
        numeric = int(normalized, 10)
    except ValueError:
        return normalized, None
    return normalized, numeric if numeric > 0 else None


def normalize_row(row: Mapping[str | None, Any]) -> dict[str, Any]:
    if row.get(None):
        raise RejectedRow("unexpected_extra_columns")
    raw_word = row.get("word")
    word = optional_text(raw_word if isinstance(raw_word, str) else None)
    if word is None:
        raise RejectedRow("missing_word")
    if len(word) > MAX_WORD_LENGTH:
        raise RejectedRow("word_too_long", word)

    tag = optional_text(row.get("tag"))
    tags = frozenset(tag.lower().replace("/", " ").split()) if tag else frozenset()
    frq, frq_rank = normalize_frq(row.get("frq"))
    now = utc_now_naive()
    normalized: dict[str, Any] = {
        "id": stable_identifier("word", word),
        "word": word,
        "phonetic": optional_text(row.get("phonetic")),
        "definition": optional_text(row.get("definition")),
        "translation": optional_text(row.get("translation")),
        "pos": optional_text(row.get("pos")),
        "collins": optional_text(row.get("collins")),
        "oxford": optional_text(row.get("oxford")),
        "tag": tag,
        "bnc": optional_text(row.get("bnc")),
        "frq": frq,
        "frqRank": frq_rank,
        "exchange": optional_text(row.get("exchange")),
        "createdAt": now,
        "updatedAt": now,
    }
    normalized.update({exam: exam in tags for exam in EXAM_TAGS})
    return normalized


def frq_ordering() -> tuple[ColumnElement[Any], ...]:
    """D007 ordering: positive numeric rank first, then a stable tail."""

    return (
        WordBook.frq_rank.asc().nulls_last(),
        WordBook.word.asc(),
        WordBook.id.asc(),
    )


async def upsert_word_batch(
    session_factory: async_sessionmaker[AsyncSession],
    rows: Sequence[dict[str, Any]],
) -> tuple[int, int, int]:
    words = [str(row["word"]) for row in rows]
    async with session_factory() as session, session.begin():
        result = await session.execute(select(WordBook).where(WordBook.word.in_(words)))
        existing = {record.word: record for record in result.scalars()}
        inserted = 0
        updated = 0
        skipped = 0
        changed_rows: list[dict[str, Any]] = []
        for row in rows:
            current = existing.get(str(row["word"]))
            if current is None:
                inserted += 1
                changed_rows.append(row)
                continue
            is_changed = any(
                getattr(current, "frq_rank" if field_name == "frqRank" else field_name)
                != row[field_name]
                for field_name in MAPPED_FIELDS
            )
            if is_changed:
                updated += 1
                changed_rows.append(row)
            else:
                skipped += 1

        if changed_rows:
            statement = postgres_insert(WordBook.__table__)  # type: ignore[arg-type]
            statement = statement.values(changed_rows)
            excluded = statement.excluded
            statement = statement.on_conflict_do_update(
                index_elements=[WordBook.__table__.c.word],
                set_={
                    field_name: getattr(excluded, field_name)
                    for field_name in (*MAPPED_FIELDS[1:], "updatedAt")
                },
            )
            await session.execute(statement)
    return inserted, updated, skipped


async def import_ecdict(
    source_path: Path,
    rejects_path: Path,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    batch_size: int = 1_000,
) -> ImportCounts:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    counts = ImportCounts()
    batch: list[dict[str, Any]] = []
    batch_words: set[str] = set()

    async def flush() -> None:
        if not batch:
            return
        try:
            inserted, updated, skipped = await upsert_word_batch(session_factory, batch)
        except Exception as error:
            raise BatchImportError(counts) from error
        counts.inserted += inserted
        counts.updated += updated
        counts.skipped += skipped
        counts.committed_batches += 1
        batch.clear()
        batch_words.clear()

    try:
        source = source_path.open("r", encoding="utf-8-sig", newline="")
    except UnicodeError as error:
        raise InvalidSourceFormat("ECDICT source is not valid UTF-8") from error

    with source, RejectWriter(rejects_path) as rejects:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != list(ECDICT_FIELDS):
            raise InvalidSourceFormat(
                f"ECDICT header mismatch: expected {list(ECDICT_FIELDS)}, got {reader.fieldnames}"
            )
        while True:
            try:
                row = next(reader)
            except StopIteration:
                break
            except csv.Error:
                counts.rows_read += 1
                counts.rejected += 1
                counts.rejection_reasons["malformed_csv"] += 1
                rejects.record(line=reader.line_num, reason="malformed_csv")
                continue
            except UnicodeError as error:
                raise InvalidSourceFormat("ECDICT source is not valid UTF-8") from error

            counts.rows_read += 1
            try:
                normalized = normalize_row(row)
                word = str(normalized["word"])
                if word in batch_words:
                    raise RejectedRow("duplicate_word_in_batch", word)
            except RejectedRow as error:
                counts.rejected += 1
                counts.rejection_reasons[error.reason] += 1
                rejects.record(line=reader.line_num, reason=error.reason, word=error.word)
                continue
            batch.append(normalized)
            batch_words.add(word)
            if len(batch) >= batch_size:
                await flush()
        await flush()
    return counts
