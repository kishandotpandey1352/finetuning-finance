from typing import Any

from pydantic import BaseModel, Field


class AgentAnalyzeRequest(BaseModel):
    question: str = Field(min_length=1)
    user_id: str | None = None
    provider_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAnalyzeResponse(BaseModel):
    ok: bool
    request_id: str
    answer: str
    memory_context: str
    memory_used_count: int
    model: str