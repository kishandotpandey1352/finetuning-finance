from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from demos.remitly_treasury.agent_models import (
    FundingRecommendation,
    FundingRecommendationResult,
    FundingRecommendationType,
)
from demos.remitly_treasury.domain import FundingPolicy


class ApprovalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApprovalDecision(str, Enum):
    no_action = "NO_ACTION"
    auto_allowed = "AUTO_ALLOWED"
    waiting_for_approval = "WAITING_FOR_APPROVAL"
    blocked = "BLOCKED"


class FundingApprovalRecord(ApprovalModel):
    destination_currency: str
    source_currency: str | None = None
    required_amount: float = Field(ge=0)
    decision: ApprovalDecision
    reason: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=300)


class ApprovalGateResult(ApprovalModel):
    schema_version: Literal["ApprovalGateResult.v1"] = "ApprovalGateResult.v1"
    workflow_state: ApprovalDecision
    decisions: list[FundingApprovalRecord] = Field(
        default_factory=list,
        max_length=50,
    )
    evidence_ids: list[str] = Field(default_factory=list, max_length=500)


class TreasuryApprovalGate:
    """Deterministic Treasury approval policy.

    The gate does not call an LLM, modify recommendation amounts,
    or execute a funding action.
    """

    name = "treasury_approval_gate"

    def evaluate(
        self,
        *,
        recommendation_result: FundingRecommendationResult,
        policy: FundingPolicy,
    ) -> ApprovalGateResult:
        decisions: list[FundingApprovalRecord] = []
        all_evidence: list[str] = [policy.evidence_id]

        if not recommendation_result.recommendations:
            return ApprovalGateResult(
                workflow_state=ApprovalDecision.no_action,
                decisions=[],
                evidence_ids=list(
                    dict.fromkeys(
                        recommendation_result.evidence_ids
                        + [policy.evidence_id]
                    )
                ),
            )

        for item in recommendation_result.recommendations:
            decision, reason = self._evaluate_one(
                recommendation=item,
                policy=policy,
            )
            evidence_ids = list(
                dict.fromkeys(item.evidence_ids + [policy.evidence_id])
            )
            all_evidence.extend(evidence_ids)

            decisions.append(
                FundingApprovalRecord(
                    destination_currency=item.destination_currency.value,
                    source_currency=(
                        item.source_currency.value
                        if item.source_currency is not None
                        else None
                    ),
                    required_amount=float(item.required_amount),
                    decision=decision,
                    reason=reason,
                    evidence_ids=evidence_ids,
                )
            )

        if any(d.decision == ApprovalDecision.blocked for d in decisions):
            workflow_state = ApprovalDecision.blocked
        elif any(
            d.decision == ApprovalDecision.waiting_for_approval
            for d in decisions
        ):
            workflow_state = ApprovalDecision.waiting_for_approval
        elif any(
            d.decision == ApprovalDecision.auto_allowed
            for d in decisions
        ):
            workflow_state = ApprovalDecision.auto_allowed
        else:
            workflow_state = ApprovalDecision.no_action

        return ApprovalGateResult(
            workflow_state=workflow_state,
            decisions=decisions,
            evidence_ids=list(dict.fromkeys(all_evidence)),
        )

    def _evaluate_one(
        self,
        *,
        recommendation: FundingRecommendation,
        policy: FundingPolicy,
    ) -> tuple[ApprovalDecision, str]:
        if (
            recommendation.recommendation
            == FundingRecommendationType.no_funding_required
        ):
            return ApprovalDecision.no_action, "No funding action is required."

        if (
            recommendation.recommendation
            == FundingRecommendationType.funding_source_unavailable
        ):
            return (
                ApprovalDecision.blocked,
                "Funding is required but no permitted source is available.",
            )

        if recommendation.source_currency is None:
            return (
                ApprovalDecision.blocked,
                "Funding recommendation has no source currency.",
            )

        if not policy.corridor_enabled(
            recommendation.source_currency,
            recommendation.destination_currency,
        ):
            return (
                ApprovalDecision.blocked,
                "Recommended funding corridor is not permitted by policy.",
            )

        if not recommendation.source_capacity_sufficient:
            return (
                ApprovalDecision.blocked,
                "Recommended source does not have sufficient policy-protected surplus.",
            )

        amount = float(recommendation.required_amount)

        if amount > float(policy.manual_approval_threshold):
            return (
                ApprovalDecision.waiting_for_approval,
                (
                    f"Funding amount {amount:.2f} exceeds the manual approval "
                    f"threshold {policy.manual_approval_threshold:.2f}."
                ),
            )

        if amount <= float(policy.auto_execution_limit):
            return (
                ApprovalDecision.auto_allowed,
                (
                    f"Funding amount {amount:.2f} is within the auto-allowed "
                    f"limit {policy.auto_execution_limit:.2f}."
                ),
            )

        return (
            ApprovalDecision.waiting_for_approval,
            (
                f"Funding amount {amount:.2f} exceeds the auto-allowed limit "
                f"{policy.auto_execution_limit:.2f}; human approval is required."
            ),
        )
