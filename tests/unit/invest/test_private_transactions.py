"""Dashboard transaction journal (ODR-005): append-only recording over Transaction Accounting V2."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_input as pi
from acash.dashboard_api import private_transactions as pt
from acash.dashboard_api import private_view_server as srv
from acash.invest import market_authority as ma
from acash.invest.capacity_plan import CAPACITY_SCHEMA
from acash.ppds import private_observation as po
from acash.ppds import transactions as txn

EVIDENCE = Path("docs/research/evidence")
PORT = 8765
TOKEN = "t" * 43
ORIGIN = "http://127.0.0.1:3002"
TODAY = date(2026, 11, 3)


def _write(root: Path, record: Path, doc: Dict[str, Any]) -> None:
    (root / record).parent.mkdir(parents=True, exist_ok=True)
    (root / record).write_text(json.dumps(doc), encoding="utf-8")


def _odr(root: Path, odr2: str = "RATIFIED", odr5: str = "RATIFIED", **odr5_changes: Any) -> None:
    _write(root, po.AUTHORIZATION_RECORD, {"capability": po.AUTHORIZED_CAPABILITY, "status": "RATIFIED", "ratified_by": "OWNER",
                                           "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA]})
    _write(root, txn.AUTHORIZATION_RECORD, {"decision_id": "ODR_UPI_PRIVATE_TRANSACTIONS_002",
                                            "capability": txn.AUTHORIZED_CAPABILITY, "status": odr2, "ratified_by": "OWNER",
                                            "ratified_on": "2026-11-02", "scope_schemas": [txn.SCHEMA]})
    _write(root, pt.RECORD, {"decision_id": pt.DECISION_ID, "capability": pt.CAPABILITY, "status": odr5,
                             "ratified_by": "OWNER", "ratified_on": "2026-11-03", "requires": pt.REQUIRES,
                             "scope_schemas": [txn.SCHEMA], "scope_files": pt.SCOPE_FILES, **odr5_changes})


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ma, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(pt, "_today", lambda: TODAY)
    _odr(tmp_path)
    private = tmp_path / "data" / "private"
    private.mkdir(parents=True)
    for name, source in (("snapshot.json", "upi_v1_2_synthetic_snapshot.json"), ("capacity.json", "upi_v1_synthetic_capacity.json")):
        doc = json.loads((EVIDENCE / source).read_text(encoding="utf-8"))
        doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
        (private / name).write_text(json.dumps(doc), encoding="utf-8")
    return tmp_path


def _call(method: str, name: str, body: Any = None, service: Optional[pi.InputService] = None) -> Tuple[int, Any]:
    data = b"" if body is None else json.dumps(body).encode("utf-8")
    headers = {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN, "Content-Type": "application/json"}
    status, out_headers, out = srv.respond(method, pt.PREFIX + name, headers, TOKEN, Path("unused.json"), PORT, data,
                                           service or pi.InputService())
    assert out_headers["Cache-Control"] == "no-store"
    return status, json.loads(out) if out else None


def _buy(tid: str = "TX_BUYSYNIDXA", qty: str = "2", price: str = "10.50", day: str = "2026-11-02",
         event: str = "BUY", **extra: Any) -> Dict[str, Any]:
    gross = format(float(qty) * float(price), ".2f")
    fee = extra.pop("commission", "1.00")
    net = -(float(gross) + float(fee)) if event == "BUY" else float(gross) - float(fee)
    return {"transaction_id": tid, "account_ref": "BROKER_D_MAIN", "event_type": event, "trade_date": day,
            "security_id": "SYNIDX", "quantity": qty, "price": price, "gross_amount": gross, "commission": fee,
            "currency": "USD", "net_cash": format(net, ".2f"), **extra}


def _record(row: Dict[str, Any], service: Optional[pi.InputService] = None, **extra: Any) -> Tuple[int, Any]:
    revision = _call("GET", "state")[1]["revision"]
    return _call("POST", "record", {"base_revision": revision, "confirm": True, "transaction": row, **extra}, service)


def _position(state: Dict[str, Any], account: str, security: str) -> Optional[str]:
    for p in state["projection"]["positions"]:
        if (p["account_ref"], p["security_id"]) == (account, security):
            return str(p["quantity"])
    return None


def _cash(state: Dict[str, Any], account: str, ccy: str = "USD") -> Optional[str]:
    for c in state["projection"]["cash"]:
        if (c["account_ref"], c["currency"]) == (account, ccy):
            return str(c["amount"])
    return None


def test_baseline_comes_from_snapshot_quantities_and_settled_cash(root: Path) -> None:
    http, state = _call("GET", "state")
    assert http == 200 and state["baseline"]["cutoff"] == "2026-10-30" and state["entries"] == []
    assert _position(state, "BROKER_D_MAIN", "SYNIDX") == "12" and _position(state, "BROKER_D_MAIN", "SYNBOND") == "30"
    assert _cash(state, "BROKER_D_MAIN") == "40.00" and _cash(state, "BANK_FCD") == "500.00"
    assert {"code": "VALUE_ONLY_POSITION_NOT_IN_BASELINE", "where": "BROKER_D_MAIN:SYNTHEME"} in state["baseline"]["baseline_excluded"]
    known = {p["security_id"]: p["cost_status"] for p in state["projection"]["positions"]}
    assert known == {"SYNIDX": "KNOWN", "SYNBOND": "COST_NOT_ESTABLISHED"}
    assert state["corrections"] == "NOT_ENABLED_PENDING_OWNER_DECISION"


def test_buy_sell_and_cash_events_replay_through_the_canonical_ledger(root: Path) -> None:
    assert _record(_buy())[1]["status"] == "RECORDED"
    state = _call("GET", "state")[1]
    assert _position(state, "BROKER_D_MAIN", "SYNIDX") == "14" and _cash(state, "BROKER_D_MAIN") == "18.00"
    assert _record(_buy("TX_SELLSYNIDXA", qty="0.5", price="12.00", event="SELL", day="2026-11-03"))[1]["status"] == "RECORDED"
    for row in ({"transaction_id": "TX_DEPOSITAAAA", "account_ref": "BANK_FCD", "event_type": "DEPOSIT", "trade_date": "2026-11-01",
                 "currency": "USD", "net_cash": "100.00"},
                {"transaction_id": "TX_WITHDRAWAAA", "account_ref": "BANK_FCD", "event_type": "WITHDRAWAL", "trade_date": "2026-11-02",
                 "currency": "USD", "net_cash": "-50.00"},
                {"transaction_id": "TX_DIVIDENDAAA", "account_ref": "BROKER_D_MAIN", "event_type": "DIVIDEND", "trade_date": "2026-11-02",
                 "security_id": "SYNIDX", "currency": "USD", "net_cash": "0.75"},
                {"transaction_id": "TX_FEEAAAAAAAA", "account_ref": "BROKER_D_MAIN", "event_type": "FEE", "trade_date": "2026-11-02",
                 "currency": "USD", "net_cash": "-0.25"}):
        assert _record(row)[1]["status"] == "RECORDED", row
    state = _call("GET", "state")[1]
    assert _position(state, "BROKER_D_MAIN", "SYNIDX") == "13.5"
    assert _cash(state, "BROKER_D_MAIN") == "23.50" and _cash(state, "BANK_FCD") == "550.00"
    realized = state["projection"]["realized"]
    assert len(realized) == 1 and realized[0]["status"] == "REALIZED"
    assert [e["status"] for e in state["entries"]] == ["APPLIED"] * 6


def test_preview_reports_effect_without_writing(root: Path) -> None:
    http, out = _call("POST", "preview", {"transaction": _buy()})
    assert http == 200 and out["duplicate"] is None
    assert _position({"projection": out["effect"]["before"]}, "BROKER_D_MAIN", "SYNIDX") == "12"
    assert _position({"projection": out["effect"]["after"]}, "BROKER_D_MAIN", "SYNIDX") == "14"
    assert not (root / "data" / "private" / "transactions" / pt.JOURNAL_FILE).exists()


def test_resubmission_conflicts_and_possible_duplicates(root: Path) -> None:
    assert _record(_buy(qty="1"))[1]["status"] == "RECORDED"
    assert _record(_buy(qty="1"))[1]["status"] == "ALREADY_RECORDED"
    assert _record(_buy(qty="3"))[0:2] == (409, {"status": "TXN_ID_CONFLICT"})
    assert _record(_buy("TX_BUYSYNIDXB", qty="1")) == (409, {"status": "POSSIBLE_DUPLICATE"})
    http, out = _record(_buy("TX_BUYSYNIDXB", qty="1"), confirm_duplicate=True)
    assert http == 200 and out["status"] == "RECORDED"
    assert _position(_call("GET", "state")[1], "BROKER_D_MAIN", "SYNIDX") == "14"


def test_stale_revision_and_missing_confirmation_are_refused(root: Path) -> None:
    base = _call("GET", "state")[1]["revision"]
    assert _call("POST", "record", {"base_revision": base, "confirm": False, "transaction": _buy()})[1]["status"] == "CONFIRMATION_REQUIRED"
    assert _call("POST", "record", {"base_revision": base, "confirm": True, "transaction": _buy()})[0] == 200
    http, out = _call("POST", "record", {"base_revision": base, "confirm": True, "transaction": _buy("TX_BUYSYNIDXC", qty="1")})
    assert (http, out["status"]) == (409, "REVISION_CONFLICT")
    assert _call("POST", "record", {"base_revision": base, "confirm": True, "transaction": _buy(), "x": 1})[0] == 400


@pytest.mark.parametrize("row, code", [
    (_buy(qty="20", price="1.00", event="SELL"), "TXN_POSITION_OVERSOLD"),
    (_buy(qty="10", price="10.00"), "TXN_CASH_NEGATIVE"),
    (_buy(day="2026-10-30"), "TXN_BEFORE_BASELINE_CUTOFF"),
    (_buy(day="2026-11-04"), "TXN_FUTURE_TRADE_DATE"),
    ({**_buy(), "account_ref": "BROKER_UNKNOWN"}, "TXN_ACCOUNT_UNKNOWN"),
    ({**_buy(), "security_id": "SYNNEW"}, "TXN_SECURITY_UNKNOWN"),
    ({**_buy(), "currency": "THB"}, "TXN_CURRENCY_MISMATCH"),
    ({**_buy(), "net_cash": "-1.00"}, "TXN_NET_CASH_INCONSISTENT"),
    ({**_buy(), "transaction_id": "TX_1"}, "TXN_ID_REQUIRED"),
    ({"transaction_id": "TX_OPENINGAAA", "account_ref": "BROKER_D_MAIN", "event_type": "OPENING_POSITION",
      "trade_date": "2026-11-02", "security_id": "SYNIDX", "quantity": "5", "currency": "USD"}, "TXN_EVENT_NOT_AUTHORABLE"),
    ({**_buy(), "event_type": "STOCK_SPLIT"}, "TXN_EVENT_NOT_AUTHORABLE"),
])
def test_invalid_transactions_fail_closed_and_write_nothing(root: Path, row: Dict[str, Any], code: str) -> None:
    http, out = _record(row)
    assert (http, out["status"], out["code"]) == (422, "TRANSACTION_REFUSED", code)
    assert not (root / "data" / "private" / "transactions").exists()


def test_journal_is_append_only_with_backups_and_survives_restart(root: Path) -> None:
    assert _record(_buy())[0] == 200
    journal = root / "data" / "private" / "transactions" / pt.JOURNAL_FILE
    first = json.loads(journal.read_text("utf-8"))["transactions"]
    assert _record(_buy("TX_BUYSYNIDXD", qty="1"))[0] == 200
    second = json.loads(journal.read_text("utf-8"))["transactions"]
    assert second[:1] == first and len(second) == 2
    assert len(list((journal.parent / "backups").glob("journal-*.json"))) == 1
    assert _position(_call("GET", "state", service=pi.InputService())[1], "BROKER_D_MAIN", "SYNIDX") == "15"


def test_write_failure_leaves_journal_unchanged(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert _record(_buy())[0] == 200
    journal = root / "data" / "private" / "transactions" / pt.JOURNAL_FILE
    before = journal.read_bytes()
    original = pi._atomic_write

    def failing(path: Path, data: bytes) -> None:
        if path.name == pt.JOURNAL_FILE:
            raise OSError("disk full")
        original(path, data)
    monkeypatch.setattr(pi, "_atomic_write", failing)
    assert _record(_buy("TX_BUYSYNIDXE", qty="1"))[1]["status"] == "WRITE_FAILED"
    assert journal.read_bytes() == before


@pytest.mark.parametrize("odr2, odr5, changes, http_state, http_record", [
    ("RATIFIED", "PROPOSED_NOT_RATIFIED", {}, 200, 403),
    ("RATIFIED", "REVOKED", {}, 200, 403),
    ("RATIFIED", "RATIFIED", {"scope_files": ["data/private/"]}, 200, 403),
    ("RATIFIED", "RATIFIED", {"requires": ["ODR_UPI_PRIVATE_OBSERVATION_001"]}, 200, 403),
    ("REVOKED", "RATIFIED", {}, 403, 403),
])
def test_odr_005_and_002_gate_writes_and_reads(root: Path, odr2: str, odr5: str, changes: Dict[str, Any],
                                               http_state: int, http_record: int) -> None:
    assert _record(_buy())[0] == 200
    _odr(root, odr2, odr5, **changes)
    assert _call("GET", "state")[0] == http_state
    out = _call("POST", "record", {"base_revision": "x", "confirm": True, "transaction": _buy("TX_BUYSYNIDXF", qty="1")})
    assert out[0] == http_record
    assert len(json.loads((root / "data" / "private" / "transactions" / pt.JOURNAL_FILE).read_text("utf-8"))["transactions"]) == 1


def test_journal_link_is_refused(root: Path) -> None:
    target = root / "elsewhere"
    target.mkdir()
    link = root / "data" / "private" / "transactions"
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("symlink creation not permitted on this host")
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    assert _call("GET", "state")[1]["code"] == "INPUT_PATH_LINK_REFUSED"
    out = _call("POST", "record", {"base_revision": pi.ABSENT, "confirm": True, "transaction": _buy()})
    assert (out[0], out[1]["code"]) == (422, "INPUT_PATH_LINK_REFUSED")
    assert not list(target.iterdir())


def test_projected_holdings_feed_market_valuation(root: Path) -> None:
    doc = json.loads((root / "data" / "private" / "snapshot.json").read_text("utf-8"))
    assert pt.holdings_for_valuation(doc, TODAY) == (doc, "STATEMENT_BASELINE")
    assert _record(_buy())[0] == 200
    projected, basis = pt.holdings_for_valuation(doc, TODAY)
    assert basis == "STATEMENT_BASELINE_PLUS_JOURNAL"
    main = next(a for a in projected["accounts"] if a["account_ref"] == "BROKER_D_MAIN")
    by_sec = {p["security_id"]: p for p in main["positions"]}
    assert by_sec["SYNIDX"]["quantity"] == "14" and by_sec["SYNIDX"]["cost_basis_total"] == "1122.00"
    assert "quantity" not in by_sec["SYNTHEME"] and "cost_basis_total" not in by_sec["SYNBOND"]
    assert [c for c in main["cash"] if c["kind"] == "SETTLED"] == [{"currency": "USD", "amount": "18.00", "kind": "SETTLED"}]
    quant = next(a for a in projected["accounts"] if a["account_ref"] == "BROKER_W_QUANT")
    assert quant["cash"] == next(a for a in doc["accounts"] if a["account_ref"] == "BROKER_W_QUANT")["cash"]
    po.build_book(po.parse_snapshot(projected))
    assert json.loads((root / "data" / "private" / "snapshot.json").read_text("utf-8")) == doc


def test_journal_cash_on_a_negative_baseline_line_fails_closed(root: Path) -> None:
    path = root / "data" / "private" / "snapshot.json"
    doc = json.loads(path.read_text("utf-8"))
    quant = next(a for a in doc["accounts"] if a["account_ref"] == "BROKER_W_QUANT")
    quant["cash"] = [{"currency": "USD", "amount": "-5.00", "kind": "SETTLED"}]
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert _record({"transaction_id": "TX_DEPOSITQUANT", "account_ref": "BROKER_W_QUANT", "event_type": "DEPOSIT",
                    "trade_date": "2026-11-02", "currency": "USD", "net_cash": "10.00"})[0] == 200
    with pytest.raises(DataContractError, match="TXN_NEGATIVE_BASELINE_CASH_NOT_PROJECTABLE"):
        pt.holdings_for_valuation(doc, TODAY)


def test_transaction_routes_have_no_broker_or_edit_surface(root: Path) -> None:
    assert set(pt.ROUTES) == {"state", "preview", "record", "rebase"}
    assert all(m in ("GET", "POST") for methods in pt.ROUTES.values() for m in methods)
    for method in ("PUT", "DELETE", "PATCH"):
        assert _call(method, "record", {})[0] == 405
    text = Path(str(pt.__file__)).read_text(encoding="utf-8")
    for banned in ("import urllib", "import socket", "import requests", "alpaca", "/v2/orders"):
        assert banned not in text


def _snapshot_edit(root: Path, change: Any) -> None:
    path = root / "data" / "private" / "snapshot.json"
    doc = json.loads(path.read_text("utf-8"))
    change(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _main(doc: Dict[str, Any]) -> Dict[str, Any]:
    return next(a for a in doc["accounts"] if a["account_ref"] == "BROKER_D_MAIN")


def _baseline(state: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
    b = state["baseline"]
    return b["baseline_status"], b["cutoff"], b["baseline_id"]


def test_first_record_freezes_the_opening_baseline(root: Path) -> None:
    assert _baseline(_call("GET", "state")[1]) == ("PROVISIONAL_FROM_SNAPSHOT", "2026-10-30", None)
    assert _record(_buy())[0] == 200
    frozen = json.loads((root / "data" / "private" / "transactions" / pt.BASELINE_FILE).read_text("utf-8"))
    assert frozen["batch_id"] == "BASELINE_V1" and {r["trade_date"] for r in frozen["transactions"]} == {"2026-10-30"}
    st = _call("GET", "state")[1]
    assert _baseline(st) == ("FROZEN", "2026-10-30", "BASELINE_V1")
    assert (_position(st, "BROKER_D_MAIN", "SYNIDX"), _cash(st, "BROKER_D_MAIN")) == ("14", "18.00")


def test_price_only_snapshot_update_keeps_the_frozen_baseline(root: Path) -> None:
    assert _record(_buy())[0] == 200
    before = _call("GET", "state")[1]
    _snapshot_edit(root, lambda d: [p.update(price=str(Decimal(str(p["price"])) + 1)) for p in d["prices"]])
    after = _call("GET", "state")[1]
    assert _baseline(after) == ("FROZEN", "2026-10-30", "BASELINE_V1")
    assert after["projection"] == before["projection"]


@pytest.mark.parametrize("change", [
    lambda d: d.update(valuation_date="2026-11-02"),
    lambda d: next(p for p in _main(d)["positions"] if p["security_id"] == "SYNIDX").update(quantity="14"),
    lambda d: _main(d)["cash"][0].update(amount="18.00"),
], ids=["valuation_date", "quantity", "cash"])
def test_material_snapshot_change_never_moves_the_cutoff_silently(root: Path, change: Any) -> None:
    assert _record(_buy())[0] == 200
    _snapshot_edit(root, change)
    st = _call("GET", "state")[1]
    assert _baseline(st) == ("SNAPSHOT_DIVERGED_REBASE_REQUIRED", "2026-10-30", "BASELINE_V1")
    assert [e["status"] for e in st["entries"]] == ["APPLIED"]
    assert _position(st, "BROKER_D_MAIN", "SYNIDX") == "14"
    assert _record(_buy("TX_SECONDBUYAAA", day="2026-11-03"))[1]["status"] == "BASELINE_REBASE_REQUIRED"
    assert _call("POST", "preview", {"transaction": _buy("TX_SECONDBUYAAA", day="2026-11-03")})[0] == 409
    doc = json.loads((root / "data" / "private" / "snapshot.json").read_text("utf-8"))
    assert pt.holdings_for_valuation(doc, TODAY) == (doc, "STATEMENT_ONLY_JOURNAL_NOT_APPLIED_REBASE_REQUIRED")


def test_rebase_previews_then_archives_and_absorbs_events_exactly_once(root: Path) -> None:
    assert _record(_buy())[0] == 200
    assert _record(_buy("TX_SELLSYNIDXA", qty="1", price="12.00", day="2026-11-03", event="SELL"))[0] == 200

    def roll(d: Dict[str, Any]) -> None:
        d["valuation_date"] = "2026-11-02"
        next(p for p in _main(d)["positions"] if p["security_id"] == "SYNIDX").update(quantity="14", cost_basis_total="1122.00")
        _main(d)["cash"][0]["amount"] = "18.00"
    _snapshot_edit(root, roll)
    revision = _call("GET", "state")[1]["revision"]
    status, out = _call("POST", "rebase", {"base_revision": revision, "confirm": False})
    assert status == 200 and out["status"] == "REBASE_PREVIEW"
    plan = out["plan"]
    assert (plan["from_baseline"], plan["to_baseline"], plan["absorbed"], plan["reactivated"]) == \
        ("BASELINE_V1", "BASELINE_V2", ["TX_BUYSYNIDXA"], [])
    assert _position({"projection": plan["before"]}, "BROKER_D_MAIN", "SYNIDX") == "13"
    assert _position({"projection": plan["after"]}, "BROKER_D_MAIN", "SYNIDX") == "13"
    assert _cash({"projection": plan["after"]}, "BROKER_D_MAIN") == _cash({"projection": plan["before"]}, "BROKER_D_MAIN") == "29.00"
    assert _call("GET", "state")[1]["revision"] == revision
    assert _call("POST", "rebase", {"base_revision": "stale", "confirm": True})[1]["status"] == "REVISION_CONFLICT"
    status, out = _call("POST", "rebase", {"base_revision": revision, "confirm": True})
    assert status == 200 and out["status"] == "REBASED"
    tx = root / "data" / "private" / "transactions"
    assert json.loads((tx / "baselines" / "BASELINE_V1.json").read_text("utf-8"))["batch_id"] == "BASELINE_V1"
    st = _call("GET", "state")[1]
    assert _baseline(st) == ("FROZEN", "2026-11-02", "BASELINE_V2")
    assert [e["status"] for e in st["entries"]] == ["BEFORE_BASELINE_CUTOFF", "APPLIED"]
    assert (_position(st, "BROKER_D_MAIN", "SYNIDX"), _cash(st, "BROKER_D_MAIN")) == ("13", "29.00")
    assert _call("POST", "rebase", {"base_revision": st["revision"], "confirm": True})[1]["status"] == "REBASE_NOT_REQUIRED"


def test_rebase_write_failure_keeps_the_old_baseline_and_can_be_retried(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert _record(_buy())[0] == 200
    _snapshot_edit(root, lambda d: d.update(valuation_date="2026-11-01"))
    path = root / "data" / "private" / "transactions" / pt.BASELINE_FILE
    original = path.read_bytes()
    real = pi._atomic_write

    def fail(target: Path, data: bytes) -> None:
        if target.name == pt.BASELINE_FILE:
            raise OSError("disk full")
        real(target, data)
    monkeypatch.setattr(pi, "_atomic_write", fail)
    revision = _call("GET", "state")[1]["revision"]
    assert _call("POST", "rebase", {"base_revision": revision, "confirm": True})[1]["status"] == "WRITE_FAILED"
    assert path.read_bytes() == original
    monkeypatch.setattr(pi, "_atomic_write", real)
    assert _call("POST", "rebase", {"base_revision": revision, "confirm": True})[1]["status"] == "REBASED"


def test_journal_without_a_frozen_baseline_requires_a_rebase(root: Path) -> None:
    assert _record(_buy())[0] == 200
    (root / "data" / "private" / "transactions" / pt.BASELINE_FILE).unlink()
    st = _call("GET", "state")[1]
    assert st["baseline"]["baseline_status"] == "BASELINE_MISSING_REBASE_REQUIRED"
    assert _record(_buy("TX_SECONDBUYAAA", day="2026-11-03"))[1]["status"] == "BASELINE_REBASE_REQUIRED"


def test_replay_is_deterministic_across_restarts_and_conserves_cash(root: Path) -> None:
    for row in (_buy(), _buy("TX_BUYAGAINAAA", qty="0.5", price="11.00", day="2026-11-03", commission="0.50"),
                _buy("TX_SELLPARTAAA", qty="1.25", price="12.00", day="2026-11-03", event="SELL")):
        assert _record(row)[0] == 200
    first = _call("GET", "state", service=pi.InputService())[1]
    second = _call("GET", "state", service=pi.InputService())[1]
    assert first["projection"] == second["projection"] and first["revision"] == second["revision"]
    nets = sum(Decimal(e["net_cash"]) for e in first["entries"])
    assert Decimal(_cash(first, "BROKER_D_MAIN") or "0") == Decimal("40") + nets
    assert Decimal(_position(first, "BROKER_D_MAIN", "SYNIDX") or "0") == Decimal("12") + 2 + Decimal("0.5") - Decimal("1.25")
    assert first["event_date_policy"] == "TRADE_DATE_AS_ENTERED_FUTURE_CHECK_ASIA_BANGKOK"