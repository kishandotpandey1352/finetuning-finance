from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from time import perf_counter

from demos.remitly_treasury.agent_models import (
    CashPositionResult,
    FundingRecommendationResult,
    ObligationsResult,
    VarianceResult,
)
from demos.remitly_treasury.agents import (
    CashPositionAgent,
    FundingRecommendationAgent,
    ObligationsAgent,
    VarianceReconciliationAgent,
)
from demos.remitly_treasury.approval import (
    ApprovalDecision,
    ApprovalGateResult,
    TreasuryApprovalGate,
)
from demos.remitly_treasury.domain import (
    BalanceSnapshot,
    FundingPolicy,
    SettlementSnapshot,
)
from demos.remitly_treasury.failure import (
    SettlementServiceUnavailableError,
    SimulatedSettlementService,
    TreasuryFailure,
    TreasuryFailureCode,
    TreasuryRunState,
)
from demos.remitly_treasury.security import (
    TreasuryAuthorizationError,
    TreasuryCapability,
    TreasuryCapabilityGuard,
    TreasuryDataScope,
)
from demos.remitly_treasury.tools import StaleSourceDataError


class TreasuryTaskState(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"
    retrying = "retrying"


@dataclass(frozen=True)
class TreasuryTaskSpec:
    task_id: str
    dependencies: tuple[str, ...]


TREASURY_DAG = (
    TreasuryTaskSpec("cash_position", ()),
    TreasuryTaskSpec("obligations", ()),
    TreasuryTaskSpec("variance", ("cash_position", "obligations")),
    TreasuryTaskSpec("funding_recommendation", ("variance",)),
    TreasuryTaskSpec("approval_gate", ("funding_recommendation",)),
)


@dataclass
class TreasuryWorkflowResult:
    cash_position: CashPositionResult | None
    obligations: ObligationsResult | None
    variance: VarianceResult | None
    funding_recommendation: FundingRecommendationResult | None
    approval: ApprovalGateResult | None
    workflow_state: ApprovalDecision | None
    run_state: TreasuryRunState
    failure: TreasuryFailure | None
    task_states: dict[str, TreasuryTaskState]
    retry_counts: dict[str, int]
    started_order: list[str]
    completed_order: list[str]
    latency_ms: int


def _run_state_from_approval(decision: ApprovalDecision) -> TreasuryRunState:
    return {
        ApprovalDecision.no_action: TreasuryRunState.no_action,
        ApprovalDecision.auto_allowed: TreasuryRunState.auto_allowed,
        ApprovalDecision.waiting_for_approval: TreasuryRunState.waiting_for_approval,
        ApprovalDecision.blocked: TreasuryRunState.blocked,
    }[decision]


class TreasuryDAGWorkflow:
    def __init__(
        self,
        *,
        cash_agent=None,
        obligations_agent=None,
        variance_agent=None,
        funding_agent=None,
        approval_gate=None,
        capability_guard: TreasuryCapabilityGuard | None = None,
        settlement_service: SimulatedSettlementService | None = None,
        settlement_retry_limit: int = 2,
    ):
        if settlement_retry_limit < 0:
            raise ValueError("settlement_retry_limit must be >= 0")

        self.cash_agent = cash_agent or CashPositionAgent()
        self.obligations_agent = obligations_agent or ObligationsAgent()
        self.variance_agent = variance_agent or VarianceReconciliationAgent()
        self.funding_agent = funding_agent or FundingRecommendationAgent()
        self.approval_gate = approval_gate or TreasuryApprovalGate()
        self.capability_guard = capability_guard or TreasuryCapabilityGuard()
        self.settlement_service = settlement_service or SimulatedSettlementService()
        self.settlement_retry_limit = settlement_retry_limit

        # Fail closed if execution privilege is ever accidentally added.
        self.capability_guard.assert_no_execution_capability()

    async def run(
        self,
        *,
        balances: BalanceSnapshot,
        settlements: SettlementSnapshot,
        policy: FundingPolicy,
        reference_time: datetime,
        max_balance_age_seconds: int,
        settlements_through: datetime | None = None,
    ) -> TreasuryWorkflowResult:
        states = {task.task_id: TreasuryTaskState.pending for task in TREASURY_DAG}
        retries = {task.task_id: 0 for task in TREASURY_DAG}
        started: list[str] = []
        completed: list[str] = []
        clock = perf_counter()

        cash_result = None
        obligations_result = None
        variance_result = None
        funding_result = None
        approval_result = None

        def result(
            *,
            run_state: TreasuryRunState,
            failure: TreasuryFailure | None = None,
            workflow_state: ApprovalDecision | None = None,
        ) -> TreasuryWorkflowResult:
            return TreasuryWorkflowResult(
                cash_position=cash_result,
                obligations=obligations_result,
                variance=variance_result,
                funding_recommendation=funding_result,
                approval=approval_result,
                workflow_state=workflow_state,
                run_state=run_state,
                failure=failure,
                task_states=states,
                retry_counts=retries,
                started_order=started,
                completed_order=completed,
                latency_ms=max(0, int((perf_counter() - clock) * 1000)),
            )

        def skip_downstream(after_task: str) -> None:
            order = [
                "cash_position",
                "obligations",
                "variance",
                "funding_recommendation",
                "approval_gate",
            ]
            if after_task in {"cash_position", "obligations"}:
                targets = ["variance", "funding_recommendation", "approval_gate"]
            elif after_task == "variance":
                targets = ["funding_recommendation", "approval_gate"]
            elif after_task == "funding_recommendation":
                targets = ["approval_gate"]
            else:
                targets = []
            for task_id in targets:
                if states[task_id] == TreasuryTaskState.pending:
                    states[task_id] = TreasuryTaskState.skipped

        async def run_cash():
            states["cash_position"] = TreasuryTaskState.running
            started.append("cash_position")
            try:
                self.capability_guard.authorize(
                    agent_name=self.cash_agent.name,
                    capability=TreasuryCapability.ANALYZE_CASH_POSITION,
                    data_scopes={TreasuryDataScope.BALANCE_SNAPSHOT},
                )
                value = await asyncio.to_thread(
                    self.cash_agent.execute,
                    balances=balances,
                    reference_time=reference_time,
                    max_age_seconds=max_balance_age_seconds,
                )
                states["cash_position"] = TreasuryTaskState.completed
                completed.append("cash_position")
                return "ok", value, None
            except TreasuryAuthorizationError as exc:
                states["cash_position"] = TreasuryTaskState.failed
                completed.append("cash_position")
                return (
                    "unauthorized",
                    None,
                    TreasuryFailure(
                        code=TreasuryFailureCode.unauthorized_execution,
                        message=str(exc),
                        failed_task="cash_position",
                    ),
                )
            except StaleSourceDataError as exc:
                states["cash_position"] = TreasuryTaskState.failed
                completed.append("cash_position")
                return (
                    "stale",
                    None,
                    TreasuryFailure(
                        code=TreasuryFailureCode.stale_source_data,
                        message=str(exc),
                        failed_task="cash_position",
                        evidence_ids=[r.evidence_id for r in balances.records],
                    ),
                )
            except Exception as exc:
                states["cash_position"] = TreasuryTaskState.failed
                completed.append("cash_position")
                return (
                    "failed",
                    None,
                    TreasuryFailure(
                        code=TreasuryFailureCode.failed_dependency,
                        message=f"Cash-position dependency failed: {exc}",
                        failed_task="cash_position",
                    ),
                )

        async def run_obligations():
            states["obligations"] = TreasuryTaskState.running
            started.append("obligations")
            attempts = 0
            max_attempts = self.settlement_retry_limit + 1

            try:
                self.capability_guard.authorize(
                    agent_name=self.obligations_agent.name,
                    capability=TreasuryCapability.ANALYZE_OBLIGATIONS,
                    data_scopes={TreasuryDataScope.SETTLEMENT_SNAPSHOT},
                )
            except TreasuryAuthorizationError as exc:
                states["obligations"] = TreasuryTaskState.failed
                completed.append("obligations")
                return (
                    "unauthorized",
                    None,
                    TreasuryFailure(
                        code=TreasuryFailureCode.unauthorized_execution,
                        message=str(exc),
                        failed_task="obligations",
                    ),
                )

            while attempts < max_attempts:
                attempts += 1
                try:
                    self.settlement_service.before_read()
                    value = await asyncio.to_thread(
                        self.obligations_agent.execute,
                        settlements=settlements,
                        through=settlements_through,
                    )
                    retries["obligations"] = attempts - 1
                    states["obligations"] = TreasuryTaskState.completed
                    completed.append("obligations")
                    return "ok", value, None
                except SettlementServiceUnavailableError as exc:
                    retries["obligations"] = attempts - 1
                    if attempts >= max_attempts:
                        states["obligations"] = TreasuryTaskState.failed
                        completed.append("obligations")
                        return (
                            "failed",
                            None,
                            TreasuryFailure(
                                code=TreasuryFailureCode.settlement_service_unavailable,
                                message=str(exc),
                                retry_count=attempts - 1,
                                failed_task="obligations",
                            ),
                        )
                    states["obligations"] = TreasuryTaskState.retrying
                    await asyncio.sleep(0)
                    states["obligations"] = TreasuryTaskState.running
                except Exception as exc:
                    states["obligations"] = TreasuryTaskState.failed
                    completed.append("obligations")
                    return (
                        "failed",
                        None,
                        TreasuryFailure(
                            code=TreasuryFailureCode.failed_dependency,
                            message=f"Obligations dependency failed: {exc}",
                            retry_count=attempts - 1,
                            failed_task="obligations",
                        ),
                    )

        cash_task = asyncio.create_task(run_cash())
        obligations_task = asyncio.create_task(run_obligations())

        cash_status, cash_value, cash_failure = await cash_task
        obligations_status, obligations_value, obligations_failure = await obligations_task

        cash_result = cash_value
        obligations_result = obligations_value

        if cash_status != "ok" or obligations_status != "ok":
            skip_downstream("cash_position")

            auth_failure = (
                cash_failure if cash_status == "unauthorized"
                else obligations_failure if obligations_status == "unauthorized"
                else None
            )
            if auth_failure is not None:
                return result(
                    run_state=TreasuryRunState.unauthorized_execution,
                    failure=auth_failure,
                )

            if cash_status == "stale":
                return result(
                    run_state=TreasuryRunState.stale_source_data,
                    failure=cash_failure,
                )

            upstream_failure = cash_failure or obligations_failure
            return result(
                run_state=TreasuryRunState.failed_dependency,
                failure=TreasuryFailure(
                    code=TreasuryFailureCode.failed_dependency,
                    message=(
                        "Required upstream Treasury dependency failed; "
                        "downstream calculations and recommendations were skipped."
                    ),
                    retry_count=(
                        upstream_failure.retry_count if upstream_failure else 0
                    ),
                    failed_task=(
                        upstream_failure.failed_task if upstream_failure else None
                    ),
                    evidence_ids=(
                        upstream_failure.evidence_ids if upstream_failure else []
                    ),
                ),
            )

        states["variance"] = TreasuryTaskState.running
        started.append("variance")
        try:
            self.capability_guard.authorize(
                agent_name=self.variance_agent.name,
                capability=TreasuryCapability.RECONCILE_VARIANCE,
                data_scopes={
                    TreasuryDataScope.CASH_POSITION_RESULT,
                    TreasuryDataScope.OBLIGATIONS_RESULT,
                },
            )
            variance_result = await asyncio.to_thread(
                self.variance_agent.execute,
                cash=cash_result,
                obligations=obligations_result,
            )
            states["variance"] = TreasuryTaskState.completed
            completed.append("variance")
        except TreasuryAuthorizationError as exc:
            states["variance"] = TreasuryTaskState.failed
            skip_downstream("variance")
            completed.append("variance")
            return result(
                run_state=TreasuryRunState.unauthorized_execution,
                failure=TreasuryFailure(
                    code=TreasuryFailureCode.unauthorized_execution,
                    message=str(exc),
                    failed_task="variance",
                ),
            )
        except Exception as exc:
            states["variance"] = TreasuryTaskState.failed
            skip_downstream("variance")
            completed.append("variance")
            return result(
                run_state=TreasuryRunState.failed_dependency,
                failure=TreasuryFailure(
                    code=TreasuryFailureCode.failed_dependency,
                    message=f"Variance dependency failed: {exc}",
                    failed_task="variance",
                ),
            )

        states["funding_recommendation"] = TreasuryTaskState.running
        started.append("funding_recommendation")
        try:
            self.capability_guard.authorize(
                agent_name=self.funding_agent.name,
                capability=TreasuryCapability.RECOMMEND_FUNDING,
                data_scopes={
                    TreasuryDataScope.CASH_POSITION_RESULT,
                    TreasuryDataScope.VARIANCE_RESULT,
                    TreasuryDataScope.FUNDING_POLICY,
                },
            )
            funding_result = await asyncio.to_thread(
                self.funding_agent.execute,
                cash=cash_result,
                variance=variance_result,
                policy=policy,
            )
            states["funding_recommendation"] = TreasuryTaskState.completed
            completed.append("funding_recommendation")
        except TreasuryAuthorizationError as exc:
            states["funding_recommendation"] = TreasuryTaskState.failed
            skip_downstream("funding_recommendation")
            completed.append("funding_recommendation")
            return result(
                run_state=TreasuryRunState.unauthorized_execution,
                failure=TreasuryFailure(
                    code=TreasuryFailureCode.unauthorized_execution,
                    message=str(exc),
                    failed_task="funding_recommendation",
                ),
            )
        except Exception as exc:
            states["funding_recommendation"] = TreasuryTaskState.failed
            skip_downstream("funding_recommendation")
            completed.append("funding_recommendation")
            return result(
                run_state=TreasuryRunState.failed_dependency,
                failure=TreasuryFailure(
                    code=TreasuryFailureCode.failed_dependency,
                    message=f"Funding recommendation failed: {exc}",
                    failed_task="funding_recommendation",
                ),
            )

        states["approval_gate"] = TreasuryTaskState.running
        started.append("approval_gate")
        try:
            self.capability_guard.authorize(
                agent_name=self.approval_gate.name,
                capability=TreasuryCapability.EVALUATE_APPROVAL,
                data_scopes={
                    TreasuryDataScope.FUNDING_RECOMMENDATION_RESULT,
                    TreasuryDataScope.FUNDING_POLICY,
                },
            )
            approval_result = await asyncio.to_thread(
                self.approval_gate.evaluate,
                recommendation_result=funding_result,
                policy=policy,
            )
            states["approval_gate"] = TreasuryTaskState.completed
            completed.append("approval_gate")
        except TreasuryAuthorizationError as exc:
            states["approval_gate"] = TreasuryTaskState.failed
            completed.append("approval_gate")
            return result(
                run_state=TreasuryRunState.unauthorized_execution,
                failure=TreasuryFailure(
                    code=TreasuryFailureCode.unauthorized_execution,
                    message=str(exc),
                    failed_task="approval_gate",
                ),
            )
        except Exception as exc:
            states["approval_gate"] = TreasuryTaskState.failed
            completed.append("approval_gate")
            return result(
                run_state=TreasuryRunState.failed_dependency,
                failure=TreasuryFailure(
                    code=TreasuryFailureCode.failed_dependency,
                    message=f"Approval gate failed: {exc}",
                    failed_task="approval_gate",
                ),
            )

        return result(
            run_state=_run_state_from_approval(approval_result.workflow_state),
            workflow_state=approval_result.workflow_state,
        )
