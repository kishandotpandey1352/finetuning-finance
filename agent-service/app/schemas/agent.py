from typing import Any

from pydantic import BaseModel, Field


class AgentAnalyzeRequest(BaseModel):
    question: str = Field(min_length=1)
    user_id: str | None = None
    provider_id: str | None = None

    use_documents: bool = False
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=6, ge=1, le=20)

    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAnalyzeResponse(BaseModel):
    ok: bool
    request_id: str
    answer: str

    memory_context: str
    memory_used_count: int

    model: str

    tool_plan: dict[str, Any] | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)

    grounding: dict[str, Any] | None = None