from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException

from app.graphs.finance_memory_graph import build_finance_memory_graph
from app.schemas.agent import AgentAnalyzeRequest, AgentAnalyzeResponse


router = APIRouter(prefix="/agents", tags=["agents"])


def get_user_id(request_user_id: str | None, header_user_id: str | None) -> str:
    return request_user_id or header_user_id or "local-demo-user"


@router.post("/analyze", response_model=AgentAnalyzeResponse)
def analyze(
    request: AgentAnalyzeRequest,
    x_user_id: str | None = Header(default=None),
):
    request_id = str(uuid4())

    try:
        user_id = get_user_id(request.user_id, x_user_id)
        graph = build_finance_memory_graph()

        result = graph.invoke(
            {
                "request_id": request_id,
                "user_id": user_id,
                "question": request.question.strip(),
                "provider_id": request.provider_id,
                "metadata": request.metadata,
            }
        )

        return AgentAnalyzeResponse(
            ok=True,
            request_id=request_id,
            answer=result.get("answer", ""),
            memory_context=result.get("memory_context", ""),
            memory_used_count=result.get("memory_used_count", 0),
            model=result.get("model", ""),
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error