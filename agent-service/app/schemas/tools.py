from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolRiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ToolName(str, Enum):
    memory_lookup = "memory_lookup"
    financial_calculator = "financial_calculator"
    audit_log = "audit_log"


class ToolCallStatus(str, Enum):
    planned = "planned"
    completed = "completed"
    skipped = "skipped"
    failed = "failed"


class ToolDefinition(BaseModel):
    name: ToolName
    description: str
    risk_level: ToolRiskLevel
    requires_confirmation: bool = False
    allowed_in_background: bool = True


class ToolCallRecord(BaseModel):
    tool_name: ToolName
    status: ToolCallStatus
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class FinancialCalculationType(str, Enum):
    growth_rate = "growth_rate"
    margin = "margin"
    delta = "delta"
    percentage_of = "percentage_of"
    cagr = "cagr"


class FinancialCalculatorInput(BaseModel):
    calculation_type: FinancialCalculationType
    current_value: float | None = None
    previous_value: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    beginning_value: float | None = None
    ending_value: float | None = None
    periods: float | None = None


class FinancialCalculatorOutput(BaseModel):
    calculation_type: FinancialCalculationType
    result: float
    result_percent: float | None = None
    explanation: str


class AuditLogInput(BaseModel):
    event_type: str
    agent_name: str = "finance_memory_agent"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogOutput(BaseModel):
    ok: bool
    event_id: str
    event_type: str


class ToolPlan(BaseModel):
    use_memory_lookup: bool = True
    use_financial_calculator: bool = False
    financial_calculator_input: FinancialCalculatorInput | None = None
    reason: str