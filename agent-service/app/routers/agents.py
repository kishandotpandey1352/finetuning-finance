from uuid import uuid4

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from app.graphs.finance_memory_graph import (
    build_finance_memory_graph,
)

from app.schemas.agent import (
    AgentAnalyzeRequest,
    AgentAnalyzeResponse,
)


router = APIRouter(
    prefix="/agents",
    tags=["agents"],
)


def get_user_id(
    request_user_id: str | None,
    header_user_id: str | None,
) -> str:
    return (
        request_user_id
        or header_user_id
        or "local-demo-user"
    )


@router.post(
    "/analyze",
    response_model=AgentAnalyzeResponse,
)
def analyze(
    request: AgentAnalyzeRequest,
    x_user_id: str | None = Header(
        default=None
    ),
):
    request_id = str(
        uuid4()
    )

    effective_dataset_id = (
        request.dataset_id
    )

    # ---------------------------------------------------------
    # Phase 3F
    # Ensure dataset_id and chart_request.dataset_id agree.
    # ---------------------------------------------------------

    if request.chart_request:
        chart_dataset_id = (
            request
            .chart_request
            .dataset_id
        )

        if (
            effective_dataset_id
            and effective_dataset_id
            != chart_dataset_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "dataset_id and "
                    "chart_request.dataset_id "
                    "must refer to the same "
                    "dataset."
                ),
            )

        effective_dataset_id = (
            chart_dataset_id
        )

    try:
        user_id = get_user_id(
            request.user_id,
            x_user_id,
        )

        graph = (
            build_finance_memory_graph()
        )

        # -----------------------------------------------------
        # Initial LangGraph state
        # -----------------------------------------------------

        result = graph.invoke(
            {
                "request_id":
                    request_id,

                "user_id":
                    user_id,

                "question":
                    request
                    .question
                    .strip(),

                "provider_id":
                    request.provider_id,

                # ---------------------------------------------
                # Phase 3D / 3G
                # Document-aware analysis
                # ---------------------------------------------

                "use_documents":
                    request.use_documents,

                "document_ids":
                    request.document_ids,

                "top_k":
                    request.top_k,

                # ---------------------------------------------
                # Phase 3E
                # Structured dataset analysis
                # ---------------------------------------------

                "dataset_id":
                    effective_dataset_id,

                # ---------------------------------------------
                # Phase 3F
                # Chart planning
                # ---------------------------------------------

                "chart_request":
                    request.chart_request,

                # ---------------------------------------------
                # Phase 3H-A
                # Web fallback control
                #
                # IMPORTANT:
                # 3H-A does not execute web research.
                # These fields only carry user permission
                # and expose deterministic gap detection.
                # ---------------------------------------------

                "allow_web_fallback":
                    request.allow_web_fallback,

                "trusted_web_domains":
                    request.trusted_web_domains,

                "web_fallback_used":
                    False,

                "web_fallback_available":
                    False,

                "web_fallback_reason":
                    None,

                # ---------------------------------------------
                # Existing request metadata
                # ---------------------------------------------

                "metadata":
                    request.metadata,
            }
        )

        # -----------------------------------------------------
        # Extract graph results
        # -----------------------------------------------------

        tool_plan = (
            result.get(
                "tool_plan"
            )
        )

        tool_results = (
            result.get(
                "tool_results",
                [],
            )
        )

        # -----------------------------------------------------
        # API response
        # -----------------------------------------------------

        return AgentAnalyzeResponse(
            ok=True,

            request_id=(
                request_id
            ),

            answer=(
                result.get(
                    "answer",
                    "",
                )
            ),

            memory_context=(
                result.get(
                    "memory_context",
                    "",
                )
            ),

            memory_used_count=(
                result.get(
                    "memory_used_count",
                    0,
                )
            ),

            model=(
                result.get(
                    "model",
                    "",
                )
            ),

            tool_plan=(
                tool_plan.model_dump(
                    mode="json"
                )
                if tool_plan
                else None
            ),

            tool_results=[
                tool_result.model_dump(
                    mode="json"
                )
                for tool_result
                in tool_results
            ],

            grounding=(
                result.get(
                    "grounding"
                )
            ),

            # ---------------------------------------------
            # Phase 3H-A
            # Web fallback state
            # ---------------------------------------------

            web_fallback_used=bool(
                result.get(
                    "web_fallback_used",
                    False,
                )
            ),

            web_fallback_available=bool(
                result.get(
                    "web_fallback_available",
                    False,
                )
            ),

            web_fallback_reason=(
                result.get(
                    "web_fallback_reason"
                )
            ),
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(error).__name__}: "
                f"{error}"
            ),
        ) from error