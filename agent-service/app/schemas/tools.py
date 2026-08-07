from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolRiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ToolName(str, Enum):
    memory_lookup = "memory_lookup"
    financial_calculator = "financial_calculator"
    audit_log = "audit_log"
    document_search = "document_search"

    # Phase 3E
    csv_profile = "csv_profile"


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


# ---------------------------------------------------------
# Financial calculator
# ---------------------------------------------------------


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


# ---------------------------------------------------------
# Audit
# ---------------------------------------------------------


class AuditLogInput(BaseModel):
    event_type: str
    agent_name: str = "finance_memory_agent"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogOutput(BaseModel):
    ok: bool
    event_id: str
    event_type: str


# ---------------------------------------------------------
# Document search
# ---------------------------------------------------------


class DocumentSearchInput(BaseModel):
    query: str = Field(min_length=1)
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=6, ge=1, le=20)


class DocumentSource(BaseModel):
    source_number: int
    document_id: str
    chunk_id: str
    file_name: str
    chunk_index: int
    page_number: int | None = None
    score: float
    snippet: str


class DocumentSearchOutput(BaseModel):
    sources: list[DocumentSource] = Field(default_factory=list)
    source_count: int = 0
    best_score: float = 0.0
    embedding_model: str


# ---------------------------------------------------------
# CSV profile - Phase 3E
# ---------------------------------------------------------


class CsvProfileInput(BaseModel):
    dataset_id: str = Field(min_length=1)


# ---------------------------------------------------------
# Tool plan
# ---------------------------------------------------------


class ToolPlan(BaseModel):
    use_memory_lookup: bool = True

    use_financial_calculator: bool = False
    financial_calculator_input: FinancialCalculatorInput | None = None

    use_document_search: bool = False
    document_search_input: DocumentSearchInput | None = None

    # Phase 3E
    use_csv_profile: bool = False
    csv_profile_input: CsvProfileInput | None = None

    reason: str