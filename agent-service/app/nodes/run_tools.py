from app.graphs.state import FinanceAgentState
from app.schemas.tools import ToolCallRecord, ToolCallStatus, ToolName
from app.tools.registry import (
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
    # 3. Financial calculator
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

    return {
        **state,
        "tool_results": tool_results,
    }