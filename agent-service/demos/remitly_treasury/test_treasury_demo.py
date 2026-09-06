from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.models import RunState
from demos.remitly_treasury.permissions import ToolPermissionDenied, require_tool
from demos.remitly_treasury.workflow import TreasuryWorkflow


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SCENARIOS = HERE / "scenarios"


def now():
    return datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def run(**kwargs):
    wf = TreasuryWorkflow(
        balances_path=kwargs.get("balances", DATA / "balances.json"),
        obligations_path=kwargs.get("obligations", DATA / "obligations.json"),
        policy_path=DATA / "funding_policy.json",
        now_provider=now,
        settlement_fail_attempts=kwargs.get("fail_attempts", 0),
        settlement_max_retries=2,
    )
    return asyncio.run(wf.run("test-run"))


def test_normal_liquidity():
    result = run(
        balances=SCENARIOS / "balances_normal.json",
        obligations=SCENARIOS / "obligations_normal.json",
    )
    assert result.state == RunState.COMPLETED
    assert result.recommendation is not None
    assert result.recommendation.recommendation == "NO_FUNDING_REQUIRED"


def test_eur_shortfall_requires_approval():
    result = run()
    assert result.state == RunState.WAITING_FOR_APPROVAL
    assert result.recommendation is not None
    assert result.recommendation.destination_currency == "EUR"
    assert result.recommendation.proposed_amount == 430000.0
    assert result.recommendation.requires_human_approval is True


def test_stale_data_blocks_workflow():
    result = run(balances=SCENARIOS / "balances_stale.json")
    assert result.state == RunState.BLOCKED
    assert result.error is not None and "STALE_SOURCE_DATA" in result.error
    assert result.metadata["required_action"] == "REFRESH_BALANCE"


def test_tool_failure_is_bounded():
    result = run(fail_attempts=5)
    assert result.state == RunState.FAILED
    assert result.obligations is not None
    assert result.obligations.error == "SETTLEMENT_SERVICE_UNAVAILABLE"
    assert result.obligations.retry_count == 2


def test_unauthorized_tool_is_rejected():
    try:
        require_tool("cash_position_agent", "execute_funding")
    except ToolPermissionDenied as exc:
        assert "TOOL_PERMISSION_DENIED" in str(exc)
    else:
        raise AssertionError("Expected TOOL_PERMISSION_DENIED")


def main():
    tests = [
        test_normal_liquidity,
        test_eur_shortfall_requires_approval,
        test_stale_data_blocks_workflow,
        test_tool_failure_is_bounded,
        test_unauthorized_tool_is_rejected,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: Treasury demo evaluation suite ({len(tests)}/{len(tests)} scenarios).")


if __name__ == "__main__":
    main()
