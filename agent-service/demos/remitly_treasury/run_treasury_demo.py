from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.workflow import TreasuryWorkflow


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SCENARIOS = HERE / "scenarios"


def _fixed_now() -> datetime:
    return datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def money(value: float, currency: str) -> str:
    symbol = {"GBP": "£", "EUR": "€", "USD": "$"}.get(currency, currency + " ")
    return f"{symbol}{value:,.0f}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Remitly Treasury multi-agent demo")
    parser.add_argument(
        "--scenario",
        choices=["shortfall", "normal", "stale", "tool-failure"],
        default="shortfall",
    )
    args = parser.parse_args()

    balances = DATA / "balances.json"
    obligations = DATA / "obligations.json"
    fail_attempts = 0
    if args.scenario == "normal":
        balances = SCENARIOS / "balances_normal.json"
        obligations = SCENARIOS / "obligations_normal.json"
    elif args.scenario == "stale":
        balances = SCENARIOS / "balances_stale.json"
    elif args.scenario == "tool-failure":
        fail_attempts = 5

    workflow = TreasuryWorkflow(
        balances_path=balances,
        obligations_path=obligations,
        policy_path=DATA / "funding_policy.json",
        now_provider=_fixed_now,
        settlement_fail_attempts=fail_attempts,
        settlement_max_retries=2,
    )
    result = await workflow.run(run_id=f"treasury-{args.scenario}-001")

    print("\nEXECUTION TRACE")
    print("=" * 72)
    for event in result.trace:
        print(
            f"[{event.timestamp.strftime('%H:%M:%S')}] "
            f"{event.component:<30} {event.status:<24} {event.message}"
        )

    print("\n" + "=" * 72)
    print("TREASURY AI WORKFLOW")
    print("=" * 72)
    print(f"Run:    {result.run_id}")
    print(f"Status: {result.state.value}")
    if result.error:
        print(f"Error:  {result.error}")
    if result.recommendation:
        rec = result.recommendation
        print(f"Recommendation: {rec.recommendation}")
        if rec.destination_currency:
            print(f"Destination:    {rec.destination_currency}")
        if rec.source_currency:
            print(f"Source:         {rec.source_currency}")
        print(f"Amount:         {money(rec.proposed_amount, rec.destination_currency or 'GBP')}")
        print(f"Human approval: {'YES' if rec.requires_human_approval else 'NO'}")
        print("Evidence:       " + ", ".join(rec.evidence_ids))
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
