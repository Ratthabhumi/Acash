"""Dated broker-display captures: no snapshot rewrite, no transaction, no global weight from a share."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import broker_positions as bp

ROWS = [
    {"security_id": "META", "displayed_value": "6190.83", "displayed_currency": "THB",
     "displayed_subportfolio_weight": "0.3132"},
    {"security_id": "GE", "displayed_value": "3637.46", "displayed_currency": "THB",
     "displayed_subportfolio_weight": "0.1840"},
    {"security_id": "HOOD", "displayed_value": "3401.60", "displayed_currency": "THB",
     "displayed_subportfolio_weight": "0.1721", "displayed_price": "87.26"},
    {"security_id": "ACHR", "displayed_value": "3338.04", "displayed_currency": "THB",
     "displayed_subportfolio_weight": "0.1689"},
]


def _capture(doc: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(observation_id="DIME_NEWWAVE_20261105T0015+07", broker="DIME",
                observed_at="2026-11-05T00:15:00+07:00", currency="THB", subportfolio="Newwave",
                rows=ROWS, source="DIME_SCREENSHOT")
    base.update(kwargs)
    return bp.record(doc, **base)


def test_capture_is_dated_evidence_not_a_transaction(tmp_path: Path) -> None:
    doc = _capture(bp.empty(tmp_path / "obs.json"))
    entry = doc["observations"][0]
    assert entry["observed_at"] == "2026-11-05T00:15:00+07:00"
    assert entry["evidence_status"] == "BROKER_DISPLAYED_OBSERVATION"
    assert entry["is_transaction"] is False and entry["creates_position"] is False
    assert entry["subportfolio_rows_complete"] is False
    assert {r["security_id"] for r in entry["rows"]} == {"META", "GE", "HOOD", "ACHR"}
    # No quantity or trade field exists, so a capture cannot become a fill.
    assert all("quantity" not in r for r in entry["rows"])


def test_same_observation_twice_is_refused_and_a_new_date_is_allowed(tmp_path: Path) -> None:
    doc = _capture(bp.empty(tmp_path / "obs.json"))
    with pytest.raises(DataContractError, match="BROKER_OBSERVATION_DUPLICATE"):
        _capture(doc)
    later = _capture(doc, observation_id="DIME_NEWWAVE_20261105T2340+07",
                     observed_at="2026-11-05T23:40:00+07:00")
    assert len(later["observations"]) == 2


def test_naive_timestamp_and_smuggled_fields_are_refused(tmp_path: Path) -> None:
    with pytest.raises(DataContractError, match="BROKER_OBSERVATION_INVALID"):
        _capture(bp.empty(tmp_path / "obs.json"), observed_at="2026-11-05T00:15:00")
    with pytest.raises(DataContractError, match="unexpected field"):
        _capture(bp.empty(tmp_path / "obs.json"), rows=[{**ROWS[0], "quantity": "1.1619193"}])
    with pytest.raises(DataContractError, match="BROKER_OBSERVATION_INVALID"):
        _capture(bp.empty(tmp_path / "obs.json"), rows=[{"security_id": "HOOD", "displayed_value": "0"}])


def test_subportfolio_share_is_not_a_global_weight(tmp_path: Path) -> None:
    doc = _capture(bp.empty(tmp_path / "obs.json"))
    rows = doc["observations"][0]["rows"]
    shares = bp.subportfolio_weights(rows)
    assert shares["HOOD"] == Decimal("3401.60") / Decimal("16567.93")
    # The broker's 17.21% is a share of a five-asset sub-portfolio; the four visible rows imply 20.53%,
    # which is precisely why a displayed share is never reused as a computed weight.
    assert abs(shares["HOOD"] - Decimal("0.1721")) > Decimal("0.02")
    # The global weight needs the portfolio total on the same date; it is two orders smaller.
    hood_global = bp.global_weight(Decimal("3401.60"), Decimal("208740.01"))
    assert hood_global < Decimal("0.02") and hood_global != Decimal("0.1721")


def test_ge_and_gev_are_never_merged(tmp_path: Path) -> None:
    rows = ROWS + [{"security_id": "GEV", "displayed_value": "3400.00", "displayed_currency": "THB"}]
    doc = _capture(bp.empty(tmp_path / "obs.json"), rows=rows)
    symbols = [r["security_id"] for r in doc["observations"][0]["rows"]]
    assert "GE" in symbols and "GEV" in symbols and len(symbols) == len(set(symbols))
    with pytest.raises(DataContractError, match="security_id"):
        _capture(bp.empty(tmp_path / "o2.json"), rows=ROWS + [ROWS[1]])


def test_write_is_atomic_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "obs.json"
    bp.write(_capture(bp.empty(path)), path)
    assert json.loads(path.read_text(encoding="utf-8"))["schema"] == bp.SCHEMA
    assert not list(tmp_path.glob("*.tmp"))
    assert bp.empty(path)["observations"][0]["observation_id"] == "DIME_NEWWAVE_20261105T0015+07"
