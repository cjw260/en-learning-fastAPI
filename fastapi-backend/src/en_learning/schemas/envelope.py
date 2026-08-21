from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SuccessEnvelope[T](BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    path: str
    message: str
    code: int
    success: Literal[True] = True
    data: T


class FailureEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    path: str
    message: str
    code: int
    success: Literal[False] = False
    details: dict[str, Any] | None = Field(default=None, exclude_if=lambda value: value is None)
