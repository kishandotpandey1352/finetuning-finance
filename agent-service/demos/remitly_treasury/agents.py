from __future__ import annotations

from datetime import datetime

from demos.remitly_treasury.domain import (
    BalanceSnapshot,
    Currency,
    FundingPolicy,
    SettlementSnapshot,
)
from demos.remitly_treasury.agent_models import (
    CashPosition,
    CashPositionResult,
    CurrencyObligation,
    CurrencyVariance,
    FundingRecommendation,
    FundingRecommendationResult,
    FundingRecommendationType,
    ObligationsResult,
    TreasuryAgentStatus,
    VarianceResult,
)
from demos.remitly_treasury.tools import (
    available_balances_by_currency,
    deterministic_base_variance,
    deterministic_projected_requirement,
    deterministic_projected_shortfall,
    deterministic_surplus,
    required_liquidity_by_currency,
    scheduled_outflows_by_currency,
    validate_balance_freshness,
)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class CashPositionAgent:
    """Read-only specialist for current liquidity positions.

    Allowed responsibilities:
    - validate balance freshness,
    - aggregate balances/requirements,
    - calculate base variance with deterministic T2 arithmetic.

    It does not read settlements, recommend funding, or execute transfers.
    """

    name = "cash_position_agent"

    def execute(
        self,
        *,
        balances: BalanceSnapshot,
        reference_time: datetime,
        max_age_seconds: int,
    ) -> CashPositionResult:
        validate_balance_freshness(
            balances,
            reference_time=reference_time,
            max_age_seconds=max_age_seconds,
        )

        available = available_balances_by_currency(balances)
        required = required_liquidity_by_currency(balances)

        positions: dict[Currency, CashPosition] = {}
        all_evidence: list[str] = []

        currencies = sorted(
            set(available) | set(required),
            key=lambda item: item.value,
        )
        for currency in currencies:
            evidence_ids = [
                record.evidence_id
                for record in balances.records
                if record.currency == currency
            ]
            all_evidence.extend(evidence_ids)

            available_value = float(available.get(currency, 0.0))
            required_value = float(required.get(currency, 0.0))
            positions[currency] = CashPosition(
                currency=currency,
                available=available_value,
                required=required_value,
                variance=deterministic_base_variance(
                    available_balance=available_value,
                    required_liquidity=required_value,
                ),
                evidence_ids=evidence_ids,
            )

        status = (
            TreasuryAgentStatus.alert
            if any(position.variance < 0 for position in positions.values())
            else TreasuryAgentStatus.completed
        )
        return CashPositionResult(
            status=status,
            positions=positions,
            evidence_ids=_unique(all_evidence),
        )


class ObligationsAgent:
    """Read-only specialist for upcoming settlement outflows.

    It does not read balances, calculate liquidity shortfall, recommend funding,
    or perform any execution.
    """

    name = "obligations_agent"

    def execute(
        self,
        *,
        settlements: SettlementSnapshot,
        through: datetime | None = None,
    ) -> ObligationsResult:
        totals = scheduled_outflows_by_currency(
            settlements,
            through=through,
        )

        obligations: dict[Currency, CurrencyObligation] = {}
        all_evidence: list[str] = []

        for currency in sorted(totals, key=lambda item: item.value):
            evidence_ids = [
                record.evidence_id
                for record in settlements.records
                if record.currency == currency
                and record.direction.value == "outflow"
                and record.status.value in {"pending", "scheduled"}
                and (through is None or record.due_at <= through)
            ]
            all_evidence.extend(evidence_ids)
            obligations[currency] = CurrencyObligation(
                currency=currency,
                scheduled_outflows=float(totals[currency]),
                evidence_ids=evidence_ids,
            )

        return ObligationsResult(
            status=TreasuryAgentStatus.completed,
            obligations=obligations,
            evidence_ids=_unique(all_evidence),
        )


class VarianceReconciliationAgent:
    """Pure reconciliation specialist.

    Consumes only outputs from CashPositionAgent and ObligationsAgent.
    It does not read source files or make funding decisions.
    """

    name = "variance_agent"

    def execute(
        self,
        *,
        cash: CashPositionResult,
        obligations: ObligationsResult,
    ) -> VarianceResult:
        currencies = sorted(
            set(cash.positions) | set(obligations.obligations),
            key=lambda item: item.value,
        )

        variances: dict[Currency, CurrencyVariance] = {}
        all_evidence: list[str] = []

        for currency in currencies:
            cash_position = cash.positions.get(currency)
            obligation = obligations.obligations.get(currency)

            available = cash_position.available if cash_position else 0.0
            required = cash_position.required if cash_position else 0.0
            outflows = obligation.scheduled_outflows if obligation else 0.0

            evidence_ids: list[str] = []
            if cash_position:
                evidence_ids.extend(cash_position.evidence_ids)
            if obligation:
                evidence_ids.extend(obligation.evidence_ids)
            evidence_ids = _unique(evidence_ids)
            all_evidence.extend(evidence_ids)

            projected_requirement = deterministic_projected_requirement(
                required_liquidity=required,
                scheduled_outflows=outflows,
            )
            shortfall = deterministic_projected_shortfall(
                available_balance=available,
                required_liquidity=required,
                scheduled_outflows=outflows,
            )

            variances[currency] = CurrencyVariance(
                currency=currency,
                available=available,
                required_liquidity=required,
                scheduled_outflows=outflows,
                projected_requirement=projected_requirement,
                projected_shortfall=shortfall,
                shortfall_detected=shortfall > 0,
                evidence_ids=evidence_ids,
            )

        return VarianceResult(
            status=(
                TreasuryAgentStatus.alert
                if any(v.shortfall_detected for v in variances.values())
                else TreasuryAgentStatus.completed
            ),
            variances=variances,
            evidence_ids=_unique(all_evidence),
        )


class FundingRecommendationAgent:
    """Recommendation-only specialist.

    It may identify an enabled funding corridor and state the required amount.
    It cannot approve or execute a transfer. T5 owns approval policy.
    """

    name = "funding_recommendation_agent"

    def execute(
        self,
        *,
        cash: CashPositionResult,
        variance: VarianceResult,
        policy: FundingPolicy,
    ) -> FundingRecommendationResult:
        recommendations: list[FundingRecommendation] = []
        all_evidence: list[str] = [policy.evidence_id]

        shortfalls = [
            value
            for value in variance.variances.values()
            if value.shortfall_detected
        ]

        if not shortfalls:
            return FundingRecommendationResult(
                status=TreasuryAgentStatus.completed,
                recommendations=[],
                evidence_ids=_unique(variance.evidence_ids + [policy.evidence_id]),
            )

        for shortfall in sorted(shortfalls, key=lambda item: item.currency.value):
            destination = shortfall.currency
            required_amount = float(shortfall.projected_shortfall)

            candidates: list[tuple[float, Currency, list[str]]] = []
            for source_currency, position in cash.positions.items():
                if source_currency == destination:
                    continue
                if not policy.corridor_enabled(source_currency, destination):
                    continue

                surplus = deterministic_surplus(
                    available_balance=position.available,
                    required_liquidity=position.required,
                    minimum_buffer=policy.minimum_liquidity_buffer,
                )
                if surplus <= 0:
                    continue
                candidates.append(
                    (surplus, source_currency, position.evidence_ids)
                )

            evidence_ids = list(shortfall.evidence_ids)
            evidence_ids.append(policy.evidence_id)

            if not candidates:
                recommendation = FundingRecommendation(
                    destination_currency=destination,
                    recommendation=FundingRecommendationType.funding_source_unavailable,
                    required_amount=required_amount,
                    source_currency=None,
                    source_available_surplus=0.0,
                    source_capacity_sufficient=False,
                    unfunded_amount=required_amount,
                    reason=(
                        f"{destination.value} has a projected shortfall of "
                        f"{required_amount:.2f}, but no enabled funding corridor "
                        "has positive source surplus."
                    ),
                    evidence_ids=_unique(evidence_ids),
                )
            else:
                candidates.sort(key=lambda item: item[0], reverse=True)
                source_surplus, source_currency, source_evidence = candidates[0]
                evidence_ids.extend(source_evidence)

                capacity_sufficient = source_surplus >= required_amount
                unfunded = max(0.0, required_amount - source_surplus)

                recommendation = FundingRecommendation(
                    destination_currency=destination,
                    recommendation=FundingRecommendationType.transfer_required,
                    required_amount=required_amount,
                    source_currency=source_currency,
                    source_available_surplus=source_surplus,
                    source_capacity_sufficient=capacity_sufficient,
                    unfunded_amount=unfunded,
                    reason=(
                        f"{destination.value} requires {required_amount:.2f} of "
                        f"funding based on projected liquidity. "
                        f"{source_currency.value}->{destination.value} is enabled. "
                        f"Source surplus after required liquidity and policy buffer "
                        f"is {source_surplus:.2f}."
                    ),
                    evidence_ids=_unique(evidence_ids),
                )

            all_evidence.extend(recommendation.evidence_ids)
            recommendations.append(recommendation)

        return FundingRecommendationResult(
            status=TreasuryAgentStatus.alert,
            recommendations=recommendations,
            evidence_ids=_unique(all_evidence),
        )
