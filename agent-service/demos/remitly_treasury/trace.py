from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from demos.remitly_treasury.workflow import (
    TREASURY_DAG,
    TreasuryTaskState,
    TreasuryWorkflowResult,
)


class TraceEventType(str, Enum):
    workflow_started = "WORKFLOW_STARTED"
    dag_plan = "DAG_PLAN"
    task_started = "TASK_STARTED"
    task_retry = "TASK_RETRY"
    task_finished = "TASK_FINISHED"
    task_skipped = "TASK_SKIPPED"
    failure = "FAILURE"
    workflow_finished = "WORKFLOW_FINISHED"


@dataclass(frozen=True)
class TreasuryTraceEvent:
    sequence: int
    event_type: TraceEventType
    task_id: str | None
    state: str | None
    detail: str
    retry_count: int = 0
    evidence_ids: tuple[str, ...] = ()


def _evidence_for_task(
    result: TreasuryWorkflowResult,
    task_id: str,
) -> tuple[str, ...]:
    value = {
        "cash_position": result.cash_position,
        "obligations": result.obligations,
        "variance": result.variance,
        "funding_recommendation": result.funding_recommendation,
        "approval_gate": result.approval,
    }.get(task_id)

    if value is None:
        return ()

    evidence_ids = getattr(value, "evidence_ids", None)
    if not evidence_ids:
        return ()
    return tuple(dict.fromkeys(evidence_ids))


def build_execution_trace(
    result: TreasuryWorkflowResult,
    *,
    scenario_name: str,
) -> list[TreasuryTraceEvent]:
    """Create a visible, stable trace from the governed workflow result.

    The trace is intentionally derived from server-owned runtime state rather
    than agent prose. It contains task ordering, final task state, retry counts,
    evidence IDs and the terminal workflow state.
    """

    events: list[TreasuryTraceEvent] = []

    def emit(
        event_type: TraceEventType,
        *,
        task_id: str | None = None,
        state: str | None = None,
        detail: str,
        retry_count: int = 0,
        evidence_ids: tuple[str, ...] = (),
    ) -> None:
        events.append(
            TreasuryTraceEvent(
                sequence=len(events) + 1,
                event_type=event_type,
                task_id=task_id,
                state=state,
                detail=detail,
                retry_count=retry_count,
                evidence_ids=evidence_ids,
            )
        )

    emit(
        TraceEventType.workflow_started,
        state="RUNNING",
        detail=f"Scenario '{scenario_name}' started.",
    )

    dependencies = "; ".join(
        f"{spec.task_id}<-{','.join(spec.dependencies) if spec.dependencies else 'ROOT'}"
        for spec in TREASURY_DAG
    )
    emit(
        TraceEventType.dag_plan,
        state="PLANNED",
        detail=dependencies,
    )

    for task_id in result.started_order:
        emit(
            TraceEventType.task_started,
            task_id=task_id,
            state="RUNNING",
            detail=f"{task_id} started.",
        )

        retry_count = result.retry_counts.get(task_id, 0)
        if retry_count:
            emit(
                TraceEventType.task_retry,
                task_id=task_id,
                state="RETRYING",
                detail=(
                    f"{task_id} used {retry_count} bounded "
                    f"retr{'y' if retry_count == 1 else 'ies'}."
                ),
                retry_count=retry_count,
            )

    completed = set(result.completed_order)
    for task_id in result.completed_order:
        final_state = result.task_states[task_id]
        emit(
            TraceEventType.task_finished,
            task_id=task_id,
            state=final_state.value.upper(),
            detail=f"{task_id} finished as {final_state.value}.",
            retry_count=result.retry_counts.get(task_id, 0),
            evidence_ids=_evidence_for_task(result, task_id),
        )

    for spec in TREASURY_DAG:
        if (
            result.task_states[spec.task_id] == TreasuryTaskState.skipped
            and spec.task_id not in completed
        ):
            emit(
                TraceEventType.task_skipped,
                task_id=spec.task_id,
                state="SKIPPED",
                detail=(
                    f"{spec.task_id} skipped because a required "
                    "upstream dependency did not produce valid output."
                ),
            )

    if result.failure is not None:
        emit(
            TraceEventType.failure,
            task_id=result.failure.failed_task,
            state=result.failure.code.value,
            detail=result.failure.message,
            retry_count=result.failure.retry_count,
            evidence_ids=tuple(result.failure.evidence_ids),
        )

    emit(
        TraceEventType.workflow_finished,
        state=result.run_state.value,
        detail=(
            f"Scenario '{scenario_name}' finished with "
            f"{result.run_state.value} in {result.latency_ms} ms."
        ),
    )

    return events


def render_execution_trace(events: list[TreasuryTraceEvent]) -> str:
    lines = []
    for event in events:
        task = event.task_id or "-"
        evidence = (
            ",".join(event.evidence_ids)
            if event.evidence_ids
            else "-"
        )
        lines.append(
            f"{event.sequence:02d} | {event.event_type.value:<18} | "
            f"{task:<24} | {event.state or '-':<24} | "
            f"retries={event.retry_count} | evidence={evidence} | "
            f"{event.detail}"
        )
    return "\n".join(lines)
