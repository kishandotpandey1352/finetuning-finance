from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.failure import (
    TreasuryFailureCode,
    TreasuryRunState,
)
from demos.remitly_treasury.security import (
    TREASURY_AGENT_PERMISSIONS,
    TreasuryAuthorizationError,
    TreasuryCapability,
    TreasuryCapabilityGuard,
    TreasuryDataScope,
)
from demos.remitly_treasury.tools import (
    read_balance_snapshot,
    read_funding_policy,
    read_settlement_snapshot,
)
from demos.remitly_treasury.workflow import TreasuryDAGWorkflow


DATA = Path(__file__).parent / "demos" / "remitly_treasury" / "data"
NOW = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)


def assert_raises_auth(fn):
    try:
        fn()
    except TreasuryAuthorizationError:
        return
    raise AssertionError("Expected TreasuryAuthorizationError")


def test_registry_is_least_privilege():
    cash = TREASURY_AGENT_PERMISSIONS["cash_position_agent"]
    obligations = TREASURY_AGENT_PERMISSIONS["obligations_agent"]
    variance = TREASURY_AGENT_PERMISSIONS["variance_agent"]
    funding = TREASURY_AGENT_PERMISSIONS["funding_recommendation_agent"]
    approval = TREASURY_AGENT_PERMISSIONS["treasury_approval_gate"]

    assert cash.allowed_capabilities == frozenset({
        TreasuryCapability.ANALYZE_CASH_POSITION,
    })
    assert cash.allowed_data_scopes == frozenset({
        TreasuryDataScope.BALANCE_SNAPSHOT,
    })

    assert obligations.allowed_data_scopes == frozenset({
        TreasuryDataScope.SETTLEMENT_SNAPSHOT,
    })

    assert variance.allowed_data_scopes == frozenset({
        TreasuryDataScope.CASH_POSITION_RESULT,
        TreasuryDataScope.OBLIGATIONS_RESULT,
    })

    assert funding.allowed_data_scopes == frozenset({
        TreasuryDataScope.CASH_POSITION_RESULT,
        TreasuryDataScope.VARIANCE_RESULT,
        TreasuryDataScope.FUNDING_POLICY,
    })

    assert approval.allowed_data_scopes == frozenset({
        TreasuryDataScope.FUNDING_RECOMMENDATION_RESULT,
        TreasuryDataScope.FUNDING_POLICY,
    })

    for permission in TREASURY_AGENT_PERMISSIONS.values():
        assert permission.network_access is False
        assert permission.can_execute_funds is False


def test_cash_agent_cannot_read_settlements():
    guard = TreasuryCapabilityGuard()
    assert_raises_auth(
        lambda: guard.authorize(
            agent_name="cash_position_agent",
            capability=TreasuryCapability.ANALYZE_CASH_POSITION,
            data_scopes={
                TreasuryDataScope.BALANCE_SNAPSHOT,
                TreasuryDataScope.SETTLEMENT_SNAPSHOT,
            },
        )
    )


def test_variance_agent_cannot_read_raw_balances():
    guard = TreasuryCapabilityGuard()
    assert_raises_auth(
        lambda: guard.authorize(
            agent_name="variance_agent",
            capability=TreasuryCapability.RECONCILE_VARIANCE,
            data_scopes={
                TreasuryDataScope.CASH_POSITION_RESULT,
                TreasuryDataScope.OBLIGATIONS_RESULT,
                TreasuryDataScope.BALANCE_SNAPSHOT,
            },
        )
    )


def test_funding_agent_cannot_approve():
    guard = TreasuryCapabilityGuard()
    assert_raises_auth(
        lambda: guard.authorize(
            agent_name="funding_recommendation_agent",
            capability=TreasuryCapability.EVALUATE_APPROVAL,
            data_scopes={
                TreasuryDataScope.FUNDING_POLICY,
            },
        )
    )


def test_unknown_agent_is_rejected():
    guard = TreasuryCapabilityGuard()
    assert_raises_auth(
        lambda: guard.authorize(
            agent_name="made_up_agent",
            capability=TreasuryCapability.RECOMMEND_FUNDING,
            data_scopes=set(),
        )
    )


def test_normal_workflow_passes_authorization():
    balances = read_balance_snapshot(DATA / "balances.json")
    settlements = read_settlement_snapshot(DATA / "obligations.json")
    policy = read_funding_policy(DATA / "funding_policy.json")

    result = asyncio.run(
        TreasuryDAGWorkflow().run(
            balances=balances,
            settlements=settlements,
            policy=policy,
            reference_time=NOW,
            max_balance_age_seconds=3600,
        )
    )

    assert result.failure is None
    assert result.run_state in {
        TreasuryRunState.no_action,
        TreasuryRunState.auto_allowed,
        TreasuryRunState.waiting_for_approval,
        TreasuryRunState.blocked,
    }


class DenyFundingGuard(TreasuryCapabilityGuard):
    def authorize(self, *, agent_name, capability, data_scopes):
        if capability == TreasuryCapability.RECOMMEND_FUNDING:
            raise TreasuryAuthorizationError(
                "Injected test denial for funding recommendation."
            )
        return super().authorize(
            agent_name=agent_name,
            capability=capability,
            data_scopes=data_scopes,
        )


def test_runtime_propagates_unauthorized_state():
    balances = read_balance_snapshot(DATA / "balances.json")
    settlements = read_settlement_snapshot(DATA / "obligations.json")
    policy = read_funding_policy(DATA / "funding_policy.json")

    result = asyncio.run(
        TreasuryDAGWorkflow(
            capability_guard=DenyFundingGuard(),
        ).run(
            balances=balances,
            settlements=settlements,
            policy=policy,
            reference_time=NOW,
            max_balance_age_seconds=3600,
        )
    )

    assert result.run_state == TreasuryRunState.unauthorized_execution
    assert result.failure is not None
    assert result.failure.code == TreasuryFailureCode.unauthorized_execution
    assert result.failure.failed_task == "funding_recommendation"
    assert result.funding_recommendation is None
    assert result.approval is None


def main():
    test_registry_is_least_privilege()
    test_cash_agent_cannot_read_settlements()
    test_variance_agent_cannot_read_raw_balances()
    test_funding_agent_cannot_approve()
    test_unknown_agent_is_rejected()
    test_normal_workflow_passes_authorization()
    test_runtime_propagates_unauthorized_state()
    print(
        "PASS: T7 Treasury least-privilege registry blocks unauthorized "
        "capabilities/data scopes and propagates authorization failures."
    )


if __name__ == "__main__":
    main()
