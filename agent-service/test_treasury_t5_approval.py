from pathlib import Path

from demos.remitly_treasury.approval import ApprovalDecision, TreasuryApprovalGate
from demos.remitly_treasury.agent_models import (
    FundingRecommendation,
    FundingRecommendationResult,
    FundingRecommendationType,
    TreasuryAgentStatus,
)
from demos.remitly_treasury.domain import Currency
from demos.remitly_treasury.tools import read_funding_policy


DATA = Path(__file__).parent / "demos" / "remitly_treasury" / "data"


def make_result(amount, source_surplus, sufficient):
    return FundingRecommendationResult(
        status=TreasuryAgentStatus.alert,
        recommendations=[
            FundingRecommendation(
                destination_currency=Currency.EUR,
                recommendation=FundingRecommendationType.transfer_required,
                required_amount=amount,
                source_currency=Currency.GBP,
                source_available_surplus=source_surplus,
                source_capacity_sufficient=sufficient,
                unfunded_amount=max(0, amount - source_surplus),
                reason="test",
                evidence_ids=["BAL-EUR-001", "SET-EUR-201", "BAL-GBP-001"],
            )
        ],
        evidence_ids=["BAL-EUR-001", "SET-EUR-201", "BAL-GBP-001"],
    )


def main():
    policy = read_funding_policy(DATA / "funding_policy.json")
    gate = TreasuryApprovalGate()

    high = gate.evaluate(
        recommendation_result=make_result(430000, 500000, True),
        policy=policy,
    )
    assert high.workflow_state == ApprovalDecision.waiting_for_approval

    small = gate.evaluate(
        recommendation_result=make_result(20000, 100000, True),
        policy=policy,
    )
    assert small.workflow_state == ApprovalDecision.auto_allowed

    blocked = gate.evaluate(
        recommendation_result=make_result(430000, 200000, False),
        policy=policy,
    )
    assert blocked.workflow_state == ApprovalDecision.blocked

    print("PASS: T5 deterministic approval gate enforces auto-allow, human approval, and blocked funding states.")


if __name__ == "__main__":
    main()
