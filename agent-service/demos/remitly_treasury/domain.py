from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TreasuryModel(BaseModel):
    """Strict base model for all Treasury demo domain objects."""

    model_config = ConfigDict(extra="forbid")


class Currency(str, Enum):
    GBP = "GBP"
    EUR = "EUR"
    USD = "USD"


class EvidenceKind(str, Enum):
    balance = "balance"
    settlement = "settlement"
    policy = "policy"


class TreasuryEvidenceRef(TreasuryModel):
    evidence_id: str = Field(min_length=3, max_length=100)
    kind: EvidenceKind
    source_name: str = Field(min_length=1, max_length=120)
    source_record_id: str = Field(min_length=1, max_length=120)

    @field_validator("evidence_id")
    @classmethod
    def evidence_id_must_be_namespaced(cls, value: str) -> str:
        allowed = ("BAL-", "SET-", "POL-")
        if not value.startswith(allowed):
            raise ValueError(
                "Treasury evidence IDs must start with BAL-, SET-, or POL-."
            )
        return value


class BalanceRecord(TreasuryModel):
    record_id: str = Field(min_length=1, max_length=100)
    evidence_id: str = Field(min_length=3, max_length=100)
    account_id: str = Field(min_length=1, max_length=100)
    currency: Currency
    available_balance: float = Field(ge=0)
    required_liquidity: float = Field(ge=0)
    last_updated: datetime
    source: str = Field(min_length=1, max_length=100)

    @field_validator("evidence_id")
    @classmethod
    def validate_balance_evidence_id(cls, value: str) -> str:
        if not value.startswith("BAL-"):
            raise ValueError("Balance evidence IDs must start with BAL-.")
        return value


class BalanceSnapshot(TreasuryModel):
    schema_version: Literal["TreasuryBalanceSnapshot.v1"] = "TreasuryBalanceSnapshot.v1"
    as_of: datetime
    records: list[BalanceRecord] = Field(min_length=1, max_length=100)


class SettlementDirection(str, Enum):
    outflow = "outflow"
    inflow = "inflow"


class SettlementStatus(str, Enum):
    pending = "pending"
    scheduled = "scheduled"


class SettlementRecord(TreasuryModel):
    record_id: str = Field(min_length=1, max_length=100)
    evidence_id: str = Field(min_length=3, max_length=100)
    settlement_id: str = Field(min_length=1, max_length=100)
    currency: Currency
    amount: float = Field(gt=0)
    direction: SettlementDirection
    status: SettlementStatus
    due_at: datetime
    source: str = Field(min_length=1, max_length=100)

    @field_validator("evidence_id")
    @classmethod
    def validate_settlement_evidence_id(cls, value: str) -> str:
        if not value.startswith("SET-"):
            raise ValueError("Settlement evidence IDs must start with SET-.")
        return value


class SettlementSnapshot(TreasuryModel):
    schema_version: Literal["TreasurySettlementSnapshot.v1"] = (
        "TreasurySettlementSnapshot.v1"
    )
    as_of: datetime
    records: list[SettlementRecord] = Field(default_factory=list, max_length=500)


class FundingCorridor(TreasuryModel):
    source_currency: Currency
    destination_currency: Currency
    enabled: bool = True


class FundingPolicy(TreasuryModel):
    schema_version: Literal["TreasuryFundingPolicy.v1"] = "TreasuryFundingPolicy.v1"
    policy_id: str = Field(min_length=1, max_length=100)
    evidence_id: str = Field(min_length=3, max_length=100)
    minimum_liquidity_buffer: float = Field(ge=0)
    manual_approval_threshold: float = Field(gt=0)
    auto_execution_limit: float = Field(ge=0)
    max_source_utilization_ratio: float = Field(gt=0, le=1)
    available_funding_corridors: list[FundingCorridor] = Field(
        default_factory=list,
        max_length=50,
    )
    source: str = Field(min_length=1, max_length=100)

    @field_validator("evidence_id")
    @classmethod
    def validate_policy_evidence_id(cls, value: str) -> str:
        if not value.startswith("POL-"):
            raise ValueError("Policy evidence IDs must start with POL-.")
        return value

    @field_validator("manual_approval_threshold")
    @classmethod
    def approval_threshold_must_exceed_zero(cls, value: float) -> float:
        return value

    def corridor_enabled(
        self,
        source_currency: Currency,
        destination_currency: Currency,
    ) -> bool:
        return any(
            corridor.enabled
            and corridor.source_currency == source_currency
            and corridor.destination_currency == destination_currency
            for corridor in self.available_funding_corridors
        )


class TreasuryScenario(TreasuryModel):
    schema_version: Literal["TreasuryScenario.v1"] = "TreasuryScenario.v1"
    scenario_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    balances_file: str
    settlements_file: str
    funding_policy_file: str
