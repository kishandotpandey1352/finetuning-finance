from typing import Any, TypedDict


class FinanceAgentState(TypedDict, total=False):
    request_id: str
    user_id: str
    question: str
    provider_id: str | None
    metadata: dict[str, Any]

    memory_context: str
    memory_used_count: int

    answer: str
    model: str