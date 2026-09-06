from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .models import BalanceRecord, FundingPolicy, SettlementObligation
from .permissions import require_tool


class StaleSourceData(RuntimeError):
    pass


class SettlementServiceUnavailable(RuntimeError):
    pass


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_policy(path: Path) -> FundingPolicy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FundingPolicy(
        minimum_liquidity_buffer=float(payload["minimum_liquidity_buffer"]),
        auto_execution_threshold=float(payload["auto_execution_threshold"]),
        manual_approval_threshold=float(payload["manual_approval_threshold"]),
        max_balance_age_hours=float(payload["max_balance_age_hours"]),
        available_funding_corridors=tuple(payload["available_funding_corridors"]),
    )


class MockBalanceTool:
    name = "read_balances"

    def __init__(self, path: Path, now_provider: Callable[[], datetime]):
        self.path = path
        self.now_provider = now_provider

    def read(self, *, agent_name: str, max_age_hours: float) -> list[BalanceRecord]:
        require_tool(agent_name, self.name)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        now = self.now_provider()
        records: list[BalanceRecord] = []
        for item in payload["balances"]:
            updated = _dt(item["last_updated"])
            age_hours = (now - updated).total_seconds() / 3600
            if age_hours > max_age_hours:
                raise StaleSourceData(
                    f"STALE_SOURCE_DATA: {item['currency']} balance is {age_hours:.1f}h old"
                )
            records.append(
                BalanceRecord(
                    currency=item["currency"],
                    available_balance=float(item["available_balance"]),
                    required_liquidity=float(item["required_liquidity"]),
                    last_updated=updated,
                    evidence_id=item["evidence_id"],
                )
            )
        return records


class MockSettlementTool:
    name = "read_settlements"

    def __init__(self, path: Path, fail_attempts: int = 0):
        self.path = path
        self.fail_attempts = fail_attempts
        self.calls = 0

    def read(self, *, agent_name: str) -> list[SettlementObligation]:
        require_tool(agent_name, self.name)
        self.calls += 1
        if self.calls <= self.fail_attempts:
            raise SettlementServiceUnavailable("SETTLEMENT_SERVICE_UNAVAILABLE")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [
            SettlementObligation(
                settlement_id=item["settlement_id"],
                currency=item["currency"],
                amount=float(item["amount"]),
                due_at=_dt(item["due_at"]),
                status=item["status"],
                evidence_id=item["evidence_id"],
            )
            for item in payload["obligations"]
            if item["status"] == "pending"
        ]
