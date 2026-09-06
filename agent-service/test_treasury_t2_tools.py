from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from demos.remitly_treasury.domain import Currency
from demos.remitly_treasury.tools import (
    StaleSourceDataError,
    TreasurySourceValidationError,
    available_balances_by_currency,
    deterministic_base_variance,
    deterministic_projected_requirement,
    deterministic_projected_shortfall,
    deterministic_surplus,
    read_balance_snapshot,
    read_funding_policy,
    read_settlement_snapshot,
    required_liquidity_by_currency,
    scheduled_outflows_by_currency,
    validate_balance_freshness,
)


DATA = Path(__file__).parent / "demos" / "remitly_treasury" / "data"


def test_strict_readers():
    balances = read_balance_snapshot(DATA / "balances.json")
    settlements = read_settlement_snapshot(DATA / "obligations.json")
    policy = read_funding_policy(DATA / "funding_policy.json")
    assert len(balances.records) == 3
    assert len(settlements.records) == 2
    assert policy.manual_approval_threshold == 250000


def test_invalid_source_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.json"
        path.write_text(json.dumps({"bad": "shape"}), encoding="utf-8")
        try:
            read_balance_snapshot(path)
        except TreasurySourceValidationError:
            return
        raise AssertionError("Invalid balance JSON was accepted.")


def test_balance_freshness():
    balances = read_balance_snapshot(DATA / "balances.json")
    validate_balance_freshness(
        balances,
        reference_time=datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc),
        max_age_seconds=3600,
    )


def test_stale_balance_is_blocked():
    balances = read_balance_snapshot(DATA / "balances.json")
    try:
        validate_balance_freshness(
            balances,
            reference_time=datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc),
            max_age_seconds=3600,
        )
    except StaleSourceDataError:
        return
    raise AssertionError("Stale balance data was accepted.")


def test_currency_aggregations():
    balances = read_balance_snapshot(DATA / "balances.json")
    available = available_balances_by_currency(balances)
    required = required_liquidity_by_currency(balances)
    assert available[Currency.GBP] == 1200000
    assert required[Currency.GBP] == 900000
    assert available[Currency.EUR] == 450000
    assert required[Currency.EUR] == 700000


def test_settlement_outflow_aggregation():
    settlements = read_settlement_snapshot(DATA / "obligations.json")
    outflows = scheduled_outflows_by_currency(settlements)
    assert outflows[Currency.EUR] == 180000
    assert outflows[Currency.GBP] == 50000


def test_deterministic_arithmetic():
    assert deterministic_base_variance(
        available_balance=450000,
        required_liquidity=700000,
    ) == -250000
    assert deterministic_projected_requirement(
        required_liquidity=700000,
        scheduled_outflows=180000,
    ) == 880000
    assert deterministic_projected_shortfall(
        available_balance=450000,
        required_liquidity=700000,
        scheduled_outflows=180000,
    ) == 430000
    assert deterministic_surplus(
        available_balance=1200000,
        required_liquidity=900000,
        minimum_buffer=100000,
    ) == 200000


def main():
    test_strict_readers()
    test_invalid_source_is_rejected()
    test_balance_freshness()
    test_stale_balance_is_blocked()
    test_currency_aggregations()
    test_settlement_outflow_aggregation()
    test_deterministic_arithmetic()
    print("PASS: T2 deterministic Treasury readers, freshness validation, aggregation, and arithmetic validated.")


if __name__ == "__main__":
    main()
