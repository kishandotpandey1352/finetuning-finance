from app.schemas.tools import (
    AuditLogInput,
    FinancialCalculatorInput,
    ToolDefinition,
    ToolName,
    ToolRiskLevel,
)
from app.tools.audit import audit_log_tool
from app.tools.financial_calculator import financial_calculator_tool
from app.tools.memory import memory_lookup_tool


TOOL_REGISTRY: dict[ToolName, ToolDefinition] = {
    ToolName.memory_lookup: ToolDefinition(
        name=ToolName.memory_lookup,
        description="Read confirmed user preference memory.",
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),
    ToolName.financial_calculator: ToolDefinition(
        name=ToolName.financial_calculator,
        description="Calculate growth, margin, delta, percentage, or CAGR.",
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),
    ToolName.audit_log: ToolDefinition(
        name=ToolName.audit_log,
        description="Write an agent audit event.",
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),
}


def list_tool_definitions() -> list[ToolDefinition]:
    return list(TOOL_REGISTRY.values())


def run_memory_lookup(user_id: str) -> dict:
    return memory_lookup_tool(user_id)


def run_financial_calculator(tool_input: FinancialCalculatorInput) -> dict:
    return financial_calculator_tool(tool_input).model_dump(mode="json")


def run_audit_log(
    user_id: str,
    request_id: str,
    tool_input: AuditLogInput,
) -> dict:
    return audit_log_tool(user_id, request_id, tool_input).model_dump(mode="json")