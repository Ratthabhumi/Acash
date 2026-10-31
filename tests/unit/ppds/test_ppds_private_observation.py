"""Local-private observation path: golden values, trust boundary and fail-closed contract."""

from __future__ import annotations

import copy
import json
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


def test_golden_nav_in_both_report_currencies() -> None:
    summary = po.book_summary(_book(_doc()))
    thb, usd = summary["analytics"]["THB"], summary["analytics"]["USD"]
    assert (thb["nav"], thb["securities_value"], thb["settled_cash"]) == ("134691.50", "97350.00", "37341.50")
    assert thb["accrued_interest_excluded_from_nav"] == "13.20"
    assert usd["nav"] == "4081.56"
    assert abs(Decimal(thb["conservation_residual"])) <= po.CONSERVATION_TOLERANCE


def test_classification_never_inferred_from_sub_portfolio_name() -> None:
    thb = po.book_summary(_book(_doc()))["analytics"]["THB"]
    alloc = thb["allocation_by_classification"]
    assert alloc["CORE_DIVERSIFIED"]["value"] == "70125.00"
    assert alloc["UNKNOWN"]["value"] == "3300.00"
    assert alloc["THEMATIC"]["value"] == "17325.00"
    assert sum(Decimal(v["weight"]) for v in alloc.values()) == Decimal("0.9999")


def test_unrealized_pnl_is_security_currency_only() -> None:
    thb = po.book_summary(_book(_doc()))["analytics"]["THB"]
    assert thb["unrealized_pnl_security_currency"] == {"USD": "20.00"}
    assert "FX_COMPONENT_NOT_ESTABLISHED" in thb["unrealized_pnl_status"]


def test_reconciliation_verdicts() -> None:
    verdicts = {(r["security_id"], r["sub_portfolio"]): r["verdict"] for r in po.book_summary(_book(_doc()))["reconciliation"]}
    assert verdicts[("SYNMOON", "Theme")] == "UNEXPLAINED_DIFFERENCE"
    assert verdicts[("SYNIDX", "Theme")] == "NOT_DISPLAYED"
    assert verdicts[("SYNIDX", "Core")] == "CONSISTENT_WITHIN_DISPLAY_ROUNDING"


def test_snapshot_only_state_and_governance() -> None:
    summary = po.book_summary(_book(_doc()))
    assert summary["support_state"] == "SNAPSHOT_ONLY"
    assert summary["performance_status"] == "PERFORMANCE_NOT_ESTABLISHED"
    assert summary["governance"]["trading_authority"] == "NONE"
    assert summary["governance"]["d5_eligible"] is False
    assert summary["governance"]["order_controls"] is None
    concentration = summary["analytics"]["THB"]["concentration"]
    assert concentration["look_through_status"] == "OVERLAP_NOT_ESTABLISHED"


def test_stress_is_labelled_illustrative_and_gaps_not_evaluated() -> None:
    stress = po.book_summary(_book(_doc()))["analytics"]["THB"]["stress_illustrative"]
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
    a = po.book_summary(_book(doc))["analytics"]
    b = po.book_summary(_book(shuffled))["analytics"]
    assert a == b


def test_ledger_lineage_is_deterministic() -> None:
    first, second = _book(_doc()), _book(_doc())
    assert {k: v.head_sha256 for k, v in first.ledgers.items()} == {k: v.head_sha256 for k, v in second.ledgers.items()}


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
    (_set("observed_at", "2026-11-01T09:00:00"), "PRIVATE_OBSERVED_AT_NAIVE"),
    (_set("data_class", "REAL"), "PRIVATE_DATA_CLASS_INVALID"),
    (_set("schema", "OTHER"), "PRIVATE_SCHEMA_MISMATCH"),
    (_set("accounts.1.account_ref", "BROKER_A_MAIN"), "PRIVATE_DUPLICATE_ACCOUNT_REF"),
    (_set("accounts.0.account_ref", "ACC_1234567"), "PRIVATE_REF_NOT_OPAQUE"),
    (_set("accounts.0.positions.0.sub_portfolio", "Acct 123456789"), "PRIVATE_LABEL_INVALID"),
    (_set("accounts.0.positions.1.security_id", "SYNIDX"), "PRIVATE_DUPLICATE_POSITION_LINE"),
    (_set("accounts.0.positions.4.security_id", "SYNNONE"), "PRIVATE_PRICE_MISSING"),
    (_set("prices.0.as_of", "2026-10-31"), "PRIVATE_PRICE_DATE_MISMATCH"),
    (_set("fx_rates.0.as_of", "2026-10-31"), "PRIVATE_FX_DATE_MISMATCH"),
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


def test_unused_price_rejected() -> None:
    doc = _doc()
    doc["prices"].append({"security_id": "SYNX", "currency": "USD", "price": "1.00", "as_of": "2026-11-01", "source_id": "S"})
    with pytest.raises(DataContractError, match="PRIVATE_UNUSED_PRICE"):
        po.parse_snapshot(doc)


def test_missing_fx_for_account_base_fails_in_ppds() -> None:
    doc = _doc()
    doc["fx_rates"] = [r for r in doc["fx_rates"] if r["from"] != "USD"]
    with pytest.raises(DataContractError, match="FX"):
        _book(doc)


def test_missing_cost_basis_fails_closed() -> None:
    doc = _doc()
    doc["accounts"][0]["positions"][0]["cost_basis_total"] = None
    with pytest.raises(DataContractError, match="PRIVATE_COST_BASIS_REQUIRED"):
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


def test_staleness_window() -> None:
    book = _book(_doc())
    assert po.valuation_age_days(book, date(2026, 11, 12)) == {"valuation_age_days": 11, "stale": True}
    with pytest.raises(DataContractError, match="PRIVATE_REPORT_DATE_BEFORE_VALUATION"):
        po.valuation_age_days(book, date(2026, 10, 31))


def test_private_location_boundary(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    po.assert_private_location(root / "data" / "private" / "s.json", root)
    po.assert_private_location(tmp_path / "elsewhere" / "s.json", root)
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        po.assert_private_location(root / "docs" / "s.json", root)
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        po.assert_private_location(root / "data" / "privateish" / "s.json", root)


def test_owner_private_snapshot_rejected_inside_tracked_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    doc = _doc()
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    tracked = tmp_path / "docs" / "owner.json"
    tracked.parent.mkdir(parents=True)
    tracked.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        po.load_snapshot(tracked)
    private = tmp_path / "data" / "private" / "owner.json"
    private.parent.mkdir(parents=True)
    private.write_text(json.dumps(doc), encoding="utf-8")
    assert po.load_snapshot(private).data_class == "OWNER_PRIVATE_OBSERVATION"


def test_gitignore_protects_private_directory() -> None:
    lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/data/private/" in lines
