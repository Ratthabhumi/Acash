"""V1_2 minimum viable private snapshot: partial evidence, broker totals, residuals, identity, gate scope."""

from __future__ import annotations

import copy
import json
import socket
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import capacity_plan as cp
from acash.invest import preflight as pf
from acash.invest import wealth_pack as wp
from acash.ppds import private_observation as po
from acash.ppds import transactions as tx

FIXTURE = Path("docs/research/evidence/upi_v1_2_synthetic_snapshot.json")
V1_1 = Path("docs/research/evidence/upi_v1_synthetic_snapshot.json")
TXNS = Path("docs/research/evidence/upi_v2_synthetic_transactions.json")
PILOT_PACK_DIR = Path("docs/research/evidence/upi_v1_2_synthetic_pack")
TOTALS_ONLY = Path("docs/research/evidence/upi_v1_2_synthetic_totals_only.json")
TOTALS_ONLY_PACK_DIR = Path("docs/research/evidence/upi_v1_2_synthetic_totals_only_pack")
TARGETS = '{"CORE_DIVERSIFIED": "0.7", "CASH": "0.3"}'


def _doc() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return doc


def _ev(doc: Dict[str, Any], ccy: str = "THB") -> Dict[str, Any]:
    report: Dict[str, Any] = po.evidence_report(po.build_book(po.parse_snapshot(doc)), ccy)
    return report


def _account(report: Dict[str, Any], ref: str) -> Dict[str, Any]:
    found: Dict[str, Any] = next(a for a in report["accounts"] if a["account_ref"] == ref)
    return found


def _acct_doc(doc: Dict[str, Any], ref: str) -> Dict[str, Any]:
    found: Dict[str, Any] = next(a for a in doc["accounts"] if a["account_ref"] == ref)
    return found


def _ratify(root: Path, record: Path, capability: str, schemas: List[str], status: str = "RATIFIED") -> None:
    path = root / record
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"capability": capability, "status": status, "ratified_by": "OWNER",
                                "ratified_on": "2026-11-02", "scope_schemas": schemas}), encoding="utf-8")


def test_golden_evidence_values() -> None:
    ev = _ev(_doc())
    assert ev["valuation_basis"] == {"computed_nav_ppds": "77220.00", "observed_position_value": "8250.00",
                                     "unclassified_holdings_value": "10280.00", "total_best_evidence": "95750.00"}
    assert ev["coverage"] == {"known_value_coverage": "0.8926", "position_level_coverage": "0.7622",
                              "cash_observed_accounts": "3/4", "account_total_reconciliation_coverage": "0.1723",
                              "cost_basis_coverage": "0.4997", "historical_transaction_coverage": "NOT_ESTABLISHED_SNAPSHOT_ONLY"}
    usd = _ev(_doc(), "USD")["valuation_basis"]
    assert (usd["computed_nav_ppds"], usd["unclassified_holdings_value"]) == ("2340.00", "311.52")


def test_evidence_levels_and_total_statuses() -> None:
    ev = _ev(_doc())
    main = _account(ev, "BROKER_D_MAIN")
    assert main["evidence_level"] == "POSITION_MARKET_VALUE_ONLY"
    assert (main["account_total"]["status"], main["account_total"]["difference"]) == ("UNEXPLAINED_DIFFERENCE", "160.00")
    assert [(s["sub_portfolio"], s["status"]) for s in main["sub_portfolio_totals"]] == [
        ("Core", "RECONCILED"), ("Theme", "UNEXPLAINED_DIFFERENCE")]
    assert main["flags"] == ["SUBPORTFOLIO_TOTALS_INFORMATIONAL_ACCOUNT_TOTAL_GOVERNS"]
    assert _account(ev, "BANK_FCD")["account_total"]["status"] == "RECONCILED"
    assert _account(ev, "BROKER_W_QUANT")["account_total"]["status"] == "RECONCILED"
    other = _account(ev, "BROKER_X_OTHER")
    assert (other["evidence_level"], other["account_total"]["status"], other["account_total"]["reason"]) == (
        "ACCOUNT_TOTAL_ONLY", "INSUFFICIENT_EVIDENCE", "NO_COMPONENT_LINES")
    assert other["unclassified_holdings_value"] == "5000.00"
    assert ev["market_session_status"] == "MARKET_SESSION_NOT_VERIFIED"


def test_value_only_positions_never_enter_ppds_nav() -> None:
    summary = po.book_summary(po.build_book(po.parse_snapshot(_doc())))
    assert summary["analytics"]["THB"]["nav"] == "77220.00"
    assert summary["schema"] == po.SCHEMA_V1_2


def test_v1_1_documents_report_without_evidence_block() -> None:
    summary = po.book_summary(po.build_book(po.load_snapshot(V1_1)))
    assert "evidence" not in summary and summary["schema"] == po.SCHEMA


@pytest.mark.parametrize("amount, status, residual", [
    ("2090.00", "RECONCILED", "0.00"),
    ("2090.2", "CONSISTENT_WITH_DISPLAY_ROUNDING", "0.00"),
    ("2091", "UNEXPLAINED_DIFFERENCE", "33.00"),
])
def test_account_total_rounding_policy(amount: str, status: str, residual: str) -> None:
    doc = _doc()
    _acct_doc(doc, "BROKER_D_MAIN")["reported_total"]["amount"] = amount
    main = _account(_ev(doc), "BROKER_D_MAIN")
    assert (main["account_total"]["status"], main["unclassified_holdings_value"]) == (status, residual)


def test_known_value_exceeding_total_is_flagged_not_netted() -> None:
    doc = _doc()
    _acct_doc(doc, "BROKER_D_MAIN")["reported_total"]["amount"] = "2000.00"
    ev = _ev(doc)
    main = _account(ev, "BROKER_D_MAIN")
    assert "KNOWN_VALUE_EXCEEDS_REPORTED_TOTAL" in main["flags"]
    assert main["unclassified_holdings_value"] == "0.00"
    assert ev["valuation_basis"]["total_best_evidence"] == "90470.00"


def test_missing_fx_for_total_leaves_residual_unestablished() -> None:
    doc = _doc()
    _acct_doc(doc, "BROKER_D_MAIN")["reported_total"]["currency"] = "EUR"
    main = _account(_ev(doc), "BROKER_D_MAIN")
    assert (main["account_total"]["status"], main["account_total"]["reason"]) == (
        "RESIDUAL_NOT_ESTABLISHED", "CURRENCY_CONVERSION_NOT_AVAILABLE")
    assert main["flags"] == ["RESIDUAL_NOT_ESTABLISHED_FX_MISSING", "SUBPORTFOLIO_TOTALS_INFORMATIONAL_ACCOUNT_TOTAL_GOVERNS"]
    assert main["unclassified_holdings_value"] == "0.00"


def test_subportfolio_totals_govern_only_without_account_total() -> None:
    doc = _doc()
    del _acct_doc(doc, "BROKER_D_MAIN")["reported_total"]
    doc["accounts"].append({"account_ref": "BROKER_S_SUBS", "broker": "BROKER_S", "role": "OTHER", "base_currency": "THB",
                            "sub_portfolio_totals": [{"sub_portfolio": "Growth", "amount": "700.00", "currency": "THB"}]})
    ev = _ev(doc)
    assert _account(ev, "BROKER_D_MAIN")["unclassified_holdings_value"] == "5280.00"
    subs = _account(ev, "BROKER_S_SUBS")
    assert (subs["evidence_level"], subs["unclassified_holdings_value"]) == ("SUBPORTFOLIO_TOTAL_ONLY", "700.00")


def test_unverified_identity_is_not_merged_across_accounts() -> None:
    doc = _doc()
    _acct_doc(doc, "BANK_FCD")["positions"] = [
        {"security_id": "SYNTHEME", "observed_market_value": "10.00", "observed_market_value_currency": "USD"},
        {"security_id": "SYNIDX", "quantity": "1"}]
    _acct_doc(doc, "BANK_FCD")["reported_total"]["amount"] = "610.00"
    keys = {h["key"]: h["weight"] for h in _ev(doc)["concentration_best_evidence"]["top_holdings"]}
    assert "BANK_FCD:SYNTHEME" in keys and "BROKER_D_MAIN:SYNTHEME" in keys
    assert keys["ZZSYNIDX0005"] == "0.4317"


def test_totals_only_snapshot_yields_evidence_only_report() -> None:
    summary = po.book_summary(po.build_book(po.load_snapshot(TOTALS_ONLY)))
    assert (summary["report_type"], summary["analytics"]) == ("EVIDENCE_ONLY_REPORT", {})
    assert summary["unsupported_analyses"] == list(po.EVIDENCE_ONLY_UNSUPPORTED)
    ev = summary["evidence"]["THB"]
    assert ev["valuation_basis"] == {"computed_nav_ppds": "0.00", "observed_position_value": "0.00",
                                     "unclassified_holdings_value": "90750.00", "total_best_evidence": "90750.00"}
    assert ev["concentration_best_evidence"]["status"] == "LOWER_BOUND_UNCLASSIFIED_VALUE_PRESENT"
    assert ev["concentration_best_evidence"]["top_holdings"] == []
    assert [(a["account_ref"], a["evidence_level"]) for a in ev["accounts"]] == [
        ("BROKER_D_FCD", "ACCOUNT_TOTAL_ONLY"), ("BROKER_D_MAIN", "SUBPORTFOLIO_TOTAL_ONLY")]
    assert all(a["account_total"]["status"] == "INSUFFICIENT_EVIDENCE" for a in ev["accounts"])


def test_full_v1_2_report_is_labelled() -> None:
    assert po.book_summary(po.build_book(po.parse_snapshot(_doc())))["report_type"] == "FULL_REPORT"


def _tmp_inputs_public(monkeypatch: pytest.MonkeyPatch) -> None:
    """Synthetic inputs written to tmp_path are outside the repository, which is presumed private."""
    monkeypatch.setattr(po, "presumed_private", lambda path, root=None: False)


def test_evidence_only_pack_and_golden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tmp_inputs_public(monkeypatch)
    targets = tmp_path / "targets.json"
    targets.write_text(TARGETS, encoding="utf-8")
    wp.main(["--snapshot", str(TOTALS_ONLY), "--target-weights-file", str(targets), "--output", str(tmp_path / "out")])
    pack = json.loads((tmp_path / "out" / "upi_v1_pack.json").read_text(encoding="utf-8"))
    assert pack["B_long_term"]["contribution_first"] == "NOT_EVALUATED_EVIDENCE_ONLY_REPORT"
    assert pack["E_decision"]["reasons"][1].startswith("EVIDENCE_ONLY_REPORT")
    assert pack["E_decision"]["orders_generated"] == 0
    for name in ("upi_v1_pack.json", "upi_v1_pack.md"):
        assert (tmp_path / "out" / name).read_bytes() == (TOTALS_ONLY_PACK_DIR / name).read_bytes()


def test_target_weights_inputs_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"CASH": "x"}', encoding="utf-8")
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path / "repo_without_ratification")
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED.*not read"):
        wp.main(["--target-weights-file", str(bad), "--output", str(tmp_path / "o")])
    _tmp_inputs_public(monkeypatch)
    bad.write_text('{"CASH": "x"}', encoding="utf-8")
    with pytest.raises(DataContractError, match="TARGET_WEIGHTS_MALFORMED_DECIMAL"):
        wp.main(["--target-weights-file", str(bad), "--output", str(tmp_path / "o")])
    with pytest.raises(DataContractError, match="TARGET_WEIGHTS_AMBIGUOUS"):
        wp.main(["--target-weights", TARGETS, "--target-weights-file", str(bad), "--output", str(tmp_path / "o")])


def test_permutation_invariance() -> None:
    doc, shuffled = _doc(), _doc()
    shuffled["accounts"].reverse()
    for account in shuffled["accounts"]:
        account.get("positions", []).reverse()
        account.get("sub_portfolio_totals", []).reverse()
    assert _ev(doc) == _ev(shuffled)


def _set(path: str, value: Any) -> Any:
    def apply(doc: Dict[str, Any]) -> None:
        target: Any = doc
        keys = path.split(".")
        for key in keys[:-1]:
            target = target[int(key)] if key.isdigit() else target[key]
        last = keys[-1]
        if value is _DELETE:
            del target[int(last) if last.isdigit() else last]
        elif last.isdigit():
            target[int(last)] = value
        else:
            target[last] = value
    return apply


_DELETE = object()


@pytest.mark.parametrize("mutate, code", [
    (_set("accounts.0.positions.2.observed_market_value", _DELETE), "PRIVATE_AMOUNT_CURRENCY_PAIR_INCOMPLETE"),
    (_set("accounts.0.positions.2", {"security_id": "SYNTHEME", "sub_portfolio": "Theme"}), "PRIVATE_POSITION_EVIDENCE_MISSING"),
    (_set("securities.0.isin", "ZZSYNIDX0004"), "PRIVATE_ISIN_INVALID"),
    (_set("securities.1.figi", "BBX00SYNBND1"), "PRIVATE_FIGI_INVALID"),
    (_set("securities.0.exchange_mic", "ARCA1"), "PRIVATE_EXCHANGE_MIC_INVALID"),
    (_set("securities.0.instrument_type", "STOCK"), "PRIVATE_INSTRUMENT_TYPE_INVALID"),
    (_set("securities.0.trading_currency", "THB"), "PRIVATE_IDENTITY_CURRENCY_MISMATCH"),
    (_set("accounts.0.sub_portfolio_totals.1.sub_portfolio", "Core"), "PRIVATE_DUPLICATE_SUBPORTFOLIO_TOTAL"),
    (_set("accounts.0.sub_portfolio_totals.1.sub_portfolio", _DELETE), "PRIVATE_SUBPORTFOLIO_TOTAL_UNLABELLED"),
    (_set("accounts.0.reported_total.amount", "-2250.00"), "PRIVATE_NEGATIVE_VALUE"),
    (_set("accounts.0.reported_total.amount", 2250), "PRIVATE_NUMBER_MUST_BE_STRING"),
    (_set("accounts.0.reported_total.source", "app"), "PRIVATE_UNKNOWN_FIELDS"),
    (_set("accounts.3.reported_total", _DELETE), "PRIVATE_EMPTY_ACCOUNT"),
    (_set("schema", po.SCHEMA), "PRIVATE_UNKNOWN_FIELDS"),
])
def test_malformed_v1_2_fails_closed_without_echoing_amounts(mutate: Any, code: str) -> None:
    doc = _doc()
    mutate(doc)
    with pytest.raises(DataContractError, match=code) as err:
        po.parse_snapshot(doc)
    assert "2250" not in str(err.value) and "1100" not in str(err.value)


def test_quantity_and_value_lines_for_same_security_and_sub_are_duplicates() -> None:
    doc = _doc()
    doc["accounts"][0]["positions"].append({"security_id": "SYNIDX", "sub_portfolio": "Core", "observed_market_value": "1.00",
                                            "observed_market_value_currency": "USD"})
    with pytest.raises(DataContractError, match="PRIVATE_DUPLICATE_POSITION_LINE"):
        po.parse_snapshot(doc)


def _private_copy(tmp_path: Path, doc: Dict[str, Any]) -> Path:
    doc = copy.deepcopy(doc)
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    path = tmp_path / "data" / "private" / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_gate_is_scoped_to_listed_schemas_and_revocable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    path = _private_copy(tmp_path, _doc())
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        po.load_snapshot(path)
    _ratify(tmp_path, po.AUTHORIZATION_RECORD, po.AUTHORIZED_CAPABILITY, [po.SCHEMA])
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        po.load_snapshot(path)
    _ratify(tmp_path, po.AUTHORIZATION_RECORD, po.AUTHORIZED_CAPABILITY, [po.SCHEMA, po.SCHEMA_V1_2])
    assert po.load_snapshot(path).data_class == "OWNER_PRIVATE_OBSERVATION"
    _ratify(tmp_path, po.AUTHORIZATION_RECORD, po.AUTHORIZED_CAPABILITY, [po.SCHEMA, po.SCHEMA_V1_2], status="REVOKED")
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        po.load_snapshot(path)


def test_snapshot_ratification_does_not_open_transactions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    _ratify(tmp_path, po.AUTHORIZATION_RECORD, po.AUTHORIZED_CAPABILITY, [po.SCHEMA, po.SCHEMA_V1_2, tx.SCHEMA])
    batch = json.loads(TXNS.read_text(encoding="utf-8"))
    batch["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    path = tmp_path / "data" / "private" / "txns.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(batch), encoding="utf-8")
    with pytest.raises(DataContractError, match="ODR_UPI_PRIVATE_TRANSACTIONS_002"):
        tx.load_batch(path)
    _ratify(tmp_path, tx.AUTHORIZATION_RECORD, tx.AUTHORIZED_CAPABILITY, [tx.SCHEMA])
    assert tx.load_batch(path).data_class == "OWNER_PRIVATE_OBSERVATION"


def test_committed_records_keep_scope_and_governance_unchanged() -> None:
    tx_doc = json.loads(tx.AUTHORIZATION_RECORD.read_text(encoding="utf-8"))
    if tx_doc["status"] == "RATIFIED":
        lineage = tx_doc["ratification_lineage"]
        assert tx_doc["ratified_by"] == "OWNER" and lineage["decided_by"] == "OWNER"
        assert lineage["scope_changed"] is False and Path(lineage["acceptance_evidence"]).is_file()
    else:
        assert (tx_doc["status"], tx_doc["ratified_by"], tx_doc["ratified_on"]) == ("PROPOSED_NOT_RATIFIED", None, None)
    assert tx_doc["scope_schemas"] == [tx.SCHEMA] and "BROKER_NATIVE_IMPORT" in tx_doc["independent_of"]
    obs = json.loads(po.AUTHORIZATION_RECORD.read_text(encoding="utf-8"))
    if obs["status"] == "RATIFIED":
        assert obs["ratified_by"] == "OWNER" and obs["ratification_lineage"]["decided_by"] == "OWNER"
        assert obs["ratification_lineage"]["scope_changed"] is False
    else:
        assert (obs["status"], obs["ratified_by"], obs["ratified_on"]) == ("PROPOSED_NOT_RATIFIED", None, None)
    assert obs["scope_schemas"] == [po.SCHEMA, po.SCHEMA_V1_2, "ACASH_PRIVATE_CAPACITY_V1"]
    for doc in (obs, tx_doc):
        assert {"TRADING_AUTHORIZED", "CAPITAL_TRANSFER", "BROKER_ACCOUNT_CONNECTIVITY"} <= set(doc["independent_of"])
    assert "OWNER_PRIVATE_TRANSACTIONS_AUTHORIZED" in obs["independent_of"]
    assert po.private_observation_authorized(None, tx.SCHEMA) is False
    assert po.GOVERNANCE_FLAGS == {"research_admission": "NOT_ADMITTED_PRIVATE_OBSERVATION", "d5_eligible": False,
                                   "trading_authority": "NONE", "capital_authority_usd": "0.00", "order_controls": None}


def test_pilot_runs_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_: Any, **__: Any) -> None:
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    wp.main(["--snapshot", str(FIXTURE), "--target-weights", TARGETS, "--output", str(tmp_path)])
    pack = json.loads((tmp_path / "upi_v1_pack.json").read_text(encoding="utf-8"))
    reasons = " ".join(pack["E_decision"]["reasons"])
    assert "UNCLASSIFIED_HOLDINGS_PRESENT" in reasons and "MARKET_SESSION_NOT_VERIFIED" in reasons
    assert pack["E_decision"]["orders_generated"] == 0


def test_committed_pilot_pack_matches_regeneration(tmp_path: Path) -> None:
    wp.main(["--snapshot", str(FIXTURE), "--target-weights", TARGETS, "--output", str(tmp_path)])
    for name in ("upi_v1_pack.json", "upi_v1_pack.md"):
        assert (tmp_path / name).read_bytes() == (PILOT_PACK_DIR / name).read_bytes()


def test_owner_private_run_writes_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    _ratify(tmp_path, po.AUTHORIZATION_RECORD, po.AUTHORIZED_CAPABILITY,
            [po.SCHEMA_V1_2, "ACASH_PRIVATE_CAPACITY_V1"])
    snapshot = _private_copy(tmp_path, _doc())
    capacity = json.loads(Path(wp.PUBLIC_CAPACITY).read_text(encoding="utf-8"))
    capacity["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    cap_path = tmp_path / "data" / "private" / "capacity.json"
    cap_path.write_text(json.dumps(capacity), encoding="utf-8")
    out = tmp_path / "data" / "private" / "out"
    wp.main(["--snapshot", str(snapshot), "--capacity", str(cap_path), "--report-date", "2026-11-02", "--output", str(out)])
    manifest = json.loads((out / "upi_run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["snapshot_schema"] == po.SCHEMA_V1_2
    assert set(manifest["code_version"]) == {"commit", "working_tree"}
    pack = json.loads((out / "upi_v1_pack.json").read_text(encoding="utf-8"))
    assert manifest["observation_authority"] == pack["observation_authority"]
    assert (manifest["odr_state_at_write"], pack["observation_authority"]["odr_state"]) == ("RATIFIED", "RATIFIED")
    assert pack["observation_authority"]["trading_authority"] == "NONE"
    reasons = pack["E_decision"]["reasons"]
    assert any(r.startswith("OWNER_PRIVATE_OBSERVATION_AUTHORIZED:") and "no trading" in r for r in reasons)
    assert not any("PROPOSED_NOT_RATIFIED" in r for r in reasons)
    assert pack["E_decision"]["conclusion"] == "NO_ACTION_PENDING_EVIDENCE"
    assert pf.preflight(snapshot, cap_path, out)["preflight"] in ("READY", "READY_WITH_WARNINGS")


def test_synthetic_pack_authority_is_independent_of_odr_state(monkeypatch: pytest.MonkeyPatch) -> None:
    book = po.build_book(po.load_snapshot(FIXTURE))
    capacity = cp.load_capacity(Path(wp.PUBLIC_CAPACITY))
    closed = wp.build_wealth_pack(book, capacity)
    assert closed["observation_authority"]["odr_state"] == "NOT_CONSULTED_SYNTHETIC_FIXTURE"
    reasons = closed["E_decision"]["reasons"]
    assert reasons[-1].startswith("PRIVATE_OBSERVATION_AUTHORIZATION_NOT_REQUIRED:")
    assert not any("GOVERNANCE_AMENDMENT" in r or "PROPOSED_NOT_RATIFIED" in r for r in reasons)
    monkeypatch.setattr(wp, "odr_state", lambda *a, **k: "RATIFIED")
    assert wp.build_wealth_pack(book, capacity)["pack_sha256"] == closed["pack_sha256"]


@pytest.mark.parametrize("record, state", [
    (None, "RECORD_UNREADABLE"),
    ({"capability": "OTHER", "status": "RATIFIED"}, "RECORD_CAPABILITY_MISMATCH"),
    ({"status": "PROPOSED_NOT_RATIFIED"}, "PROPOSED_NOT_RATIFIED"),
    ({"status": "REVOKED", "ratified_by": "OWNER", "ratified_on": "2026-11-02"}, "REVOKED"),
    ({"status": "RATIFIED", "ratified_by": "AGENT", "ratified_on": "2026-11-02"}, "RECORD_INVALID"),
    ({"status": "RATIFIED", "ratified_by": "OWNER"}, "RECORD_INVALID"),
    ({"status": "SOMETHING", "ratified_by": "OWNER", "ratified_on": "2026-11-02"}, "RECORD_INVALID"),
    ({"status": "RATIFIED", "ratified_by": "OWNER", "ratified_on": "2026-11-02", "scope_schemas": ["X"]},
     "RATIFIED_SCHEMA_OUT_OF_SCOPE"),
    ({"status": "RATIFIED", "ratified_by": "OWNER", "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2]},
     "RATIFIED"),
])
def test_odr_state_and_private_pack_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                              record: Any, state: str) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    if record is not None:
        path = tmp_path / po.AUTHORIZATION_RECORD
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"capability": po.AUTHORIZED_CAPABILITY, **record}), encoding="utf-8")
    assert po.odr_state(None, po.SCHEMA_V1_2) == state
    assert po.private_observation_authorized(None, po.SCHEMA_V1_2) is (state == "RATIFIED")
    if state == "RATIFIED":
        assert wp.observation_authority("OWNER_PRIVATE_OBSERVATION", po.SCHEMA_V1_2)["odr_state"] == "RATIFIED"
    else:
        with pytest.raises(DataContractError, match=f"PRIVATE_OBSERVATION_NOT_AUTHORIZED: .* {state} for"):
            wp.observation_authority("OWNER_PRIVATE_OBSERVATION", po.SCHEMA_V1_2)
    assert po.odr_state(None, po.SCHEMA_V1_2, "OTHER_CAPABILITY") in ("RECORD_UNREADABLE", "RECORD_CAPABILITY_MISMATCH")


def test_v2_reconciliation_reports_quantity_not_observed() -> None:
    doc: Dict[str, Any] = json.loads(V1_1.read_text(encoding="utf-8"))
    doc["schema"] = po.SCHEMA_V1_2
    for pos in doc["accounts"][0]["positions"]:
        if pos["security_id"] == "SYNNEW":
            del pos["quantity"]
    doc["prices"] = [p for p in doc["prices"] if p["security_id"] != "SYNNEW"]
    state = tx.replay(tx.merge_batches([tx.parse_batch(json.loads(TXNS.read_text(encoding="utf-8")))]), date(2026, 10, 30))
    result = tx.reconcile_with_snapshot(state, po.parse_snapshot(doc))
    assert result["support_state"] == "TRANSACTIONS_PARTIAL"
    assert result["breaks"] == [{"scope": "POSITION", "key": "BROKER_A_MAIN:SYNNEW", "status": "QUANTITY_NOT_OBSERVED",
                                 "difference": ""}]
