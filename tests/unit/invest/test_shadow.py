"""Forward-only shadow protocol: frozen, prospective and idempotent."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import shadow

D = [date(2026, 11, 4) + timedelta(days=i) for i in range(6)]
PROTOCOL: Dict[str, Any] = {
    "protocol_id": "TEST_SHADOW", "version": 1, "registered_at": "2026-11-05",
    "universe": {"cohort": "ESTABLISHED_HISTORY", "symbols": ["AAA", "BBB"],
                 "excluded_identities": []}, "strategies": ["CASH", "EQUAL_WEIGHT"],
    "benchmark": "EQUAL_WEIGHT", "cost_assumptions": "UNKNOWN", "horizon": "OPEN_ENDED",
    "no_execution_authority": shadow.NO_EXECUTION,
}


def _closes(step: str = "1") -> Dict[str, Dict[date, Decimal]]:
    return {"AAA": {d: Decimal("100") + Decimal(step) * i for i, d in enumerate(D)},
            "BBB": {d: Decimal("50") + Decimal(step) * i for i, d in enumerate(D)}}


def test_protocol_is_frozen_and_immutable(tmp_path: Path) -> None:
    path = tmp_path / "protocol.json"
    doc = shadow.register_protocol(PROTOCOL, path)
    assert doc["sha256"] == shadow.protocol_hash(PROTOCOL)
    assert shadow.register_protocol(PROTOCOL, path)["sha256"] == doc["sha256"]
    changed = {**PROTOCOL, "benchmark": "CASH"}
    with pytest.raises(DataContractError, match="SHADOW_PROTOCOL_IMMUTABLE"):
        shadow.register_protocol(changed, path)
    tampered = {**doc, "sha256": "0" * 64}
    path.write_text(__import__("json").dumps(tampered), encoding="utf-8")
    with pytest.raises(DataContractError, match="SHADOW_PROTOCOL_HASH_MISMATCH"):
        shadow.load_protocol(path)


def test_no_retroactive_signal_before_registration(tmp_path: Path) -> None:
    doc = shadow.register_protocol(PROTOCOL, tmp_path / "p.json")
    with pytest.raises(DataContractError, match="SHADOW_NOT_PROSPECTIVE"):
        shadow.evaluate_session(doc, _closes(), {"AAA": Decimal("0.5"), "BBB": Decimal("0.5")},
                                ["AAA", "BBB"], date(2026, 11, 5), tmp_path / "j.json")


def test_signal_is_recorded_once_and_outcome_is_forward_only(tmp_path: Path) -> None:
    doc = shadow.register_protocol(PROTOCOL, tmp_path / "p.json")
    journal = tmp_path / "j.json"
    closes = _closes()
    first = shadow.evaluate_session(doc, closes, {"AAA": Decimal("0.5"), "BBB": Decimal("0.5")},
                                    ["AAA", "BBB"], D[4], journal, min_sessions=1)
    assert first["status"] == "OBSERVED" and first["kind"] == "FORWARD_SHADOW_OBSERVATION"
    assert first["execution_authority"] == "NONE" and first["not_a_trade"] is True
    again = shadow.evaluate_session(doc, closes, {"AAA": Decimal("0.5"), "BBB": Decimal("0.5")},
                                    ["AAA", "BBB"], D[4], journal, min_sessions=1)
    assert again["status"] == "ALREADY_RECORDED"
    assert shadow.report(journal)["signals"] == 1
    outcomes = shadow.observe_outcomes(journal, closes, ["AAA", "BBB"])
    assert len(outcomes) == 1 and outcomes[0]["from_session"] == D[4].isoformat()
    assert outcomes[0]["basis"] == "PRICE_RETURN_ONLY"
    assert "strategy_return" in outcomes[0] and "benchmark_return" in outcomes[0]
    assert shadow.observe_outcomes(journal, closes, ["AAA", "BBB"]) == []
    report = shadow.report(journal)
    assert report["forward_observations"] == 1
    assert report["statistical_validation"] == "STATISTICAL_VALIDATION_NOT_ESTABLISHED"
    assert report["execution_authority"] == "NONE"


def test_a_blocked_panel_records_no_performance(tmp_path: Path) -> None:
    doc = shadow.register_protocol(PROTOCOL, tmp_path / "p.json")
    thin = {"AAA": {D[1]: Decimal("100"), D[2]: Decimal("101")}, "BBB": {D[2]: Decimal("50")}}
    blocked = shadow.evaluate_session(doc, thin, {"AAA": Decimal("0.5"), "BBB": Decimal("0.5")},
                                      ["AAA", "BBB"], D[2], tmp_path / "j.json", min_sessions=1)
    assert blocked["status"] == "BLOCKED" and blocked.get("strategy_id") is None
    assert "equal_weight_price_return" not in blocked


def test_no_data_after_the_cutoff_enters_the_signal(tmp_path: Path) -> None:
    doc = shadow.register_protocol(PROTOCOL, tmp_path / "p.json")
    closes = _closes()
    entry = shadow.evaluate_session(doc, closes, {"AAA": Decimal("0.5"), "BBB": Decimal("0.5")},
                                    ["AAA", "BBB"], D[4], tmp_path / "j.json", min_sessions=1)
    assert entry["panel_sessions"] == len([d for d in D if d <= D[4]])
    assert entry["decision_cutoff"] == D[4].isoformat()


def test_frozen_universe_cannot_be_trimmed(tmp_path: Path) -> None:
    doc = shadow.register_protocol(PROTOCOL, tmp_path / "p.json")
    with pytest.raises(DataContractError, match="SHADOW_UNIVERSE_MISMATCH"):
        shadow.evaluate_session(doc, _closes(), {"AAA": Decimal("1")}, ["AAA"], D[4],
                                tmp_path / "j.json", min_sessions=1)


def test_a_quarantined_constituent_blocks_instead_of_renormalising(tmp_path: Path) -> None:
    from acash.invest import security_identity as si
    protocol = {**PROTOCOL, "protocol_id": "TEST_WITH_SPCX",
                "universe": {"symbols": ["AAA", "SPCX"], "excluded_identities": []}}
    doc = shadow.register_protocol(protocol, tmp_path / "p.json")
    days = [date(2026, 3, 2), date(2026, 7, 1), D[4]]
    closes = {"AAA": {d: Decimal("100") + i for i, d in enumerate(days)},
              "SPCX": {days[0]: Decimal("22"), days[1]: Decimal("180"), D[4]: Decimal("190")}}
    entry = shadow.evaluate_session(doc, closes, {"AAA": Decimal("0.5"), "SPCX": Decimal("0.5")},
                                    ["AAA", "SPCX"], D[4], tmp_path / "j.json",
                                    registry=si.load_registry(), min_sessions=1)
    assert entry["status"] == "BLOCKED" and entry["reason"] == "CONSTITUENT_NOT_QUALIFIED"
    assert entry["detail"] == ["SPCX"]
