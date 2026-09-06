from __future__ import annotations

import argparse

from demos.remitly_treasury.evaluation import SCENARIO_NAMES, run_all_scenarios_sync
from demos.remitly_treasury.trace import render_execution_trace


BANNER = """
========================================================================================
REMITLY TREASURY MULTI-AGENT DEMO
========================================================================================
Architecture:
  Cash Position --------\\
                         > Variance/Reconciliation -> Funding Recommendation -> Approval
  Obligations ----------/

Controls:
  - deterministic Treasury arithmetic
  - evidence lineage
  - DAG dependency enforcement
  - bounded settlement retries
  - stale-data blocking
  - least-privilege capability guard
  - deterministic approval gate
  - visible execution trace
========================================================================================
""".strip()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the isolated Remitly Treasury multi-agent interview demo."
    )
    parser.add_argument(
        "--scenario",
        choices=("all",) + tuple(SCENARIO_NAMES),
        default="all",
        help="Run all scenarios or one named scenario.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Show outcomes without the full per-event trace.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = run_all_scenarios_sync()

    if args.scenario != "all":
        results = [r for r in results if r.name == args.scenario]

    print(BANNER)
    failures = []

    for result in results:
        print()
        print("=" * 88)
        print(f"SCENARIO: {result.name.upper()}")
        print(f"DESCRIPTION: {result.description}")
        print(f"EXPECTED: {result.expected_state.value}")
        print(f"ACTUAL:   {result.actual_state.value}")
        print(f"RESULT:   {'PASS' if result.passed else 'FAIL'}")

        if not args.compact:
            print("-" * 88)
            print("EXECUTION TRACE")
            print("-" * 88)
            print(render_execution_trace(list(result.trace)))

        if not result.passed:
            failures.append(result.name)

    print()
    print("=" * 88)
    print(
        f"DEMO SUMMARY: {len(results) - len(failures)}/{len(results)} "
        "selected scenario(s) passed."
    )

    if failures:
        print("FAILED SCENARIOS: " + ", ".join(failures))
        return 1

    print("Treasury demo completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
