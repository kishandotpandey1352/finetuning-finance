from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.agents import (
    CashPositionAgent,
    FundingRecommendationAgent,
    ObligationsAgent,
    VarianceReconciliationAgent,
)
from demos.remitly_treasury.domain import Currency
from demos.remitly_treasury.tools import (
    read_balance_snapshot,
    read_funding_policy,
    read_settlement_snapshot,
)
from demos.remitly_treasury.workflow import (
    TREASURY_DAG,
    TreasuryDAGWorkflow,
    TreasuryTaskState,
)


DATA = Path(__file__).parent / "demos" / "remitly_treasury" / "data"
NOW = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)


class TrackingCashAgent(CashPositionAgent):
    def __init__(self, tracker):
        self.tracker = tracker

    def execute(self, **kwargs):
        lock, active, peak = self.tracker
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        try:
            time.sleep(0.08)
            return super().execute(**kwargs)
        finally:
            with lock:
                active[0] -= 1


class TrackingObligationsAgent(ObligationsAgent):
    def __init__(self, tracker):
        self.tracker = tracker

    def execute(self, **kwargs):
        lock, active, peak = self.tracker
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        try:
            time.sleep(0.08)
            return super().execute(**kwargs)
        finally:
            with lock:
                active[0] -= 1


def run_workflow(workflow=None):
    balances = read_balance_snapshot(DATA / "balances.json")
    settlements = read_settlement_snapshot(DATA / "obligations.json")
    policy = read_funding_policy(DATA / "funding_policy.json")

    return asyncio.run(
        (workflow or TreasuryDAGWorkflow()).run(
            balances=balances,
            settlements=settlements,
            policy=policy,
            reference_time=NOW,
            max_balance_age_seconds=3600,
        )
    )


def test_dag_dependencies_are_explicit():
    by_id = {task.task_id: task for task in TREASURY_DAG}
    assert by_id["cash_position"].dependencies == ()
    assert by_id["obligations"].dependencies == ()
    assert by_id["variance"].dependencies == (
        "cash_position",
        "obligations",
    )
    assert by_id["funding_recommendation"].dependencies == ("variance",)


def test_cash_and_obligations_execute_in_parallel():
    lock = threading.Lock()
    active = [0]
    peak = [0]

    workflow = TreasuryDAGWorkflow(
        cash_agent=TrackingCashAgent((lock, active, peak)),
        obligations_agent=TrackingObligationsAgent((lock, active, peak)),
        variance_agent=VarianceReconciliationAgent(),
        funding_agent=FundingRecommendationAgent(),
    )

    result = run_workflow(workflow)
    assert peak[0] == 2
    assert result.task_states["cash_position"] == TreasuryTaskState.completed
    assert result.task_states["obligations"] == TreasuryTaskState.completed


def test_variance_waits_for_both_roots():
    result = run_workflow()
    assert result.started_order.index("variance") > result.started_order.index(
        "cash_position"
    )
    assert result.started_order.index("variance") > result.started_order.index(
        "obligations"
    )

    assert result.completed_order.index("cash_position") < result.completed_order.index(
        "variance"
    )
    assert result.completed_order.index("obligations") < result.completed_order.index(
        "variance"
    )


def test_funding_waits_for_variance():
    result = run_workflow()
    assert result.started_order.index("funding_recommendation") > result.started_order.index(
        "variance"
    )
    assert result.completed_order.index("variance") < result.completed_order.index(
        "funding_recommendation"
    )


def test_expected_shortfall_flows_through_dag():
    result = run_workflow()

    eur = result.variance.variances[Currency.EUR]
    assert eur.projected_shortfall == 430000

    recommendation = next(
        item
        for item in result.funding_recommendation.recommendations
        if item.destination_currency == Currency.EUR
    )
    assert recommendation.required_amount == 430000
    assert recommendation.source_currency == Currency.GBP
    assert recommendation.source_available_surplus == 200000


def test_all_tasks_complete_on_happy_path():
    result = run_workflow()
    assert all(
        state == TreasuryTaskState.completed
        for state in result.task_states.values()
    )


def main():
    test_dag_dependencies_are_explicit()
    test_cash_and_obligations_execute_in_parallel()
    test_variance_waits_for_both_roots()
    test_funding_waits_for_variance()
    test_expected_shortfall_flows_through_dag()
    test_all_tasks_complete_on_happy_path()
    print("PASS: T4 Treasury DAG runs roots in parallel and enforces downstream dependencies.")


if __name__ == "__main__":
    main()
