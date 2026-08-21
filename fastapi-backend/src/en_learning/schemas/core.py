from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
HTTP_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def ensure_http_url(value: str | None) -> str | None:
    if value and not HTTP_URL_PATTERN.match(value):
        raise ValueError("URL must use http or https")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LoginRequest(StrictModel):
    phone: str = Field(min_length=11, max_length=11)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError("invalid phone number")
        return value


class RegisterRequest(LoginRequest):
    name: str = Field(min_length=2, max_length=50)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("name must contain at least two non-whitespace characters")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("invalid email address")
        return value


class RefreshTokenRequest(StrictModel):
    refresh_token: str = Field(alias="refreshToken", min_length=1, max_length=4096)


class UserUpdateRequest(StrictModel):
    # The current Vue form spreads the complete login response into this payload.
    # Preserve that legacy wire shape while only exposing the editable fields below.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(min_length=2, max_length=50)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=500)
    avatar: str | None = Field(default=None, max_length=2048)
    bio: str | None = Field(default=None, max_length=500)
    is_timing_task: bool | None = Field(default=None, alias="isTimingTask")
    timing_task_time: str | None = Field(default=None, alias="timingTaskTime")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("name must contain at least two non-whitespace characters")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return RegisterRequest.normalize_email(value)

    @field_validator("address", "avatar", "bio")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("timing_task_time")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        if value is not None and not TIME_PATTERN.fullmatch(value):
            raise ValueError("timingTaskTime must be HH:MM:SS")
        return value


class TokenPair(StrictModel):
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")


class PublicUser(StrictModel):
    id: str
    name: str
    email: str | None
    phone: str
    address: str | None
    avatar: str | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    last_login_at: datetime | None = Field(alias="lastLoginAt")
    word_number: int = Field(alias="wordNumber")
    day_number: int = Field(alias="dayNumber")
    bio: str | None
    is_timing_task: bool = Field(alias="isTimingTask")
    timing_task_time: str = Field(alias="timingTaskTime")


class UserWithToken(PublicUser):
    token: TokenPair


class UserUpdateResult(StrictModel):
    name: str
    email: str | None
    address: str | None
    avatar: str | None
    bio: str | None
    is_timing_task: bool = Field(alias="isTimingTask")
    timing_task_time: str = Field(alias="timingTaskTime")


class AvatarResult(StrictModel):
    preview_url: str = Field(alias="previewUrl")
    database_url: str = Field(alias="databaseUrl")


class CourseResult(StrictModel):
    id: str
    name: str
    value: str
    description: str | None
    teacher: str
    url: str
    price: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WordResult(StrictModel):
    id: str
    word: str
    phonetic: str | None
    definition: str | None
    translation: str | None
    pos: str | None
    collins: str | None
    oxford: str | None
    tag: str | None
    bnc: str | None
    frq: str | None
    exchange: str | None
    gk: bool | None
    zk: bool | None
    gre: bool | None
    toefl: bool | None
    ielts: bool | None
    cet6: bool | None
    cet4: bool | None
    ky: bool | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WordListResult(StrictModel):
    total: int
    list: list[WordResult]


class WordQuery(StrictModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, alias="pageSize", ge=1, le=100)
    word: str | None = Field(default=None, max_length=100)
    gk: bool | None = None
    zk: bool | None = None
    gre: bool | None = None
    toefl: bool | None = None
    ielts: bool | None = None
    cet6: bool | None = None
    cet4: bool | None = None
    ky: bool | None = None

    @field_validator("word")
    @classmethod
    def normalize_word(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class MasterWordsRequest(StrictModel):
    word_ids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        alias="wordIds",
        min_length=1,
        max_length=100,
    )


class MasterWordsResult(StrictModel):
    word_number: int = Field(alias="wordNumber")


class VisitorRequest(StrictModel):
    anonymous_id: str = Field(alias="anonymousId", min_length=8, max_length=128)
    user_id: str | None = Field(default=None, alias="userId", min_length=1, max_length=128)
    browser: str | None = Field(default=None, max_length=128)
    os: str | None = Field(default=None, max_length=128)
    device: str | None = Field(default=None, max_length=128)


class UpdateVisitorRequest(StrictModel):
    visitor_id: str = Field(alias="visitorId", min_length=1, max_length=128)
    user_id: str = Field(alias="userId", min_length=1, max_length=128)


class TrackerBase(StrictModel):
    visitor_id: str = Field(alias="visitorId", min_length=1, max_length=128)


class PerformanceRequest(TrackerBase):
    fp: float = Field(ge=0, le=1_000_000_000)
    fcp: float = Field(ge=0, le=1_000_000_000)
    lcp: float = Field(ge=0, le=1_000_000_000)
    inp: float = Field(ge=0, le=1_000_000_000)
    cls: float = Field(ge=0, le=1_000_000_000)

    @field_validator("fp", "fcp", "lcp", "inp", "cls")
    @classmethod
    def finite_metric(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric must be finite")
        return value


class PageViewRequest(TrackerBase):
    url: str = Field(min_length=1, max_length=2048)
    referrer: str | None = Field(default=None, max_length=2048)
    path: str = Field(min_length=1, max_length=2048)

    @field_validator("url", "referrer")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return ensure_http_url(value)


class EventRequest(TrackerBase):
    event: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    url: str | None = Field(default=None, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return ensure_http_url(value)


class ErrorRequest(TrackerBase):
    error: str = Field(min_length=1, max_length=64)
    message: str | None = Field(default=None, max_length=2000)
    stack: str | None = Field(default=None, max_length=8000)
    url: str | None = Field(default=None, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return ensure_http_url(value)
