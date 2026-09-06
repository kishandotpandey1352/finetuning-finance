from __future__ import annotations

from datetime import datetime, timezone

from .models import TraceEvent


class ExecutionTrace:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def add(self, component: str, status: str, message: str) -> None:
        self.events.append(
            TraceEvent(
                timestamp=datetime.now(timezone.utc),
                component=component,
                status=status,
                message=message,
            )
        )

    def lines(self) -> list[str]:
        return [
            f"[{event.timestamp.strftime('%H:%M:%S')}] "
            f"{event.component}: {event.status} - {event.message}"
            for event in self.events
        ]
