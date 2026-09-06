from demos.remitly_treasury.evaluation import (
    SCENARIO_NAMES,
    run_all_scenarios_sync,
)
from demos.remitly_treasury.failure import TreasuryRunState
from demos.remitly_treasury.trace import TraceEventType


EXPECTED = {
    "normal": TreasuryRunState.no_action,
    "shortfall": TreasuryRunState.waiting_for_approval,
    "stale": TreasuryRunState.stale_source_data,
    "tool_failure": TreasuryRunState.failed_dependency,
    "unauthorized_tool": TreasuryRunState.unauthorized_execution,
}


def main():
    assert SCENARIO_NAMES == (
        "normal",
        "shortfall",
        "stale",
        "tool_failure",
        "unauthorized_tool",
    )

    results = run_all_scenarios_sync()
    assert len(results) == 5

    by_name = {result.name: result for result in results}

    for name, expected_state in EXPECTED.items():
        result = by_name[name]
        assert result.passed is True
        assert result.expected_state == expected_state
        assert result.actual_state == expected_state

        assert result.trace[0].event_type == TraceEventType.workflow_started
        assert result.trace[-1].event_type == TraceEventType.workflow_finished
        assert result.trace[-1].state == expected_state.value

    shortfall = by_name["shortfall"]
    assert any(
        event.task_id == "approval_gate"
        and event.event_type == TraceEventType.task_finished
        for event in shortfall.trace
    )

    stale = by_name["stale"]
    assert any(
        event.event_type == TraceEventType.failure
        and event.state == "STALE_SOURCE_DATA"
        for event in stale.trace
    )
    assert any(
        event.task_id == "variance"
        and event.event_type == TraceEventType.task_skipped
        for event in stale.trace
    )

    tool_failure = by_name["tool_failure"]
    assert any(
        event.task_id == "obligations"
        and event.event_type == TraceEventType.task_retry
        and event.retry_count == 2
        for event in tool_failure.trace
    )

    unauthorized = by_name["unauthorized_tool"]
    assert any(
        event.event_type == TraceEventType.failure
        and event.state == "UNAUTHORIZED_EXECUTION"
        for event in unauthorized.trace
    )

    print(
        "PASS: T8 visible trace and normal/shortfall/stale/tool-failure/"
        "unauthorized-tool scenarios are repeatable."
    )


if __name__ == "__main__":
    main()
