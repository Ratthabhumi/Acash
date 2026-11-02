"""Local-private observation path: golden values, trust boundary and fail-closed contract."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.ppds import private_observation as po

FIXTURE = Path("docs/research/evidence/upi_v1_synthetic_snapshot.json")


def _doc() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return doc


def _book(doc: Dict[str, Any]) -> po.PortfolioBook:
    return po.build_book(po.parse_snapshot(doc))


def _thb(doc: Dict[str, Any]) -> Dict[str, Any]:
    analytics: Dict[str, Any] = po.book_summary(_book(doc))["analytics"]["THB"]
    return analytics


def _position(doc: Dict[str, Any], security: str, sub: str) -> Dict[str, Any]:
    for pos in doc["accounts"][0]["positions"]:
        if pos["security_id"] == security and pos["sub_portfolio"] == sub:
            found: Dict[str, Any] = pos
            return found
    raise KeyError(security)


def _ratify(root: Path) -> None:
    record = root / po.AUTHORIZATION_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"capability": po.AUTHORIZED_CAPABILITY, "status": "RATIFIED",
                                  "ratified_by": "OWNER", "ratified_on": "2026-11-01",
                                  "scope_schemas": [po.SCHEMA]}), encoding="utf-8")


def test_golden_nav_in_both_report_currencies() -> None:
    summary = po.book_summary(_book(_doc()))
    thb, usd = summary["analytics"]["THB"], summary["analytics"]["USD"]
    assert (thb["nav"], thb["securities_value"], thb["settled_cash"]) == ("134691.50", "97350.00", "37341.50")
    assert thb["accrued_interest_excluded_from_nav"] == "13.20"
    assert usd["nav"] == "4081.56"
    assert abs(Decimal(thb["conservation_residual"])) <= po.CONSERVATION_TOLERANCE


def test_classification_never_inferred_from_sub_portfolio_name() -> None:
    alloc = _thb(_doc())["allocation_by_classification"]
    assert alloc["CORE_DIVERSIFIED"]["value"] == "70125.00"
    assert alloc["UNKNOWN"]["value"] == "3300.00"
    assert alloc["THEMATIC"]["value"] == "17325.00"


def test_mixed_known_and_unknown_cost_basis() -> None:
    pnl = _thb(_doc())["unrealized_pnl"]
    assert pnl["status"] == "PARTIAL_COST_BASIS"
    assert pnl["unrealized_pnl_security_currency_known_cost_subset"] == {"USD": "30.00"}
    assert pnl["cost_basis_value_coverage"] == "0.9661"
    statuses = {(r["security_id"], r["sub_portfolio"]): r["status"] for r in pnl["lines"]}
    assert statuses[("SYNNEW", "Unsorted")] == "COST_BASIS_UNKNOWN"


def test_nav_only_snapshot_values_without_pnl() -> None:
    doc = _doc()
    for pos in doc["accounts"][0]["positions"]:
        pos["cost_basis_total"], pos["cost_basis_currency"] = None, None
    thb = _thb(doc)
    assert thb["nav"] == "134691.50"
    assert thb["unrealized_pnl"]["status"] == "NAV_ONLY"
    assert thb["unrealized_pnl"]["unrealized_pnl_security_currency_known_cost_subset"] == {}


def test_cost_in_other_currency_is_not_compared_with_price() -> None:
    doc = _doc()
    _position(doc, "SYNIDX", "Core")["cost_basis_currency"] = "THB"
    pnl = _thb(doc)["unrealized_pnl"]
    statuses = {(r["security_id"], r["sub_portfolio"]): r["status"] for r in pnl["lines"]}
    assert statuses[("SYNIDX", "Core")] == "COST_CURRENCY_DIFFERS_PNL_NOT_ESTABLISHED"
    assert pnl["unrealized_pnl_security_currency_known_cost_subset"] == {"USD": "-170.00"}


def test_reconciliation_verdicts_and_cross_currency() -> None:
    rows = {(r["security_id"], r["sub_portfolio"]): r for r in po.book_summary(_book(_doc()))["reconciliation"]}
    assert rows[("SYNMOON", "Theme")]["verdict"] == "UNEXPLAINED_DIFFERENCE"
    assert rows[("SYNIDX", "Theme")]["verdict"] == "NOT_DISPLAYED"
    assert rows[("SYNTECH", "Theme")]["verdict"] == "CONSISTENT_WITHIN_DISPLAY_ROUNDING"
    assert rows[("SYNTECH", "Theme")]["currency"] == "THB"


@pytest.mark.parametrize("observed, verdict", [
    ("2000", "CONSISTENT_WITHIN_DISPLAY_ROUNDING"),
    ("2000.4", "UNEXPLAINED_DIFFERENCE"),
    ("2001", "UNEXPLAINED_DIFFERENCE"),
])
def test_tolerance_follows_displayed_precision(observed: str, verdict: str) -> None:
    doc = _doc()
    _position(doc, "SYNIDX", "Core")["observed_market_value"] = observed
    rows = {(r["security_id"], r["sub_portfolio"]): r for r in po.book_summary(_book(doc))["reconciliation"]}
    assert rows[("SYNIDX", "Core")]["verdict"] == verdict


def test_unconvertible_observed_currency_is_reported_not_compared() -> None:
    doc = _doc()
    _position(doc, "SYNIDX", "Core")["observed_market_value_currency"] = "EUR"
    rows = {(r["security_id"], r["sub_portfolio"]): r for r in po.book_summary(_book(doc))["reconciliation"]}
    assert rows[("SYNIDX", "Core")]["verdict"] == "CURRENCY_CONVERSION_NOT_AVAILABLE"


def test_weekend_observation_uses_previous_session() -> None:
    alignment = po.book_summary(_book(_doc()))["time_alignment"]
    assert alignment["valuation_date"] == "2026-10-30"
    assert alignment["observation_lag_days"] == 2
    assert alignment["market_session_calendar_check"] == "NOT_PERFORMED_IN_PACK"


@pytest.mark.parametrize("observed_at, lag", [
    ("2026-10-31T06:00:00+07:00", 1),
    ("2026-10-30T17:00:00-04:00", 0),
    ("2026-10-30T23:30:00-04:00", 0),
])
def test_bangkok_and_new_york_observation_times(observed_at: str, lag: int) -> None:
    doc = _doc()
    doc["observed_at"] = observed_at
    doc["prices"][0].pop("published_at")
    assert po.time_alignment(po.parse_snapshot(doc))["observation_lag_days"] == lag


def test_stale_valuation_is_labelled() -> None:
    book = _book(_doc())
    assert po.valuation_age_days(book, date(2026, 11, 9)) == {"valuation_age_days": 10, "stale": True}
    with pytest.raises(DataContractError, match="PRIVATE_REPORT_DATE_BEFORE_VALUATION"):
        po.valuation_age_days(book, date(2026, 10, 29))


def test_snapshot_only_state_and_governance() -> None:
    summary = po.book_summary(_book(_doc()))
    assert summary["support_state"] == "SNAPSHOT_ONLY"
    assert summary["performance_status"] == "PERFORMANCE_NOT_ESTABLISHED"
    assert summary["governance"]["trading_authority"] == "NONE"
    assert summary["governance"]["d5_eligible"] is False
    assert summary["governance"]["order_controls"] is None
    assert summary["analytics"]["THB"]["concentration"]["look_through_status"] == "OVERLAP_NOT_ESTABLISHED"


def test_stress_is_labelled_illustrative_and_gaps_not_evaluated() -> None:
    stress = _thb(_doc())["stress_illustrative"]
    assert stress["label"] == "ILLUSTRATIVE_NOT_FORECAST"
    deltas = {s["scenario"]: s["nav_delta"] for s in stress["scenarios"]}
    assert deltas["EQUITY_DRAWDOWN_30"] == "-29205.00"
    assert deltas["THEMATIC_SPECULATIVE_DRAWDOWN_50"] == "-11962.50"
    assert stress["not_evaluated"]["TECH_SELLOFF"] == "NOT_EVALUATED_SECTOR_DATA_MISSING"


def test_permutation_invariance_of_analytics() -> None:
    doc = _doc()
    shuffled = copy.deepcopy(doc)
    shuffled["accounts"].reverse()
    for account in shuffled["accounts"]:
        account["positions"].reverse()
    shuffled["prices"].reverse()
    assert po.book_summary(_book(doc))["analytics"] == po.book_summary(_book(shuffled))["analytics"]


def test_valuation_view_lineage_is_deterministic() -> None:
    first, second = _book(_doc()), _book(_doc())
    assert {k: v.sha256 for k, v in first.views.items()} == {k: v.sha256 for k, v in second.views.items()}


def _set(path: str, value: Any) -> Callable[[Dict[str, Any]], None]:
    def mutate(doc: Dict[str, Any]) -> None:
        target: Any = doc
        keys = path.split(".")
        for key in keys[:-1]:
            target = target[int(key)] if key.isdigit() else target[key]
        last = keys[-1]
        target[int(last) if last.isdigit() else last] = value
    return mutate


@pytest.mark.parametrize("mutate, code", [
    (_set("accounts.0.positions.0.quantity", 20.0), "PRIVATE_NUMBER_MUST_BE_STRING"),
    (_set("accounts.0.positions.0.quantity", "0"), "PRIVATE_NONPOSITIVE_VALUE"),
    (_set("accounts.0.positions.0.quantity", "NaN"), "PRIVATE_NONFINITE_DECIMAL"),
    (_set("accounts.0.cash.0.amount", "-1"), "PRIVATE_NEGATIVE_VALUE"),
    (_set("accounts.0.extra", "x"), "PRIVATE_UNKNOWN_FIELDS"),
    (_set("observed_at", "2026-11-01T09:00:00"), "PRIVATE_TIMESTAMP_NAIVE"),
    (_set("valuation_date", "2026-11-02"), "PRIVATE_VALUATION_DATE_AFTER_OBSERVATION"),
    (_set("prices.0.published_at", "2026-11-02T00:00:00+07:00"), "PRIVATE_PRICE_PUBLISHED_AFTER_OBSERVATION"),
    (_set("prices.0.published_at", "2026-10-30T16:00:00"), "PRIVATE_TIMESTAMP_NAIVE"),
    (_set("data_class", "REAL"), "PRIVATE_DATA_CLASS_INVALID"),
    (_set("schema", "ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1"), "PRIVATE_SCHEMA_MISMATCH"),
    (_set("accounts.1.account_ref", "BROKER_A_MAIN"), "PRIVATE_DUPLICATE_ACCOUNT_REF"),
    (_set("accounts.0.account_ref", "ACC_1234567"), "PRIVATE_REF_NOT_OPAQUE"),
    (_set("accounts.0.positions.0.sub_portfolio", "Acct 123456789"), "PRIVATE_LABEL_INVALID"),
    (_set("accounts.0.positions.1.security_id", "SYNIDX"), "PRIVATE_DUPLICATE_POSITION_LINE"),
    (_set("accounts.0.positions.4.security_id", "SYNNONE"), "PRIVATE_PRICE_MISSING"),
    (_set("accounts.0.positions.0.cost_basis_currency", None), "PRIVATE_AMOUNT_CURRENCY_PAIR_INCOMPLETE"),
    (_set("accounts.0.positions.0.observed_market_value_currency", None), "PRIVATE_AMOUNT_CURRENCY_PAIR_INCOMPLETE"),
    (_set("prices.0.as_of", "2026-10-29"), "PRIVATE_PRICE_DATE_MISMATCH"),
    (_set("fx_rates.0.as_of", "2026-10-29"), "PRIVATE_FX_DATE_MISMATCH"),
    (_set("fx_rates.1.from", "USD"), "PRIVATE_FX_DUPLICATE_OR_IDENTITY"),
    (_set("securities.0.evidence_ref", None), "PRIVATE_CLASSIFICATION_EVIDENCE_REQUIRED"),
    (_set("securities.0.classification", "CASH"), "PRIVATE_CLASSIFICATION_EVIDENCE_REQUIRED"),
    (_set("securities.0.methodology", "NOT_CLASSIFIED"), "PRIVATE_CLASSIFICATION_WITHOUT_METHODOLOGY"),
    (_set("securities.0.security_id", "SYNOTHER"), "PRIVATE_CLASSIFICATION_FOR_UNHELD_SECURITY"),
    (_set("accounts.0.cash.0.kind", "PENDING"), "PRIVATE_CASH_KIND_INVALID"),
    (_set("accounts.0.role", "TRADING"), "PRIVATE_ACCOUNT_ROLE_INVALID"),
    (_set("report_currencies", ["USD"]), "PRIVATE_REPORT_CURRENCIES_INVALID"),
])
def test_malformed_snapshots_fail_closed(mutate: Callable[[Dict[str, Any]], None], code: str) -> None:
    doc = _doc()
    mutate(doc)
    with pytest.raises(DataContractError, match=code):
        po.parse_snapshot(doc)


def test_errors_never_echo_amounts() -> None:
    doc = _doc()
    _position(doc, "SYNIDX", "Core")["quantity"] = "98765.4x"
    with pytest.raises(DataContractError) as excinfo:
        po.parse_snapshot(doc)
    assert "98765" not in str(excinfo.value)


def test_unused_price_rejected() -> None:
    doc = _doc()
    doc["prices"].append({"security_id": "SYNX", "currency": "USD", "price": "1.00", "as_of": "2026-10-30", "source_id": "S"})
    with pytest.raises(DataContractError, match="PRIVATE_UNUSED_PRICE"):
        po.parse_snapshot(doc)


def test_missing_fx_for_account_base_fails_in_ppds() -> None:
    doc = _doc()
    doc["fx_rates"] = [r for r in doc["fx_rates"] if r["from"] != "USD"]
    with pytest.raises(DataContractError, match="FX"):
        _book(doc)


def test_zero_nav_has_no_weights() -> None:
    doc = _doc()
    doc["accounts"] = [{"account_ref": "EMPTY_CASH", "broker": "BANK_C", "role": "OTHER", "base_currency": "THB",
                        "cash": [{"currency": "THB", "amount": "0", "kind": "SETTLED", "sub_portfolio": None}], "positions": []}]
    doc["prices"], doc["securities"] = [], []
    with pytest.raises(DataContractError, match="PRIVATE_NAV_NONPOSITIVE"):
        po.book_summary(_book(doc))


def test_duplicate_snapshots_detected() -> None:
    snap = po.parse_snapshot(_doc())
    with pytest.raises(DataContractError, match="PRIVATE_DUPLICATE_SNAPSHOT"):
        po.assert_no_duplicate_snapshots([snap, snap])


def test_private_location_boundary(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    po.assert_private_location(root / "data" / "private" / "s.json", root)
    po.assert_private_location(tmp_path / "elsewhere" / "s.json", root)
    for bad in (root / "docs" / "s.json", root / "data" / "privateish" / "s.json",
                root / "data" / "private" / ".." / ".." / "docs" / "s.json"):
        with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
            po.assert_private_location(bad, root)


def test_symlink_out_of_private_dir_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "data" / "private").mkdir(parents=True)
    link = root / "data" / "private" / "escape"
    try:
        os.symlink(root / "docs", link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this host")
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        po.assert_private_location(link / "s.json", root)


def test_owner_private_requires_ratified_decision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    doc = _doc()
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    private = tmp_path / "data" / "private" / "owner.json"
    private.parent.mkdir(parents=True)
    private.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        po.load_snapshot(private)
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        po.build_book(po.parse_snapshot(doc))
    _ratify(tmp_path)
    assert po.load_snapshot(private).data_class == "OWNER_PRIVATE_OBSERVATION"
    tracked = tmp_path / "docs" / "owner.json"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        po.load_snapshot(tracked)


@pytest.mark.parametrize("record", [
    {"capability": po.AUTHORIZED_CAPABILITY, "status": "PROPOSED_NOT_RATIFIED", "ratified_by": None, "ratified_on": None},
    {"capability": po.AUTHORIZED_CAPABILITY, "status": "RATIFIED", "ratified_by": "AI_AGENT", "ratified_on": "2026-11-01"},
    {"capability": "TRADING_AUTHORIZED", "status": "RATIFIED", "ratified_by": "OWNER", "ratified_on": "2026-11-01"},
])
def test_gate_rejects_unratified_or_foreign_records(tmp_path: Path, record: Dict[str, Any]) -> None:
    path = tmp_path / "odr.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert po.private_observation_authorized(path) is False
    assert po.private_observation_authorized(tmp_path / "missing.json") is False


def test_committed_decision_record_is_well_formed() -> None:
    record = json.loads((Path(".") / po.AUTHORIZATION_RECORD).read_text(encoding="utf-8"))
    assert record["capability"] == po.AUTHORIZED_CAPABILITY
    assert {"D5_DATA_ADMITTED", "TRADING_AUTHORIZED"} <= set(record["independent_of"])


def test_oversized_and_malformed_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    big = tmp_path / "big.json"
    big.write_text(json.dumps(_doc()), encoding="utf-8")
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    limit = po.MAX_INPUT_BYTES
    monkeypatch.setattr(po, "MAX_INPUT_BYTES", 100)
    with pytest.raises(DataContractError, match="PRIVATE_SNAPSHOT_TOO_LARGE"):
        po.load_snapshot(big)
    monkeypatch.setattr(po, "MAX_INPUT_BYTES", limit)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(DataContractError, match="PRIVATE_SNAPSHOT_MALFORMED_JSON"):
        po.load_snapshot(bad)


def test_gitignore_protects_private_directory() -> None:
    lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/data/private/" in lines
    if shutil.which("git") is None:
        pytest.skip("git not available")
    result = subprocess.run(["git", "check-ignore", "-q", "data/private/owner_snapshot.json"], check=False)
    assert result.returncode == 0
