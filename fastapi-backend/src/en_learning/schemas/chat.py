from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


class ChatRole(StrEnum):
    NORMAL = "normal"
    MASTER = "master"
    BUSINESS = "business"
    QILINGE = "qilinge"
    XIAOMAN = "xiaoman"


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    deep_think: StrictBool = Field(alias="deepThink")
    web_search: StrictBool = Field(alias="webSearch")
    role: ChatRole
    content: str = Field(min_length=1)
    user_id: str = Field(alias="userId", min_length=1, max_length=128)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class PromptMode(BaseModel):
    id: str
    label: str
    role: ChatRole


class HistoryMessage(BaseModel):
    role: str
    content: str
    reasoning: str | None = None
