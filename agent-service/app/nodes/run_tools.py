from app.graphs.state import FinanceAgentState

from app.schemas.tools import (
    ToolCallRecord,
    ToolCallStatus,
    ToolName,
)

from app.services.web_gap_detector import (
    detect_web_gap,
)

from app.tools.registry import (
    run_chart_planner,
    run_csv_profile,
    run_document_search,
    run_financial_calculator,
    run_financial_fact_extractor,
    run_memory_lookup,
)


def run_tools_node(
    state: FinanceAgentState,
) -> FinanceAgentState:
    tool_plan = state["tool_plan"]

    tool_results: list[
        ToolCallRecord
    ] = []

    # ---------------------------------------------------------
    # 1. Memory lookup
    # ---------------------------------------------------------

    try:
        memory_output = (
            run_memory_lookup(
                state["user_id"]
            )
        )

        tool_results.append(
            ToolCallRecord(
                tool_name=(
                    ToolName.memory_lookup
                ),
                status=(
                    ToolCallStatus.completed
                ),
                input={
                    "user_id":
                        state["user_id"],
                },
                output=memory_output,
            )
        )

    except Exception as error:
        tool_results.append(
            ToolCallRecord(
                tool_name=(
                    ToolName.memory_lookup
                ),
                status=(
                    ToolCallStatus.failed
                ),
                input={
                    "user_id":
                        state["user_id"],
                },
                error=(
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )
        )

    # ---------------------------------------------------------
    # 2. Document search
    # ---------------------------------------------------------

    if (
        tool_plan.use_document_search
        and
        tool_plan.document_search_input
    ):
        document_search_input = (
            tool_plan
            .document_search_input
        )

        try:
            document_search_output = (
                run_document_search(
                    state["user_id"],
                    document_search_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .document_search
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        document_search_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        document_search_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .document_search
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        document_search_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 3. Financial fact extractor - Phase 3G-D
    # ---------------------------------------------------------

    if (
        tool_plan
        .use_financial_fact_extractor
        and
        tool_plan
        .financial_fact_extractor_input
    ):
        fact_input = (
            tool_plan
            .financial_fact_extractor_input
        )

        try:
            fact_output = (
                run_financial_fact_extractor(
                    state["user_id"],
                    fact_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .financial_fact_extractor
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        fact_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        fact_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .financial_fact_extractor
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        fact_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 4. CSV profile - Phase 3E
    # ---------------------------------------------------------

    if (
        tool_plan.use_csv_profile
        and
        tool_plan.csv_profile_input
    ):
        csv_profile_input = (
            tool_plan
            .csv_profile_input
        )

        try:
            csv_profile_output = (
                run_csv_profile(
                    state["user_id"],
                    csv_profile_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName.csv_profile
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        csv_profile_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        csv_profile_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName.csv_profile
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        csv_profile_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 5. Financial calculator
    # ---------------------------------------------------------

    if (
        tool_plan
        .use_financial_calculator
        and
        tool_plan
        .financial_calculator_input
    ):
        calculator_input = (
            tool_plan
            .financial_calculator_input
        )

        try:
            calculator_output = (
                run_financial_calculator(
                    calculator_input
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .financial_calculator
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        calculator_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        calculator_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .financial_calculator
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        calculator_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 6. Chart planner - Phase 3F
    # ---------------------------------------------------------

    if (
        tool_plan.use_chart_planner
        and
        tool_plan.chart_planner_input
    ):
        chart_planner_input = (
            tool_plan
            .chart_planner_input
        )

        try:
            chart_planner_output = (
                run_chart_planner(
                    state["user_id"],
                    chart_planner_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .chart_planner
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        chart_planner_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        chart_planner_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .chart_planner
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        chart_planner_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 7. Web fallback gap detection - Phase 3H-A
    # ---------------------------------------------------------
    #
    # IMPORTANT:
    #
    # All local tools have already completed before this
    # decision is made.
    #
    # 3H-A only DETECTS whether web fallback would be useful.
    # It does NOT perform Serper/web research.
    #
    # Actual web execution will be added in Phase 3H-B.
    # ---------------------------------------------------------

    gap = detect_web_gap(
        question=state["question"],
        use_documents=bool(
            state.get(
                "use_documents",
                False,
            )
        ),
        tool_results=tool_results,
    )

    # ---------------------------------------------------------
    # Permission is already carried through state in 3H-A.
    #
    # We deliberately do not act on it yet.
    # 3H-B will use:
    #
    # if gap.needs_web and allow_web_fallback:
    #     run_serper(...)
    # ---------------------------------------------------------

    allow_web_fallback = bool(
        state.get(
            "allow_web_fallback",
            False,
        )
    )

    # Keep the variable intentionally available for 3H-B.
    _ = allow_web_fallback

    # Web fallback is available whenever deterministic
    # local-evidence analysis finds a gap.
    web_fallback_available = bool(
        gap.needs_web
    )

    # 3H-A never executes web research.
    web_fallback_used = False

    web_fallback_reason = (
        gap.reason
        if gap.needs_web
        else None
    )

    # ---------------------------------------------------------
    # Return updated graph state
    # ---------------------------------------------------------

    return {
        **state,

        "tool_results":
            tool_results,

        "web_fallback_used":
            web_fallback_used,

        "web_fallback_available":
            web_fallback_available,

        "web_fallback_reason":
            web_fallback_reason,
    }