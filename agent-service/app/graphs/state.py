from typing import Any, TypedDict

from app.schemas.tools import ToolCallRecord, ToolPlan


class FinanceAgentState(TypedDict, total=False):
    request_id: str
    user_id: str
    question: str
    provider_id: str | None
    metadata: dict[str, Any]

    use_documents: bool
    document_ids: list[str]
    top_k: int
    dataset_id: str | None
    memory_context: str
    memory_used_count: int

    tool_plan: ToolPlan
    tool_results: list[ToolCallRecord]

    answer: str
    model: str

    grounding: dict[str, Any]