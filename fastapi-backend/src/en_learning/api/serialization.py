from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from en_learning.common.responses import success_response
from en_learning.db.models import Course, User, WordBook


def utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def token_data(access_token: str, refresh_token: str) -> dict[str, str]:
    return {"accessToken": access_token, "refreshToken": refresh_token}


def business_success(request: Request, data: Any) -> JSONResponse:
    return success_response(request, data, message="Success")


def user_data(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "address": user.address,
        "avatar": user.avatar,
        "createdAt": utc_iso(user.created_at),
        "updatedAt": utc_iso(user.updated_at),
        "lastLoginAt": utc_iso(user.last_login_at),
        "wordNumber": user.word_number,
        "dayNumber": user.day_number,
        "bio": user.bio,
        "isTimingTask": user.is_timing_task,
        "timingTaskTime": user.timing_task_time,
    }


def user_update_data(user: User) -> dict[str, Any]:
    return {
        "name": user.name,
        "email": user.email,
        "address": user.address,
        "avatar": user.avatar,
        "bio": user.bio,
        "isTimingTask": user.is_timing_task,
        "timingTaskTime": user.timing_task_time,
    }


def price_string(price: Decimal) -> str:
    return f"{price:.2f}"


def course_data(course: Course) -> dict[str, Any]:
    return {
        "id": course.id,
        "name": course.name,
        "value": course.value,
        "description": course.description,
        "teacher": course.teacher,
        "url": course.url,
        "price": price_string(course.price),
        "createdAt": utc_iso(course.created_at),
        "updatedAt": utc_iso(course.updated_at),
    }


def word_data(word: WordBook) -> dict[str, Any]:
    return {
        "id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "definition": word.definition,
        "translation": word.translation,
        "pos": word.pos,
        "collins": word.collins,
        "oxford": word.oxford,
        "tag": word.tag,
        "bnc": word.bnc,
        "frq": word.frq,
        "exchange": word.exchange,
        "gk": word.gk,
        "zk": word.zk,
        "gre": word.gre,
        "toefl": word.toefl,
        "ielts": word.ielts,
        "cet6": word.cet6,
        "cet4": word.cet4,
        "ky": word.ky,
        "createdAt": utc_iso(word.created_at),
        "updatedAt": utc_iso(word.updated_at),
    }
