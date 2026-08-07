import re

from app.graphs.state import FinanceAgentState
from app.schemas.tools import (
    FinancialCalculationType,
    FinancialCalculatorInput,
    ToolPlan,
)
from app.schemas.tools import DocumentSearchInput

NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def _extract_numbers(text: str) -> list[float]:
    return [float(value) for value in NUMBER_PATTERN.findall(text)]


def plan_tools_node(state: FinanceAgentState) -> FinanceAgentState:
    question = state["question"]
    lowered = question.lower()
    numbers = _extract_numbers(question)

    use_financial_calculator = False
    calculator_input = None
    reason = "Always check confirmed memory. No calculator needed."

    if any(word in lowered for word in ["growth", "increase", "decrease"]):
        if len(numbers) >= 2:
            use_financial_calculator = True
            calculator_input = FinancialCalculatorInput(
                calculation_type=FinancialCalculationType.growth_rate,
                previous_value=numbers[0],
                current_value=numbers[1],
            )
            reason = "Detected a growth-rate style question with two numbers."

    elif any(word in lowered for word in ["margin", "ratio"]):
        if len(numbers) >= 2:
            use_financial_calculator = True
            calculator_input = FinancialCalculatorInput(
                calculation_type=FinancialCalculationType.margin,
                numerator=numbers[0],
                denominator=numbers[1],
            )
            reason = "Detected a margin or ratio question with two numbers."

    elif any(word in lowered for word in ["difference", "delta", "change"]):
        if len(numbers) >= 2:
            use_financial_calculator = True
            calculator_input = FinancialCalculatorInput(
                calculation_type=FinancialCalculationType.delta,
                previous_value=numbers[0],
                current_value=numbers[1],
            )
            reason = "Detected a delta/change question with two numbers."

    elif "cagr" in lowered:
        if len(numbers) >= 3:
            use_financial_calculator = True
            calculator_input = FinancialCalculatorInput(
                calculation_type=FinancialCalculationType.cagr,
                beginning_value=numbers[0],
                ending_value=numbers[1],
                periods=numbers[2],
            )
            reason = "Detected a CAGR question with beginning, ending, and period values."

    use_document_search = state.get("use_documents", False)

    document_search_input = None

    if use_document_search:
        document_search_input = DocumentSearchInput(
            query=question,
            document_ids=state.get("document_ids", []),
            top_k=state.get("top_k", 6),
        )

    return {
        **state,
        "tool_plan": ToolPlan(
                    use_memory_lookup=True,
                    use_financial_calculator=use_financial_calculator,
                    financial_calculator_input=calculator_input,
                    use_document_search=use_document_search,
                    document_search_input=document_search_input,
                    reason=reason,
                ),
    }