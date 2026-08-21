from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["alive", "ready"]
    service: str
    checks: dict[str, Literal["up", "down"]] | None = None
