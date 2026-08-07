import re

from app.graphs.state import FinanceAgentState
from app.schemas.tools import (
    CsvProfileInput,
    DocumentSearchInput,
    FinancialCalculationType,
    FinancialCalculatorInput,
    ToolPlan,
)
from app.schemas.tools import DocumentSearchInput

NUMBER_PATTERN = re.compile(
    r"-?\d+(?:\.\d+)?"
)


def _extract_numbers(
    text: str,
) -> list[float]:
    return [
        float(value)
        for value
        in NUMBER_PATTERN.findall(text)
    ]


def plan_tools_node(
    state: FinanceAgentState,
) -> FinanceAgentState:
    question = state["question"]

    lowered = question.lower()

    numbers = _extract_numbers(
        question
    )

    # ---------------------------------------------------------
    # Financial calculator planning
    # ---------------------------------------------------------

    use_financial_calculator = False
    calculator_input = None

    reason_parts = [
        "Always check confirmed memory."
    ]

    if any(
        word in lowered
        for word in [
            "growth",
            "increase",
            "decrease",
        ]
    ):
        if len(numbers) >= 2:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.growth_rate
                    ),
                    previous_value=numbers[0],
                    current_value=numbers[1],
                )
            )

            reason_parts.append(
                "Detected a growth-rate style "
                "question with two numbers."
            )

    elif any(
        word in lowered
        for word in [
            "margin",
            "ratio",
        ]
    ):
        if len(numbers) >= 2:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.margin
                    ),
                    numerator=numbers[0],
                    denominator=numbers[1],
                )
            )

            reason_parts.append(
                "Detected a margin or ratio "
                "question with two numbers."
            )

    elif any(
        word in lowered
        for word in [
            "difference",
            "delta",
            "change",
        ]
    ):
        if len(numbers) >= 2:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.delta
                    ),
                    previous_value=numbers[0],
                    current_value=numbers[1],
                )
            )

            reason_parts.append(
                "Detected a delta/change question "
                "with two numbers."
            )

    elif "cagr" in lowered:
        if len(numbers) >= 3:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.cagr
                    ),
                    beginning_value=numbers[0],
                    ending_value=numbers[1],
                    periods=numbers[2],
                )
            )

            reason_parts.append(
                "Detected a CAGR question with "
                "beginning, ending, and period values."
            )

    # ---------------------------------------------------------
    # Document search planning - Phase 3D
    # ---------------------------------------------------------

    use_document_search = state.get(
        "use_documents",
        False,
    )

    document_search_input = None

    if use_document_search:
        document_search_input = (
            DocumentSearchInput(
                query=question,
                document_ids=state.get(
                    "document_ids",
                    [],
                ),
                top_k=state.get(
                    "top_k",
                    6,
                ),
            )
        )

        reason_parts.append(
            "Document search was requested."
        )

    # ---------------------------------------------------------
    # CSV profiling planning - Phase 3E
    # ---------------------------------------------------------

    dataset_id = state.get(
        "dataset_id"
    )

    use_csv_profile = bool(
        dataset_id
    )

    csv_profile_input = None

    if dataset_id:
        csv_profile_input = (
            CsvProfileInput(
                dataset_id=dataset_id
            )
        )

        reason_parts.append(
            "A CSV dataset was supplied, "
            "so structured dataset profiling is required."
        )

    return {
        **state,
        "tool_plan": ToolPlan(
            use_memory_lookup=True,

            use_financial_calculator=(
                use_financial_calculator
            ),
            financial_calculator_input=(
                calculator_input
            ),

            use_document_search=(
                use_document_search
            ),
            document_search_input=(
                document_search_input
            ),

            use_csv_profile=(
                use_csv_profile
            ),
            csv_profile_input=(
                csv_profile_input
            ),

            reason=" ".join(
                reason_parts
            ),
        ),
    }