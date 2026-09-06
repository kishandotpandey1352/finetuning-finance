from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.failure import (
    SimulatedSettlementService,
    TreasuryFailureCode,
    TreasuryRunState,
)
from demos.remitly_treasury.tools import (
    read_balance_snapshot,
    read_funding_policy,
    read_settlement_snapshot,
)
from demos.remitly_treasury.workflow import (
    TreasuryDAGWorkflow,
    TreasuryTaskState,
)


DATA = Path(__file__).parent / "demos" / "remitly_treasury" / "data"
NOW = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)


def inputs():
    return (
        read_balance_snapshot(DATA / "balances.json"),
        read_settlement_snapshot(DATA / "obligations.json"),
        read_funding_policy(DATA / "funding_policy.json"),
    )


def run(workflow, *, reference_time=NOW, max_age=3600):
    balances, settlements, policy = inputs()
    return asyncio.run(
        workflow.run(
            balances=balances,
            settlements=settlements,
            policy=policy,
            reference_time=reference_time,
            max_balance_age_seconds=max_age,
        )
    )


def test_stale_balances_block_workflow():
    workflow = TreasuryDAGWorkflow()
    stale_time = datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc)
    result = run(workflow, reference_time=stale_time, max_age=3600)

    assert result.run_state == TreasuryRunState.stale_source_data
    assert result.failure is not None
    assert result.failure.code == TreasuryFailureCode.stale_source_data
    assert result.variance is None
    assert result.funding_recommendation is None
    assert result.approval is None
    assert result.task_states["variance"] == TreasuryTaskState.skipped
    assert result.task_states["funding_recommendation"] == TreasuryTaskState.skipped
    assert result.task_states["approval_gate"] == TreasuryTaskState.skipped


def test_settlement_503_retries_then_succeeds():
    service = SimulatedSettlementService(failures_before_success=2)
    workflow = TreasuryDAGWorkflow(
        settlement_service=service,
        settlement_retry_limit=2,
    )
    result = run(workflow)

    assert service.calls == 3
    assert result.retry_counts["obligations"] == 2
    assert result.obligations is not None
    assert result.variance is not None
    assert result.failure is None


def test_settlement_503_exhausts_retry_budget():
    service = SimulatedSettlementService(failures_before_success=5)
    workflow = TreasuryDAGWorkflow(
        settlement_service=service,
        settlement_retry_limit=2,
    )
    result = run(workflow)

    assert service.calls == 3
    assert result.run_state == TreasuryRunState.failed_dependency
    assert result.retry_counts["obligations"] == 2
    assert result.failure is not None
    assert result.failure.code == TreasuryFailureCode.failed_dependency
    assert result.variance is None
    assert result.funding_recommendation is None
    assert result.approval is None
    assert result.task_states["obligations"] == TreasuryTaskState.failed
    assert result.task_states["variance"] == TreasuryTaskState.skipped
    assert result.task_states["funding_recommendation"] == TreasuryTaskState.skipped
    assert result.task_states["approval_gate"] == TreasuryTaskState.skipped


def test_failed_dependency_does_not_invent_values():
    service = SimulatedSettlementService(failures_before_success=99)
    workflow = TreasuryDAGWorkflow(
        settlement_service=service,
        settlement_retry_limit=1,
    )
    result = run(workflow)

    assert result.obligations is None
    assert result.variance is None
    assert result.funding_recommendation is None
    assert result.approval is None


def main():
    test_stale_balances_block_workflow()
    test_settlement_503_retries_then_succeeds()
    test_settlement_503_exhausts_retry_budget()
    test_failed_dependency_does_not_invent_values()
    print("PASS: T6 Treasury failure handling blocks stale data, bounds settlement retries, and propagates failed dependencies.")


if __name__ == "__main__":
    main()
