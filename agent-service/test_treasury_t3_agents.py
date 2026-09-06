from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.agents import (
    CashPositionAgent,
    FundingRecommendationAgent,
    ObligationsAgent,
    VarianceReconciliationAgent,
)
from demos.remitly_treasury.agent_models import (
    FundingRecommendationType,
    TreasuryAgentStatus,
)
from demos.remitly_treasury.domain import Currency
from demos.remitly_treasury.tools import (
    read_balance_snapshot,
    read_funding_policy,
    read_settlement_snapshot,
)


DATA = Path(__file__).parent / "demos" / "remitly_treasury" / "data"
NOW = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)


def build_results():
    balances = read_balance_snapshot(DATA / "balances.json")
    settlements = read_settlement_snapshot(DATA / "obligations.json")
    policy = read_funding_policy(DATA / "funding_policy.json")

    cash = CashPositionAgent().execute(
        balances=balances,
        reference_time=NOW,
        max_age_seconds=3600,
    )
    obligations = ObligationsAgent().execute(
        settlements=settlements,
    )
    variance = VarianceReconciliationAgent().execute(
        cash=cash,
        obligations=obligations,
    )
    funding = FundingRecommendationAgent().execute(
        cash=cash,
        variance=variance,
        policy=policy,
    )
    return cash, obligations, variance, funding


def test_cash_position_agent_is_bounded_and_traceable():
    cash, _, _, _ = build_results()
    assert cash.agent == "cash_position_agent"
    assert cash.status == TreasuryAgentStatus.alert
    assert cash.positions[Currency.EUR].available == 450000
    assert cash.positions[Currency.EUR].required == 700000
    assert cash.positions[Currency.EUR].variance == -250000
    assert "BAL-EUR-001" in cash.positions[Currency.EUR].evidence_ids


def test_obligations_agent_only_reports_outflows():
    _, obligations, _, _ = build_results()
    assert obligations.agent == "obligations_agent"
    assert obligations.status == TreasuryAgentStatus.completed
    assert obligations.obligations[Currency.EUR].scheduled_outflows == 180000
    assert "SET-EUR-201" in obligations.evidence_ids


def test_variance_agent_reconciles_upstream_results():
    _, _, variance, _ = build_results()
    eur = variance.variances[Currency.EUR]
    assert variance.agent == "variance_agent"
    assert variance.status == TreasuryAgentStatus.alert
    assert eur.projected_requirement == 880000
    assert eur.projected_shortfall == 430000
    assert eur.shortfall_detected is True
    assert set(eur.evidence_ids) == {"BAL-EUR-001", "SET-EUR-201"}


def test_funding_agent_recommends_but_does_not_authorize():
    _, _, _, funding = build_results()
    assert funding.agent == "funding_recommendation_agent"
    assert funding.status == TreasuryAgentStatus.alert

    eur = next(
        item
        for item in funding.recommendations
        if item.destination_currency == Currency.EUR
    )
    assert eur.recommendation == FundingRecommendationType.transfer_required
    assert eur.required_amount == 430000
    assert eur.source_currency == Currency.GBP
    assert eur.source_available_surplus == 200000
    assert eur.source_capacity_sufficient is False
    assert eur.unfunded_amount == 230000
    assert "POL-FUNDING-001" in eur.evidence_ids
    assert "BAL-EUR-001" in eur.evidence_ids
    assert "SET-EUR-201" in eur.evidence_ids
    assert "BAL-GBP-001" in eur.evidence_ids


def test_agents_have_distinct_responsibilities():
    assert CashPositionAgent.name == "cash_position_agent"
    assert ObligationsAgent.name == "obligations_agent"
    assert VarianceReconciliationAgent.name == "variance_agent"
    assert FundingRecommendationAgent.name == "funding_recommendation_agent"


def main():
    test_cash_position_agent_is_bounded_and_traceable()
    test_obligations_agent_only_reports_outflows()
    test_variance_agent_reconciles_upstream_results()
    test_funding_agent_recommends_but_does_not_authorize()
    test_agents_have_distinct_responsibilities()
    print("PASS: T3 Treasury specialist agents are bounded, deterministic, and evidence-producing.")


if __name__ == "__main__":
    main()
