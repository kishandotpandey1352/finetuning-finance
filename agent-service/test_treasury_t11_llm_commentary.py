from __future__ import annotations

import asyncio

from demos.remitly_treasury.llm_commentary import build_commentary_input
from demos.remitly_treasury.web_demo_service import run_web_demo_scenario


async def fake_commentary(payload: dict) -> dict:
    grounded = build_commentary_input(payload)

    assert grounded["scenario"] == "shortfall"
    assert grounded["variance"]["EUR"]["projected_shortfall"] == 430000
    assert grounded["approval"]["workflow_state"] == "WAITING_FOR_APPROVAL"

    # The LLM input is intentionally narrower than the full runtime response.
    assert "trace" not in grounded
    assert "started_order" not in grounded
    assert "completed_order" not in grounded

    return {
        "status": "generated",
        "provider": "test-provider",
        "model": "test-model",
        "prompt_version": "test-v1",
        "latency_ms": 1,
        "summary": (
            "EUR has a validated liquidity shortfall and the funding "
            "recommendation is waiting for human approval."
        ),
        "message": None,
        "read_only": True,
        "input_scope": "validated_workflow_results_only",
    }


def main():
    result = asyncio.run(
        run_web_demo_scenario(
            "shortfall",
            commentary_generator=fake_commentary,
        )
    )

    commentary = result["ai_commentary"]

    assert commentary["status"] == "generated"
    assert commentary["read_only"] is True
    assert commentary["input_scope"] == "validated_workflow_results_only"
    assert "human approval" in commentary["summary"]

    # T11 must not change the governed Treasury decision.
    assert result["run_state"] == "WAITING_FOR_APPROVAL"
    assert result["variance"]["EUR"]["projected_shortfall"] == 430000

    print(
        "PASS: T11 LLM commentary is read-only, receives validated workflow "
        "results, and cannot alter the Treasury decision path."
    )


if __name__ == "__main__":
    main()
