from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .agents import (
    CashPositionAgent,
    FundingRecommendationAgent,
    ObligationsAgent,
    VarianceAgent,
)
from .models import RunState, TreasuryRunResult
from .tools import MockBalanceTool, MockSettlementTool, StaleSourceData, load_policy
from .tracing import ExecutionTrace


class TreasuryWorkflow:
    """Interview-safe Treasury workflow.

    The two root tasks are independent and execute in parallel. Variance waits
    for both roots; recommendation waits for variance; deterministic policy
    decides whether the workflow stops for human approval.
    """

    def __init__(
        self,
        *,
        balances_path: Path,
        obligations_path: Path,
        policy_path: Path,
        now_provider=None,
        settlement_fail_attempts: int = 0,
        settlement_max_retries: int = 2,
    ) -> None:
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self.policy = load_policy(policy_path)
        self.balance_tool = MockBalanceTool(balances_path, self.now_provider)
        self.settlement_tool = MockSettlementTool(
            obligations_path, fail_attempts=settlement_fail_attempts
        )
        self.cash_agent = CashPositionAgent(self.balance_tool, self.policy)
        self.obligations_agent = ObligationsAgent(
            self.settlement_tool, max_retries=settlement_max_retries
        )
        self.variance_agent = VarianceAgent()
        self.funding_agent = FundingRecommendationAgent()

    async def run(self, run_id: str | None = None) -> TreasuryRunResult:
        run_id = run_id or f"treasury-demo-{uuid4().hex[:8]}"
        trace = ExecutionTrace()
        trace.add("Coordinator", "RECEIVED", "Treasury liquidity-monitoring objective received")
        trace.add(
            "Coordinator",
            "PLAN_CREATED",
            "cash_position + obligations -> variance -> funding_recommendation",
        )
        trace.add("PlanValidator", "PASSED", "Dependency graph and demo policy accepted")

        trace.add("cash_position_agent", "STARTED", "Reading current balances")
        trace.add("obligations_agent", "STARTED", "Reading pending settlements")

        try:
            cash_task = asyncio.create_task(self.cash_agent.execute())
            obligations_task = asyncio.create_task(self.obligations_agent.execute())
            cash, obligations = await asyncio.gather(cash_task, obligations_task)
        except StaleSourceData as exc:
            trace.add("cash_position_agent", "BLOCKED", str(exc))
            return TreasuryRunResult(
                run_id=run_id,
                state=RunState.BLOCKED,
                trace=trace.events,
                error=str(exc),
                metadata={"required_action": "REFRESH_BALANCE"},
            )

        trace.add("cash_position_agent", "COMPLETED", "Cash positions calculated deterministically")
        if obligations.status != "success":
            trace.add(
                "obligations_agent",
                "FAILED",
                f"{obligations.error}; retries={obligations.retry_count}",
            )
            return TreasuryRunResult(
                run_id=run_id,
                state=RunState.FAILED,
                cash_position=cash,
                obligations=obligations,
                trace=trace.events,
                error="FAILED_DEPENDENCY",
            )
        trace.add(
            "obligations_agent",
            "COMPLETED",
            f"Pending settlements grouped by currency; retries={obligations.retry_count}",
        )

        trace.add("variance_agent", "STARTED", "Waiting prerequisites satisfied")
        variance = await self.variance_agent.execute(cash, obligations)
        if variance.status != "success":
            trace.add("variance_agent", "FAILED", variance.error or "FAILED_DEPENDENCY")
            return TreasuryRunResult(
                run_id=run_id,
                state=RunState.FAILED,
                cash_position=cash,
                obligations=obligations,
                variance=variance,
                trace=trace.events,
                error=variance.error,
            )
        shortfalls = {
            c: v["projected_shortfall"]
            for c, v in variance.by_currency.items()
            if float(v["projected_shortfall"]) > 0
        }
        trace.add("variance_agent", "COMPLETED", f"Shortfalls={shortfalls or 'none'}")

        trace.add("funding_recommendation_agent", "STARTED", "Creating bounded recommendation")
        recommendation = await self.funding_agent.execute(variance, self.policy)
        trace.add(
            "funding_recommendation_agent",
            "COMPLETED",
            f"{recommendation.recommendation}; amount={recommendation.proposed_amount:.2f}",
        )

        if recommendation.requires_human_approval:
            trace.add(
                "PolicyGate",
                "HUMAN_APPROVAL_REQUIRED",
                "Recommendation exceeds manual-approval threshold",
            )
            state = RunState.WAITING_FOR_APPROVAL
        elif recommendation.status == "blocked":
            trace.add("PolicyGate", "BLOCKED", recommendation.reason)
            state = RunState.BLOCKED
        else:
            trace.add("PolicyGate", "PASSED", "No human approval required")
            state = RunState.COMPLETED

        return TreasuryRunResult(
            run_id=run_id,
            state=state,
            cash_position=cash,
            obligations=obligations,
            variance=variance,
            recommendation=recommendation,
            trace=trace.events,
        )
