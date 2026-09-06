from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.domain import Currency
from demos.remitly_treasury.failure import (
    SimulatedSettlementService,
    TreasuryRunState,
)
from demos.remitly_treasury.security import (
    TreasuryAuthorizationError,
    TreasuryCapability,
    TreasuryCapabilityGuard,
)
from demos.remitly_treasury.tools import (
    read_balance_snapshot,
    read_funding_policy,
    read_settlement_snapshot,
)
from demos.remitly_treasury.trace import (
    TreasuryTraceEvent,
    build_execution_trace,
)
from demos.remitly_treasury.workflow import TreasuryDAGWorkflow


DATA = Path(__file__).parent / "data"
REFERENCE_TIME = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class TreasuryScenarioResult:
    name: str
    description: str
    expected_state: TreasuryRunState
    actual_state: TreasuryRunState
    passed: bool
    trace: tuple[TreasuryTraceEvent, ...]


class DenyFundingCapabilityGuard(TreasuryCapabilityGuard):
    """T8 test-only guard used to prove least-privilege rejection."""

    def authorize(self, *, agent_name, capability, data_scopes):
        if capability == TreasuryCapability.RECOMMEND_FUNDING:
            raise TreasuryAuthorizationError(
                "T8 unauthorized-tool scenario denied funding recommendation capability."
            )
        return super().authorize(
            agent_name=agent_name,
            capability=capability,
            data_scopes=data_scopes,
        )


def _base_inputs():
    return (
        read_balance_snapshot(DATA / "balances.json"),
        read_settlement_snapshot(DATA / "obligations.json"),
        read_funding_policy(DATA / "funding_policy.json"),
    )


def _with_available_balance(snapshot, currency: Currency, amount: float):
    records = []
    changed = False
    for record in snapshot.records:
        if record.currency == currency:
            records.append(record.model_copy(update={"available_balance": amount}))
            changed = True
        else:
            records.append(record)
    if not changed:
        raise AssertionError(f"No balance record found for {currency.value}")
    return snapshot.model_copy(update={"records": records})


async def _run_scenario(name: str):
    balances, settlements, policy = _base_inputs()
    reference_time = REFERENCE_TIME
    workflow = TreasuryDAGWorkflow()
    expected = TreasuryRunState.no_action
    description = ""

    if name == "normal":
        description = "All currencies remain sufficiently funded after scheduled outflows."
        balances = _with_available_balance(
            balances,
            Currency.EUR,
            1_000_000,
        )
        expected = TreasuryRunState.no_action

    elif name == "shortfall":
        description = (
            "EUR has a 430k projected shortfall; GBP has enough source capacity, "
            "so the high-value recommendation must wait for human approval."
        )
        balances = _with_available_balance(
            balances,
            Currency.GBP,
            1_600_000,
        )
        expected = TreasuryRunState.waiting_for_approval

    elif name == "stale":
        description = "Balance data is outside the allowed freshness window."
        reference_time = datetime(
            2026, 9, 7, 8, 0, tzinfo=timezone.utc
        )
        expected = TreasuryRunState.stale_source_data

    elif name == "tool_failure":
        description = (
            "Settlement service keeps returning 503 beyond the bounded retry budget."
        )
        workflow = TreasuryDAGWorkflow(
            settlement_service=SimulatedSettlementService(
                failures_before_success=99
            ),
            settlement_retry_limit=2,
        )
        expected = TreasuryRunState.failed_dependency

    elif name == "unauthorized_tool":
        description = (
            "Funding recommendation capability is explicitly denied by the "
            "server-owned capability guard."
        )
        workflow = TreasuryDAGWorkflow(
            capability_guard=DenyFundingCapabilityGuard()
        )
        expected = TreasuryRunState.unauthorized_execution

    else:
        raise ValueError(f"Unknown Treasury evaluation scenario: {name}")

    result = await workflow.run(
        balances=balances,
        settlements=settlements,
        policy=policy,
        reference_time=reference_time,
        max_balance_age_seconds=3600,
    )

    trace = build_execution_trace(
        result,
        scenario_name=name,
    )

    return TreasuryScenarioResult(
        name=name,
        description=description,
        expected_state=expected,
        actual_state=result.run_state,
        passed=result.run_state == expected,
        trace=tuple(trace),
    )


SCENARIO_NAMES = (
    "normal",
    "shortfall",
    "stale",
    "tool_failure",
    "unauthorized_tool",
)


async def run_all_scenarios() -> list[TreasuryScenarioResult]:
    results = []
    for name in SCENARIO_NAMES:
        results.append(await _run_scenario(name))
    return results


def run_all_scenarios_sync() -> list[TreasuryScenarioResult]:
    return asyncio.run(run_all_scenarios())
