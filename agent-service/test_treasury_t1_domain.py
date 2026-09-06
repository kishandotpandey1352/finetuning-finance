from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from demos.remitly_treasury.domain import (
    BalanceSnapshot,
    Currency,
    FundingPolicy,
    SettlementSnapshot,
    TreasuryScenario,
)


DATA = Path(__file__).parent / "demos" / "remitly_treasury" / "data"


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_balances_are_strict_and_traceable():
    snapshot = BalanceSnapshot.model_validate(load_json("balances.json"))
    assert len(snapshot.records) == 3
    assert {r.currency for r in snapshot.records} == {
        Currency.GBP,
        Currency.EUR,
        Currency.USD,
    }
    assert all(r.evidence_id.startswith("BAL-") for r in snapshot.records)


def test_settlements_are_strict_and_traceable():
    snapshot = SettlementSnapshot.model_validate(load_json("obligations.json"))
    assert len(snapshot.records) == 2
    assert all(r.evidence_id.startswith("SET-") for r in snapshot.records)


def test_policy_is_strict_and_has_corridor():
    policy = FundingPolicy.model_validate(load_json("funding_policy.json"))
    assert policy.manual_approval_threshold == 250000
    assert policy.auto_execution_limit == 25000
    assert policy.corridor_enabled(Currency.GBP, Currency.EUR) is True
    assert policy.corridor_enabled(Currency.USD, Currency.EUR) is False
    assert policy.evidence_id.startswith("POL-")


def test_scenario_references_domain_files():
    scenario = TreasuryScenario.model_validate(
        load_json("scenario_eur_shortfall.json")
    )
    assert scenario.balances_file == "balances.json"
    assert scenario.settlements_file == "obligations.json"
    assert scenario.funding_policy_file == "funding_policy.json"


def test_unknown_fields_are_rejected():
    payload = load_json("balances.json")
    payload["unexpected_field"] = "must fail"
    try:
        BalanceSnapshot.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("extra='forbid' did not reject unknown input")


def test_invalid_evidence_namespace_is_rejected():
    payload = load_json("balances.json")
    payload["records"][0]["evidence_id"] = "SET-WRONG-001"
    try:
        BalanceSnapshot.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("invalid balance evidence namespace was accepted")


def main():
    test_balances_are_strict_and_traceable()
    test_settlements_are_strict_and_traceable()
    test_policy_is_strict_and_has_corridor()
    test_scenario_references_domain_files()
    test_unknown_fields_are_rejected()
    test_invalid_evidence_namespace_is_rejected()
    print("PASS: T1 Treasury domain models, mock data, and evidence IDs validated.")


if __name__ == "__main__":
    main()
