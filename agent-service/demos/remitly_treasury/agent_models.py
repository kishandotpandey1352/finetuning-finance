from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from demos.remitly_treasury.domain import Currency


class TreasuryAgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TreasuryAgentStatus(str, Enum):
    completed = "completed"
    alert = "alert"
    blocked = "blocked"
    failed = "failed"


class CashPosition(TreasuryAgentModel):
    currency: Currency
    available: float = Field(ge=0)
    required: float = Field(ge=0)
    variance: float
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class CashPositionResult(TreasuryAgentModel):
    schema_version: Literal["CashPositionResult.v1"] = "CashPositionResult.v1"
    agent: Literal["cash_position_agent"] = "cash_position_agent"
    status: TreasuryAgentStatus
    positions: dict[Currency, CashPosition]
    evidence_ids: list[str] = Field(default_factory=list, max_length=200)


class CurrencyObligation(TreasuryAgentModel):
    currency: Currency
    scheduled_outflows: float = Field(ge=0)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class ObligationsResult(TreasuryAgentModel):
    schema_version: Literal["ObligationsResult.v1"] = "ObligationsResult.v1"
    agent: Literal["obligations_agent"] = "obligations_agent"
    status: TreasuryAgentStatus
    obligations: dict[Currency, CurrencyObligation]
    evidence_ids: list[str] = Field(default_factory=list, max_length=200)


class CurrencyVariance(TreasuryAgentModel):
    currency: Currency
    available: float = Field(ge=0)
    required_liquidity: float = Field(ge=0)
    scheduled_outflows: float = Field(ge=0)
    projected_requirement: float = Field(ge=0)
    projected_shortfall: float = Field(ge=0)
    shortfall_detected: bool
    evidence_ids: list[str] = Field(default_factory=list, max_length=200)


class VarianceResult(TreasuryAgentModel):
    schema_version: Literal["VarianceResult.v1"] = "VarianceResult.v1"
    agent: Literal["variance_agent"] = "variance_agent"
    status: TreasuryAgentStatus
    variances: dict[Currency, CurrencyVariance]
    evidence_ids: list[str] = Field(default_factory=list, max_length=300)


class FundingRecommendationType(str, Enum):
    no_funding_required = "NO_FUNDING_REQUIRED"
    transfer_required = "TRANSFER_REQUIRED"
    funding_source_unavailable = "FUNDING_SOURCE_UNAVAILABLE"


class FundingRecommendation(TreasuryAgentModel):
    destination_currency: Currency
    recommendation: FundingRecommendationType
    required_amount: float = Field(ge=0)
    source_currency: Currency | None = None
    source_available_surplus: float = Field(default=0, ge=0)
    source_capacity_sufficient: bool = False
    unfunded_amount: float = Field(default=0, ge=0)
    reason: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=300)


class FundingRecommendationResult(TreasuryAgentModel):
    schema_version: Literal["FundingRecommendationResult.v1"] = (
        "FundingRecommendationResult.v1"
    )
    agent: Literal["funding_recommendation_agent"] = "funding_recommendation_agent"
    status: TreasuryAgentStatus
    recommendations: list[FundingRecommendation] = Field(
        default_factory=list,
        max_length=20,
    )
    evidence_ids: list[str] = Field(default_factory=list, max_length=500)
