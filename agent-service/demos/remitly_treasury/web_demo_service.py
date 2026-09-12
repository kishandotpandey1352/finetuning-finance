from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from demos.remitly_treasury.domain import Currency
from demos.remitly_treasury.failure import (
    SimulatedSettlementService,
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
from demos.remitly_treasury.trace import build_execution_trace
from demos.remitly_treasury.workflow import TreasuryDAGWorkflow


DATA = Path(__file__).parent / "data"
REFERENCE_TIME = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)

SUPPORTED_SCENARIOS = (
    "normal",
    "shortfall",
    "stale",
    "tool_failure",
    "unauthorized_tool",
)


class DenyFundingCapabilityGuard(TreasuryCapabilityGuard):
    """T10 demo-only denial used for the least-privilege scenario."""

    def authorize(self, *, agent_name, capability, data_scopes):
        if capability == TreasuryCapability.RECOMMEND_FUNDING:
            raise TreasuryAuthorizationError(
                "T10 unauthorized-tool scenario denied funding recommendation capability."
            )
        return super().authorize(
            agent_name=agent_name,
            capability=capability,
            data_scopes=data_scopes,
        )


def _with_available_balance(snapshot, currency: Currency, amount: float):
    records = []
    changed = False
    for record in snapshot.records:
        if record.currency == currency:
            records.append(
                record.model_copy(update={"available_balance": amount})
            )
            changed = True
        else:
            records.append(record)

    if not changed:
        raise ValueError(f"No balance record found for {currency.value}")

    return snapshot.model_copy(update={"records": records})


CommentaryGenerator = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


async def run_web_demo_scenario(
    name: str,
    *,
    commentary_generator: CommentaryGenerator | None = None,
) -> dict:
    if name not in SUPPORTED_SCENARIOS:
        raise ValueError(
            f"Unsupported scenario '{name}'. "
            f"Choose one of: {', '.join(SUPPORTED_SCENARIOS)}"
        )

    balances = read_balance_snapshot(DATA / "balances.json")
    settlements = read_settlement_snapshot(DATA / "obligations.json")
    policy = read_funding_policy(DATA / "funding_policy.json")
    reference_time = REFERENCE_TIME
    workflow = TreasuryDAGWorkflow()

    if name == "normal":
        balances = _with_available_balance(
            balances,
            Currency.EUR,
            1_000_000,
        )

    elif name == "shortfall":
        balances = _with_available_balance(
            balances,
            Currency.GBP,
            1_600_000,
        )

    elif name == "stale":
        reference_time = datetime(
            2026, 9, 7, 8, 0, tzinfo=timezone.utc
        )

    elif name == "tool_failure":
        workflow = TreasuryDAGWorkflow(
            settlement_service=SimulatedSettlementService(
                failures_before_success=99
            ),
            settlement_retry_limit=2,
        )

    elif name == "unauthorized_tool":
        workflow = TreasuryDAGWorkflow(
            capability_guard=DenyFundingCapabilityGuard()
        )

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

    variance_by_currency = {}
    if result.variance is not None:
        for currency, value in result.variance.variances.items():
            variance_by_currency[currency.value] = {
                "available": value.available,
                "required_liquidity": value.required_liquidity,
                "scheduled_outflows": value.scheduled_outflows,
                "projected_requirement": value.projected_requirement,
                "projected_shortfall": value.projected_shortfall,
                "shortfall_detected": value.shortfall_detected,
                "evidence_ids": value.evidence_ids,
            }

    recommendations = []
    if result.funding_recommendation is not None:
        for item in result.funding_recommendation.recommendations:
            recommendations.append({
                "destination_currency": item.destination_currency.value,
                "recommendation": item.recommendation.value,
                "required_amount": item.required_amount,
                "source_currency": (
                    item.source_currency.value
                    if item.source_currency is not None
                    else None
                ),
                "source_available_surplus": item.source_available_surplus,
                "source_capacity_sufficient": item.source_capacity_sufficient,
                "unfunded_amount": item.unfunded_amount,
                "reason": item.reason,
                "evidence_ids": item.evidence_ids,
            })

    approval = None
    if result.approval is not None:
        approval = {
            "workflow_state": result.approval.workflow_state.value,
            "decisions": [
                {
                    "destination_currency": item.destination_currency,
                    "source_currency": item.source_currency,
                    "required_amount": item.required_amount,
                    "decision": item.decision.value,
                    "reason": item.reason,
                    "evidence_ids": item.evidence_ids,
                }
                for item in result.approval.decisions
            ],
            "evidence_ids": result.approval.evidence_ids,
        }

    failure = None
    if result.failure is not None:
        failure = {
            "code": result.failure.code.value,
            "message": result.failure.message,
            "retry_count": result.failure.retry_count,
            "failed_task": result.failure.failed_task,
            "evidence_ids": result.failure.evidence_ids,
        }

    response_payload: dict[str, Any] = {
        "scenario": name,
        "run_state": result.run_state.value,
        "workflow_state": (
            result.workflow_state.value
            if result.workflow_state is not None
            else None
        ),
        "latency_ms": result.latency_ms,
        "task_states": {
            key: value.value
            for key, value in result.task_states.items()
        },
        "retry_counts": result.retry_counts,
        "started_order": result.started_order,
        "completed_order": result.completed_order,
        "variance": variance_by_currency,
        "funding_recommendations": recommendations,
        "approval": approval,
        "failure": failure,
        "trace": [
            {
                "sequence": event.sequence,
                "event_type": event.event_type.value,
                "task_id": event.task_id,
                "state": event.state,
                "detail": event.detail,
                "retry_count": event.retry_count,
                "evidence_ids": list(event.evidence_ids),
            }
            for event in trace
        ],
    }

    if commentary_generator is None:
        response_payload["ai_commentary"] = {
            "status": "not_requested",
            "provider": None,
            "model": None,
            "prompt_version": None,
            "latency_ms": 0,
            "summary": None,
            "message": None,
            "read_only": True,
            "input_scope": "validated_workflow_results_only",
        }
    else:
        # The LLM is intentionally post-processing only. It cannot alter the
        # deterministic Treasury result, approval state, or execution trace.
        response_payload["ai_commentary"] = await commentary_generator(
            response_payload
        )

    return response_payload
