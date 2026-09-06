from demos.remitly_treasury.evaluation import run_all_scenarios_sync
from demos.remitly_treasury.trace import render_execution_trace


def main():
    results = run_all_scenarios_sync()

    print("=" * 88)
    print("TREASURY T8 REPEATABLE EVALUATION")
    print("=" * 88)

    failures = []

    for result in results:
        print()
        print(f"SCENARIO: {result.name}")
        print(f"DESCRIPTION: {result.description}")
        print(
            f"EXPECTED: {result.expected_state.value} | "
            f"ACTUAL: {result.actual_state.value} | "
            f"RESULT: {'PASS' if result.passed else 'FAIL'}"
        )
        print("-" * 88)
        print(render_execution_trace(list(result.trace)))

        if not result.passed:
            failures.append(result.name)

    print()
    print("=" * 88)
    print(
        f"SUMMARY: {len(results) - len(failures)}/{len(results)} "
        "scenarios passed."
    )

    if failures:
        raise SystemExit(
            "T8 evaluation failed for: " + ", ".join(failures)
        )

    print(
        "PASS: T8 visible execution trace and five repeatable Treasury "
        "evaluation scenarios validated."
    )


if __name__ == "__main__":
    main()
