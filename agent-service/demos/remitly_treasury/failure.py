from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FailureModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TreasuryRunState(str, Enum):
    completed = "COMPLETED"
    no_action = "NO_ACTION"
    auto_allowed = "AUTO_ALLOWED"
    waiting_for_approval = "WAITING_FOR_APPROVAL"
    blocked = "BLOCKED"
    stale_source_data = "STALE_SOURCE_DATA"
    failed_dependency = "FAILED_DEPENDENCY"
    unauthorized_execution = "UNAUTHORIZED_EXECUTION"


class TreasuryFailureCode(str, Enum):
    stale_source_data = "STALE_SOURCE_DATA"
    settlement_service_unavailable = "SETTLEMENT_SERVICE_UNAVAILABLE"
    failed_dependency = "FAILED_DEPENDENCY"
    unauthorized_execution = "UNAUTHORIZED_EXECUTION"


class TreasuryFailure(FailureModel):
    schema_version: Literal["TreasuryFailure.v1"] = "TreasuryFailure.v1"
    code: TreasuryFailureCode
    message: str = Field(min_length=1, max_length=1000)
    retry_count: int = Field(default=0, ge=0)
    failed_task: str | None = None
    evidence_ids: list[str] = Field(default_factory=list, max_length=200)


class SettlementServiceUnavailableError(RuntimeError):
    """Retryable simulated settlement-provider 503."""


class SimulatedSettlementService:
    """Deterministic failure injector for the interview demo."""

    def __init__(self, *, failures_before_success: int = 0) -> None:
        if failures_before_success < 0:
            raise ValueError("failures_before_success must be >= 0")
        self.failures_before_success = failures_before_success
        self.calls = 0

    def before_read(self) -> None:
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise SettlementServiceUnavailableError(
                "Simulated settlement service HTTP 503."
            )
