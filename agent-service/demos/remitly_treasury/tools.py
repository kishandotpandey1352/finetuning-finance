from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from demos.remitly_treasury.domain import (
    BalanceSnapshot,
    Currency,
    FundingPolicy,
    SettlementDirection,
    SettlementSnapshot,
    SettlementStatus,
)


class TreasuryToolError(RuntimeError):
    pass


class TreasurySourceValidationError(TreasuryToolError):
    pass


class StaleSourceDataError(TreasuryToolError):
    def __init__(
        self,
        *,
        source_name: str,
        observed_at: datetime,
        reference_time: datetime,
        max_age_seconds: int,
    ) -> None:
        self.source_name = source_name
        self.observed_at = observed_at
        self.reference_time = reference_time
        self.max_age_seconds = max_age_seconds
        super().__init__(
            f"{source_name} is stale: observed_at={observed_at.isoformat()} "
            f"reference_time={reference_time.isoformat()} "
            f"max_age_seconds={max_age_seconds}"
        )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def read_balance_snapshot(path: str | Path) -> BalanceSnapshot:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return BalanceSnapshot.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise TreasurySourceValidationError(
            f"Could not load valid balance snapshot from {path}."
        ) from exc


def read_settlement_snapshot(path: str | Path) -> SettlementSnapshot:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return SettlementSnapshot.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise TreasurySourceValidationError(
            f"Could not load valid settlement snapshot from {path}."
        ) from exc


def read_funding_policy(path: str | Path) -> FundingPolicy:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return FundingPolicy.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise TreasurySourceValidationError(
            f"Could not load valid funding policy from {path}."
        ) from exc


def validate_balance_freshness(
    snapshot: BalanceSnapshot,
    *,
    reference_time: datetime,
    max_age_seconds: int,
) -> None:
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive.")

    reference = _ensure_aware(reference_time)
    for record in snapshot.records:
        observed = _ensure_aware(record.last_updated)
        age = (reference - observed).total_seconds()
        if age < 0:
            raise TreasuryToolError(
                f"Balance record {record.record_id} is dated in the future."
            )
        if age > max_age_seconds:
            raise StaleSourceDataError(
                source_name=record.source,
                observed_at=observed,
                reference_time=reference,
                max_age_seconds=max_age_seconds,
            )


def available_balances_by_currency(
    snapshot: BalanceSnapshot,
) -> dict[Currency, float]:
    totals: dict[Currency, float] = defaultdict(float)
    for record in snapshot.records:
        totals[record.currency] += float(record.available_balance)
    return dict(totals)


def required_liquidity_by_currency(
    snapshot: BalanceSnapshot,
) -> dict[Currency, float]:
    totals: dict[Currency, float] = defaultdict(float)
    for record in snapshot.records:
        totals[record.currency] += float(record.required_liquidity)
    return dict(totals)


def scheduled_outflows_by_currency(
    snapshot: SettlementSnapshot,
    *,
    through: datetime | None = None,
) -> dict[Currency, float]:
    cutoff = _ensure_aware(through) if through is not None else None
    totals: dict[Currency, float] = defaultdict(float)

    for record in snapshot.records:
        if record.direction != SettlementDirection.outflow:
            continue
        if record.status not in {SettlementStatus.pending, SettlementStatus.scheduled}:
            continue
        if cutoff is not None and _ensure_aware(record.due_at) > cutoff:
            continue
        totals[record.currency] += float(record.amount)

    return dict(totals)


def deterministic_base_variance(
    *,
    available_balance: float,
    required_liquidity: float,
) -> float:
    return float(available_balance) - float(required_liquidity)


def deterministic_projected_requirement(
    *,
    required_liquidity: float,
    scheduled_outflows: float,
) -> float:
    return float(required_liquidity) + float(scheduled_outflows)


def deterministic_projected_shortfall(
    *,
    available_balance: float,
    required_liquidity: float,
    scheduled_outflows: float,
) -> float:
    requirement = deterministic_projected_requirement(
        required_liquidity=required_liquidity,
        scheduled_outflows=scheduled_outflows,
    )
    return max(0.0, requirement - float(available_balance))


def deterministic_surplus(
    *,
    available_balance: float,
    required_liquidity: float,
    minimum_buffer: float = 0.0,
) -> float:
    protected = float(required_liquidity) + float(minimum_buffer)
    return max(0.0, float(available_balance) - protected)
