from __future__ import annotations

import asyncio

from demos.remitly_treasury.web_demo_service import run_web_demo_scenario


def main():
    shortfall = asyncio.run(run_web_demo_scenario("shortfall"))
    assert shortfall["scenario"] == "shortfall"
    assert shortfall["run_state"] == "WAITING_FOR_APPROVAL"
    assert shortfall["variance"]["EUR"]["projected_shortfall"] == 430000
    assert shortfall["approval"]["workflow_state"] == "WAITING_FOR_APPROVAL"
    assert len(shortfall["trace"]) > 0

    failure = asyncio.run(run_web_demo_scenario("tool_failure"))
    assert failure["run_state"] == "FAILED_DEPENDENCY"
    assert failure["failure"] is not None
    assert failure["retry_counts"]["obligations"] == 2

    unauthorized = asyncio.run(run_web_demo_scenario("unauthorized_tool"))
    assert unauthorized["run_state"] == "UNAUTHORIZED_EXECUTION"
    assert unauthorized["failure"]["code"] == "UNAUTHORIZED_EXECUTION"

    print(
        "PASS: T10 Treasury web-demo service serializes governed workflow "
        "results, traces, failures, and approval state."
    )


if __name__ == "__main__":
    main()
