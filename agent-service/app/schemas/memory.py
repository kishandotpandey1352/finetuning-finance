from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    answer_style = "answer_style"
    chart_preference = "chart_preference"
    domain_focus = "domain_focus"
    risk_tone = "risk_tone"
    provider_preference = "provider_preference"


MemoryStatus = Literal["proposed", "active", "deleted"]


class UserMemory(BaseModel):
    id: str
    user_id: str
    memory_type: MemoryType
    memory_key: str
    memory_value: str
    confidence: float = Field(default=0.7, ge=0, le=1)
    source: str = "user-proposed"
    status: MemoryStatus = "proposed"
    is_active: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    deleted_at: datetime | None = None


class ProposeMemoryRequest(BaseModel):
    memory_type: MemoryType
    memory_key: str
    memory_value: str
    confidence: float = Field(default=0.7, ge=0, le=1)
    source: str = "user-proposed"
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryActionRequest(BaseModel):
    memory_id: str


class MemoryListResponse(BaseModel):
    ok: bool
    memories: list[UserMemory]


class MemoryResponse(BaseModel):
    ok: bool
    memory: UserMemory


class BasicOkResponse(BaseModel):
    ok: bool