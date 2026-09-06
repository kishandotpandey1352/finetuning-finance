from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RunState(str, Enum):
    COMPLETED = "COMPLETED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class BalanceRecord:
    currency: str
    available_balance: float
    required_liquidity: float
    last_updated: datetime
    evidence_id: str


@dataclass(frozen=True)
class SettlementObligation:
    settlement_id: str
    currency: str
    amount: float
    due_at: datetime
    status: str
    evidence_id: str


@dataclass(frozen=True)
class FundingPolicy:
    minimum_liquidity_buffer: float
    auto_execution_threshold: float
    manual_approval_threshold: float
    max_balance_age_hours: float
    available_funding_corridors: tuple[str, ...]


@dataclass
class CashPositionResult:
    status: str
    positions: dict[str, dict[str, float]]
    evidence_ids: list[str]
    error: str | None = None


@dataclass
class ObligationResult:
    status: str
    obligations: dict[str, float]
    evidence_ids: list[str]
    retry_count: int = 0
    error: str | None = None


@dataclass
class VarianceResult:
    status: str
    by_currency: dict[str, dict[str, float | bool]]
    evidence_ids: list[str]
    error: str | None = None


@dataclass
class FundingRecommendation:
    status: str
    recommendation: str
    source_currency: str | None
    destination_currency: str | None
    proposed_amount: float
    reason: str
    requires_human_approval: bool
    evidence_ids: list[str]


@dataclass
class TraceEvent:
    timestamp: datetime
    component: str
    status: str
    message: str


@dataclass
class TreasuryRunResult:
    run_id: str
    state: RunState
    cash_position: CashPositionResult | None = None
    obligations: ObligationResult | None = None
    variance: VarianceResult | None = None
    recommendation: FundingRecommendation | None = None
    trace: list[TraceEvent] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
