from app.graphs.state import FinanceAgentState
from app.schemas.tools import ToolCallRecord, ToolCallStatus, ToolName
from app.tools.registry import (
    run_csv_profile,
    run_document_search,
    run_financial_calculator,
    run_memory_lookup,
)

from app.tools.registry import (
    run_chart_planner,
    run_csv_profile,
    run_document_search,
    run_financial_calculator,
    run_memory_lookup,
)


def run_tools_node(state: FinanceAgentState) -> FinanceAgentState:
    tool_plan = state["tool_plan"]
    tool_results: list[ToolCallRecord] = []

    # ---------------------------------------------------------
    # 1. Memory lookup
    # ---------------------------------------------------------
    try:
        memory_output = run_memory_lookup(state["user_id"])

        tool_results.append(
            ToolCallRecord(
                tool_name=ToolName.memory_lookup,
                status=ToolCallStatus.completed,
                input={
                    "user_id": state["user_id"],
                },
                output=memory_output,
            )
        )

    except Exception as error:
        tool_results.append(
            ToolCallRecord(
                tool_name=ToolName.memory_lookup,
                status=ToolCallStatus.failed,
                input={
                    "user_id": state["user_id"],
                },
                error=str(error),
            )
        )

    # ---------------------------------------------------------
    # 2. Document search
    # ---------------------------------------------------------
    if (
        tool_plan.use_document_search
        and tool_plan.document_search_input
    ):
        document_search_input = tool_plan.document_search_input

        try:
            document_search_output = run_document_search(
                state["user_id"],
                document_search_input,
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=ToolName.document_search,
                    status=ToolCallStatus.completed,
                    input=document_search_input.model_dump(mode="json"),
                    output=document_search_output,
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=ToolName.document_search,
                    status=ToolCallStatus.failed,
                    input=document_search_input.model_dump(mode="json"),
                    error=str(error),
                )
            )
    # ---------------------------------------------------------
# 3. CSV profile - Phase 3E
# ---------------------------------------------------------

    if (
        tool_plan.use_csv_profile
        and tool_plan.csv_profile_input
    ):
        csv_profile_input = (
            tool_plan.csv_profile_input
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
                    tool_name=ToolName.csv_profile,
                    status=ToolCallStatus.completed,
                    input=(
                        csv_profile_input.model_dump(
                            mode="json"
                        )
                    ),
                    output=csv_profile_output,
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=ToolName.csv_profile,
                    status=ToolCallStatus.failed,
                    input=(
                        csv_profile_input.model_dump(
                            mode="json"
                        )
                    ),
                    error=str(error),
                )
            )

    # ---------------------------------------------------------
    # 4. Financial calculator
    # ---------------------------------------------------------
    if (
        tool_plan.use_financial_calculator
        and tool_plan.financial_calculator_input
    ):
        calculator_input = tool_plan.financial_calculator_input

        try:
            calculator_output = run_financial_calculator(
                calculator_input
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=ToolName.financial_calculator,
                    status=ToolCallStatus.completed,
                    input=calculator_input.model_dump(mode="json"),
                    output=calculator_output,
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=ToolName.financial_calculator,
                    status=ToolCallStatus.failed,
                    input=calculator_input.model_dump(mode="json"),
                    error=str(error),
                )
            )

    # ---------------------------------------------------------
    # Chart planner - Phase 3F
    # ---------------------------------------------------------

    if (
        tool_plan.use_chart_planner
        and tool_plan.chart_planner_input
    ):
        chart_planner_input = (
            tool_plan.chart_planner_input
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
                        ToolName.chart_planner
                    ),
                    status=(
                        ToolCallStatus.completed
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
                        ToolName.chart_planner
                    ),
                    status=(
                        ToolCallStatus.failed
                    ),
                    input=(
                        chart_planner_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=str(error),
                )
            )

    return {
        **state,
        "tool_results": tool_results,
    }