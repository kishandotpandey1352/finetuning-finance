from __future__ import annotations

import asyncio
from collections import defaultdict

from .models import (
    CashPositionResult,
    FundingPolicy,
    FundingRecommendation,
    ObligationResult,
    VarianceResult,
)
from .permissions import require_tool
from .tools import (
    MockBalanceTool,
    MockSettlementTool,
    SettlementServiceUnavailable,
    StaleSourceData,
)


class CashPositionAgent:
    name = "cash_position_agent"

    def __init__(self, tool: MockBalanceTool, policy: FundingPolicy):
        self.tool = tool
        self.policy = policy

    async def execute(self) -> CashPositionResult:
        records = await asyncio.to_thread(
            self.tool.read,
            agent_name=self.name,
            max_age_hours=self.policy.max_balance_age_hours,
        )
        positions: dict[str, dict[str, float]] = {}
        evidence_ids: list[str] = []
        for record in records:
            base_variance = record.available_balance - record.required_liquidity
            positions[record.currency] = {
                "available": record.available_balance,
                "required": record.required_liquidity,
                "base_variance": base_variance,
            }
            evidence_ids.append(record.evidence_id)
        return CashPositionResult("success", positions, evidence_ids)


class ObligationsAgent:
    name = "obligations_agent"

    def __init__(self, tool: MockSettlementTool, max_retries: int = 2):
        self.tool = tool
        self.max_retries = max_retries

    async def execute(self) -> ObligationResult:
        attempts = 0
        while True:
            try:
                records = await asyncio.to_thread(
                    self.tool.read, agent_name=self.name
                )
                grouped: dict[str, float] = defaultdict(float)
                evidence_ids: list[str] = []
                for record in records:
                    grouped[record.currency] += record.amount
                    evidence_ids.append(record.evidence_id)
                return ObligationResult(
                    status="success",
                    obligations=dict(grouped),
                    evidence_ids=evidence_ids,
                    retry_count=attempts,
                )
            except SettlementServiceUnavailable as exc:
                if attempts >= self.max_retries:
                    return ObligationResult(
                        status="failed",
                        obligations={},
                        evidence_ids=[],
                        retry_count=attempts,
                        error=str(exc),
                    )
                attempts += 1
                await asyncio.sleep(0)


class VarianceAgent:
    name = "variance_agent"

    async def execute(
        self,
        cash: CashPositionResult,
        obligations: ObligationResult,
    ) -> VarianceResult:
        if cash.status != "success" or obligations.status != "success":
            return VarianceResult(
                status="failed_dependency",
                by_currency={},
                evidence_ids=cash.evidence_ids + obligations.evidence_ids,
                error="FAILED_DEPENDENCY",
            )

        currencies = set(cash.positions) | set(obligations.obligations)
        by_currency: dict[str, dict[str, float | bool]] = {}
        for currency in sorted(currencies):
            position = cash.positions.get(
                currency,
                {"available": 0.0, "required": 0.0, "base_variance": 0.0},
            )
            outflows = obligations.obligations.get(currency, 0.0)
            projected_required = float(position["required"]) + outflows
            projected_shortfall = max(
                0.0, projected_required - float(position["available"])
            )
            projected_surplus = max(
                0.0, float(position["available"]) - projected_required
            )
            by_currency[currency] = {
                "available": float(position["available"]),
                "required_liquidity": float(position["required"]),
                "upcoming_outflows": outflows,
                "projected_required": projected_required,
                "projected_shortfall": projected_shortfall,
                "projected_surplus": projected_surplus,
                "shortfall_detected": projected_shortfall > 0,
            }
        return VarianceResult(
            status="success",
            by_currency=by_currency,
            evidence_ids=list(dict.fromkeys(cash.evidence_ids + obligations.evidence_ids)),
        )


class FundingRecommendationAgent:
    name = "funding_recommendation_agent"

    async def execute(
        self,
        variance: VarianceResult,
        policy: FundingPolicy,
    ) -> FundingRecommendation:
        require_tool(self.name, "create_recommendation")
        if variance.status != "success":
            return FundingRecommendation(
                status="blocked",
                recommendation="NO_RECOMMENDATION",
                source_currency=None,
                destination_currency=None,
                proposed_amount=0.0,
                reason="Reliable variance evidence is unavailable.",
                requires_human_approval=False,
                evidence_ids=variance.evidence_ids,
            )

        deficits = [
            (currency, float(values["projected_shortfall"]))
            for currency, values in variance.by_currency.items()
            if float(values["projected_shortfall"]) > 0
        ]
        if not deficits:
            return FundingRecommendation(
                status="success",
                recommendation="NO_FUNDING_REQUIRED",
                source_currency=None,
                destination_currency=None,
                proposed_amount=0.0,
                reason="Projected liquidity remains above required levels.",
                requires_human_approval=False,
                evidence_ids=variance.evidence_ids,
            )

        destination, shortfall = max(deficits, key=lambda item: item[1])
        sources = [
            (currency, float(values["projected_surplus"]))
            for currency, values in variance.by_currency.items()
            if currency != destination and float(values["projected_surplus"]) > 0
        ]
        if not sources:
            return FundingRecommendation(
                status="blocked",
                recommendation="EXTERNAL_FUNDING_REQUIRED",
                source_currency=None,
                destination_currency=destination,
                proposed_amount=shortfall,
                reason=f"{destination} has a projected shortfall but no internal surplus is available.",
                requires_human_approval=True,
                evidence_ids=variance.evidence_ids,
            )

        source, surplus = max(sources, key=lambda item: item[1])
        corridor = f"{source}_{destination}"
        if corridor not in policy.available_funding_corridors:
            return FundingRecommendation(
                status="blocked",
                recommendation="CORRIDOR_NOT_ALLOWED",
                source_currency=source,
                destination_currency=destination,
                proposed_amount=min(shortfall, surplus),
                reason=f"Funding corridor {corridor} is not permitted by policy.",
                requires_human_approval=True,
                evidence_ids=variance.evidence_ids,
            )

        proposed_amount = min(shortfall, surplus)
        return FundingRecommendation(
            status="alert" if proposed_amount > 0 else "success",
            recommendation="TRANSFER_REQUIRED",
            source_currency=source,
            destination_currency=destination,
            proposed_amount=proposed_amount,
            reason=(
                f"Projected {destination} liquidity is below required levels after upcoming settlements."
            ),
            requires_human_approval=(
                proposed_amount > policy.manual_approval_threshold
            ),
            evidence_ids=variance.evidence_ids,
        )
