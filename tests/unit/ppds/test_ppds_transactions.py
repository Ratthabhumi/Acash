"""Canonical transaction accounting V2 and flow-aware performance (synthetic fixtures only)."""

from __future__ import annotations

import copy
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.ppds import private_observation as po
from acash.ppds import transactions as tx
from acash.invest.performance import performance_report
from acash.ppds.exposure import evaluate_portfolio_base_currency
from acash.research.d6.contributions import xirr

TXNS = Path("docs/research/evidence/upi_v2_synthetic_transactions.json")
SNAPSHOT = Path("docs/research/evidence/upi_v1_synthetic_snapshot.json")
AS_OF = date(2026, 10, 30)


def _doc() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(TXNS.read_text(encoding="utf-8"))
    return doc


def _state(doc: Dict[str, Any], as_of: date = AS_OF) -> tx.LedgerState:
    return tx.replay(tx.merge_batches([tx.parse_batch(doc)]), as_of)


def _find(doc: Dict[str, Any], txn_id: str) -> Dict[str, Any]:
    for row in doc["transactions"]:
        if row.get("transaction_id") == txn_id:
            found: Dict[str, Any] = row
            return found
    raise KeyError(txn_id)


def test_replay_reconciles_with_snapshot() -> None:
    state = _state(_doc())
    result = tx.reconcile_with_snapshot(state, po.load_snapshot(SNAPSHOT))
    assert result["support_state"] == "TRANSACTIONS_RECONCILED"
    assert result["breaks"] == []
    assert state.cash[("BROKER_A_MAIN", "USD")] == Decimal("25.50")
    assert state.cash[("BROKER_A_MAIN", "THB")] == Decimal("0.00")
    assert "OPENING_BALANCES_PRESENT" in result["history_note"]
    assert result["unknown_cost_positions"] == ["BROKER_A_MAIN:SYNNEW"]


def test_fifo_realized_pnl_and_remaining_cost() -> None:
    state = _state(_doc())
    assert state.realized[0]["status"] == "REALIZED"
    assert state.realized[0]["realized_pnl"] == "-15.00"
    moon = state.lots[("BROKER_A_MAIN", "SYNMOON")]
    assert [(l.quantity, l.cost_total) for l in moon] == [(Decimal("40"), Decimal("240.00")), (Decimal("10"), Decimal("50.00"))]


def test_income_costs_and_external_flows() -> None:
    state = _state(_doc())
    assert state.income["DIVIDEND"] == {"USD": Decimal("10.00")}
    assert state.income["DIVIDEND_WITHHOLDING"] == {"USD": Decimal("1.50")}
    assert state.income["COMMISSION"] == {"USD": Decimal("1.50")}
    assert state.income["FEE"] == {"USD": Decimal("0.50")}
    flows = [(d.isoformat(), a, c, str(v)) for d, a, c, v in state.external_flows]
    assert flows == [("2026-01-05", "BROKER_A_MAIN", "THB", "99000.00"), ("2026-02-01", "BANK_FCD", "USD", "600.00"),
                     ("2026-09-01", "BROKER_A_MAIN", "USD", "-257.50")]


def test_internal_transfer_is_neutral_at_consolidated_level() -> None:
    state = _state(_doc())
    usd_total = sum((v for (a, c), v in state.cash.items() if c == "USD"), Decimal(0))
    external_usd = sum((v for _, _, c, v in state.external_flows if c == "USD"), Decimal(0))
    spent = Decimal("1800.00") + Decimal("600.00") + Decimal("300.00") + Decimal("50.00") + Decimal("120.00")
    received = Decimal("3000.00") + Decimal("10.00") - Decimal("1.50") + Decimal("45.00") - Decimal("0.50")
    assert usd_total == external_usd + received - spent


def test_settlement_timing_moves_cash_after_trade_date() -> None:
    state = _state(_doc(), date(2026, 7, 1))
    assert state.pending_cash == {("BROKER_A_MAIN", "USD"): Decimal("45.00")}
    assert ("BROKER_A_MAIN", "SYNMOON") in state.lots
    assert sum(l.quantity for l in state.lots[("BROKER_A_MAIN", "SYNMOON")]) == Decimal("50")


def test_stock_split_scales_quantity_not_cost() -> None:
    doc = _doc()
    doc["transactions"].append({"transaction_id": "T_SPLIT", "account_ref": "BROKER_A_MAIN", "event_type": "STOCK_SPLIT",
                                "trade_date": "2026-10-01", "security_id": "SYNIDX", "split_ratio": "2"})
    lots = _state(doc).lots[("BROKER_A_MAIN", "SYNIDX")]
    assert sum(l.quantity for l in lots) == Decimal("42.50")
    assert sum((l.cost_total or Decimal(0)) for l in lots) == Decimal("1920.00")


def test_idempotent_merge_and_preview() -> None:
    batch = tx.parse_batch(_doc())
    merged = tx.merge_batches([batch, batch])
    assert len(merged) == len(batch.transactions)
    preview = tx.import_preview(merged, batch)
    assert (preview["new"], preview["already_imported"], preview["conflicts"]) == (0, len(merged), [])
    changed = _doc()
    _find(changed, "T_DIV_IDX")["net_cash"] = "11.00"
    _find(changed, "T_DIV_WHT")["net_cash"] = "-1.65"
    conflicting = tx.parse_batch(changed)
    assert tx.import_preview(merged, conflicting)["conflicts"] == ["T_DIV_IDX", "T_DIV_WHT"]
    with pytest.raises(DataContractError, match="TXN_ID_CONFLICT"):
        tx.merge_batches([batch, conflicting])


def test_fingerprint_duplicates_need_sequence() -> None:
    doc = _doc()
    fee = next(r for r in doc["transactions"] if "transaction_id" not in r)
    doc["transactions"].append(dict(fee))
    with pytest.raises(DataContractError, match="TXN_DUPLICATE_IN_BATCH"):
        tx.parse_batch(doc)
    doc["transactions"][-1]["sequence"] = 1
    assert len(tx.parse_batch(doc).transactions) == len(doc["transactions"])


def test_order_independence() -> None:
    doc = _doc()
    shuffled = copy.deepcopy(doc)
    shuffled["transactions"].reverse()
    a, b = _state(doc), _state(shuffled)
    assert (a.cash, a.lots, a.realized, a.external_flows) == (b.cash, b.lots, b.realized, b.external_flows)


def test_mixed_data_classes_cannot_merge() -> None:
    owner = _doc()
    owner["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    with pytest.raises(DataContractError, match="TXN_DATA_CLASS_MIXED"):
        tx.merge_batches([tx.parse_batch(_doc()), tx.parse_batch(owner)])


@pytest.mark.parametrize("txn_id, field, value, code", [
    ("T_BUY_TECH", "net_cash", "-599.00", "TXN_NET_CASH_INCONSISTENT"),
    ("T_BUY_TECH", "gross_amount", "590.00", "TXN_GROSS_INCONSISTENT_WITH_QUANTITY_PRICE"),
    ("T_BUY_TECH", "net_cash", "600.00", "TXN_NET_CASH_SIGN_INVALID"),
    ("T_BUY_TECH", "quantity", 10.5, "PRIVATE_NUMBER_MUST_BE_STRING"),
    ("T_BUY_TECH", "split_ratio", "2", "TXN_FIELDS_INVALID"),
    ("T_BUY_TECH", "settlement_date", "2026-02-01", "TXN_SETTLEMENT_BEFORE_TRADE"),
    ("T_DEP_FCD", "net_cash", "-600.00", "TXN_NET_CASH_SIGN_INVALID"),
    ("T_DEP_FCD", "event_type", "INTEREST_ACCRUED", "TXN_EVENT_NOT_SUPPORTED_V2"),
    ("T_DEP_FCD", "event_type", "TRANSFER", "TXN_EVENT_TYPE_INVALID"),
    ("T_DEP_FCD", "account_ref", "ACC_1234567", "PRIVATE_REF_NOT_OPAQUE"),
    ("T_FX_1", "fx_to_currency", "THB", "TXN_FX_SAME_CURRENCY"),
    ("T_DEP_FCD", "trade_date", None, "TXN_FIELDS_INVALID"),
    ("T_DEP_FCD", "trade_date", "2026-02-30", "DATE"),
    ("T_DEP_FCD", "trade_date", "01/02/2026", "DATE"),
])
def test_malformed_transactions_fail_closed(txn_id: str, field: str, value: Any, code: str) -> None:
    doc = _doc()
    _find(doc, txn_id)[field] = value
    with pytest.raises(DataContractError, match=code):
        tx.parse_batch(doc)


@pytest.mark.parametrize("txn_id, field, value, code", [
    ("T_SELL_MOON", "quantity", "70", "TXN_POSITION_OVERSOLD"),
    ("T_WDR", "net_cash", "-9999.00", "TXN_CASH_NEGATIVE"),
    ("T_XFER_IN", "net_cash", "90.00", "TXN_TRANSFER_UNBALANCED"),
    ("T_XFER_IN", "account_ref", "BANK_FCD", "TXN_TRANSFER_UNBALANCED"),
])
def test_accounting_breaks_fail_closed(txn_id: str, field: str, value: str, code: str) -> None:
    doc = _doc()
    row = _find(doc, txn_id)
    row[field] = value
    if field == "quantity":
        row["gross_amount"], row["net_cash"] = "315.00", "315.00"
    with pytest.raises(DataContractError, match=code):
        _state(doc)


def test_dividend_double_count_detected() -> None:
    doc = _doc()
    duplicate = dict(_find(doc, "T_DIV_IDX"), transaction_id="T_DIV_IDX_AGAIN")
    doc["transactions"].append(duplicate)
    with pytest.raises(DataContractError, match="TXN_DIVIDEND_DOUBLE_COUNT_SUSPECTED"):
        _state(doc)


def test_reconciliation_reports_breaks_without_repair() -> None:
    doc = _doc()
    doc["transactions"] = [r for r in doc["transactions"] if r.get("transaction_id") != "T_BUY_IDX_2"]
    _find(doc, "T_WDR")["net_cash"] = "-137.50"
    result = tx.reconcile_with_snapshot(_state(doc), po.load_snapshot(SNAPSHOT))
    assert result["support_state"] == "TRANSACTIONS_PARTIAL"
    assert {"scope": "POSITION", "key": "BROKER_A_MAIN:SYNIDX", "status": "QUANTITY_BREAK", "difference": "-1.25"} in result["breaks"]
    with pytest.raises(DataContractError, match="TXN_RECONCILE_DATE_MISMATCH"):
        tx.reconcile_with_snapshot(_state(_doc(), date(2026, 10, 29)), po.load_snapshot(SNAPSHOT))


def test_replayed_state_values_through_ppds_and_matches_snapshot_nav() -> None:
    state = _state(_doc())
    snapshot = po.load_snapshot(SNAPSHOT)
    prices = {p.symbol: p for p in snapshot.prices}
    fx = {(r.from_currency, r.to_currency): r for r in snapshot.fx_rates}
    book = po.build_book(snapshot)
    for account in snapshot.accounts:
        replayed = evaluate_portfolio_base_currency(tx.valuation_view(state, account.account_ref),
                                                    account.base_currency, AS_OF, prices, fx)
        assert replayed.total_portfolio_nav_base == book.valuations[account.account_ref].total_portfolio_nav_base


def test_ppds_ledger_export_requires_full_cost_history() -> None:
    state = _state(_doc())
    with pytest.raises(DataContractError, match="TXN_LEDGER_EXPORT_REQUIRES_FULL_COST_HISTORY"):
        tx.to_ppds_ledger(state, "BROKER_A_MAIN")
    ledger = tx.to_ppds_ledger(state, "BANK_FCD")
    assert ledger.cash_by_currency() == {"USD": Decimal("500.00")}


def test_twr_and_xirr_golden_reference() -> None:
    doc = {"schema": tx.SCHEMA, "data_class": "SYNTHETIC_PUBLIC_FIXTURE", "batch_id": "SYN_PERF", "transactions": [
        {"transaction_id": "P_OPEN", "account_ref": "ACC_P", "event_type": "OPENING_CASH", "trade_date": "2026-01-01",
         "currency": "THB", "net_cash": "1000.00"},
        {"transaction_id": "P_DEP", "account_ref": "ACC_P", "event_type": "DEPOSIT", "trade_date": "2026-07-01",
         "currency": "THB", "net_cash": "500.00"},
    ]}
    state = _state(doc, date(2026, 12, 31))
    valuations = [(date(2026, 1, 1), Decimal("1000")), (date(2026, 7, 1), Decimal("1600")), (date(2026, 12, 31), Decimal("1700"))]
    report = performance_report(state, "TRANSACTIONS_RECONCILED", valuations, "THB", {})
    assert report["status"] == "PERFORMANCE_QUALIFIED"
    assert Decimal(report["twr_cumulative"]) == (Decimal("1700") / Decimal("1500") - 1).quantize(Decimal("1e-10"))
    expected = xirr([(date(2026, 1, 1), Decimal("-1000")), (date(2026, 7, 1), Decimal("-500")), (date(2026, 12, 31), Decimal("1700"))])
    assert report["xirr_annual"] == {"status": "ESTABLISHED", "value": f"{expected:.10f}"}
    assert report["value_change_excluding_flows"] == "200.00"


def _fixture_valuations() -> List[Tuple[date, Decimal]]:
    return [(date(2026, 1, 1), Decimal("23300")), (date(2026, 1, 5), Decimal("122300")), (date(2026, 2, 1), Decimal("142500")),
            (date(2026, 9, 1), Decimal("137000")), (AS_OF, Decimal("134691.50"))]


def test_withdrawal_makes_xirr_not_established_but_twr_qualified() -> None:
    fx = {(date(2026, 2, 1), "USD"): Decimal("33.00"), (date(2026, 9, 1), "USD"): Decimal("33.00")}
    report = performance_report(_state(_doc()), "TRANSACTIONS_RECONCILED", _fixture_valuations(), "THB", fx)
    assert report["status"] == "PERFORMANCE_QUALIFIED"
    assert report["xirr_annual"] == {"status": "XIRR_NOT_ESTABLISHED", "reason": "XIRR_UNDEFINED_SIGN_PATTERN"}
    assert report["fx_attribution"] == "FX_ATTRIBUTION_NOT_ESTABLISHED"
    assert report["external_withdrawals"] == "-8497.5000"


def test_performance_not_fabricated_when_evidence_missing() -> None:
    state = _state(_doc())
    fx = {(date(2026, 2, 1), "USD"): Decimal("33.00"), (date(2026, 9, 1), "USD"): Decimal("33.00")}
    valuations = _fixture_valuations()
    assert performance_report(state, "TRANSACTIONS_PARTIAL", valuations, "THB", fx)["status"] == "PERFORMANCE_NOT_ESTABLISHED"
    gap = [v for v in valuations if v[0] != date(2026, 2, 1)]
    missing = performance_report(state, "TRANSACTIONS_RECONCILED", gap, "THB", fx)
    assert (missing["status"], missing["reason"], missing["dates"]) == (
        "PERFORMANCE_NOT_ESTABLISHED", "VALUATION_MISSING_AT_FLOW_DATES", ["2026-02-01"])
    with pytest.raises(DataContractError, match="PERF_FX_MISSING"):
        performance_report(state, "TRANSACTIONS_RECONCILED", valuations, "THB", {})
    late = performance_report(state, "TRANSACTIONS_RECONCILED", valuations[1:], "THB", fx)
    assert late["reason"] == "FLOW_ON_OR_BEFORE_FIRST_VALUATION"


def test_owner_private_batch_is_gated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    doc = _doc()
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    path = tmp_path / "data" / "private" / "txns.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        tx.load_batch(path)


def _ratified(**changes: Any) -> Dict[str, Any]:
    record: Dict[str, Any] = json.loads(
        (Path(__file__).resolve().parents[3] / tx.AUTHORIZATION_RECORD).read_text(encoding="utf-8"))
    record.update(status="RATIFIED", ratified_by="OWNER", ratified_on="2026-01-01")
    record.update(changes)
    return record


def _private_batch(root: Path, monkeypatch: pytest.MonkeyPatch, record: Any, data_class: str = "OWNER_PRIVATE_OBSERVATION",
                   where: Tuple[str, ...] = ("data", "private")) -> Path:
    monkeypatch.setattr(po, "_repo_root", lambda: root)
    odr = root / tx.AUTHORIZATION_RECORD
    odr.parent.mkdir(parents=True, exist_ok=True)
    odr.write_text(record if isinstance(record, str) else json.dumps(record), encoding="utf-8")
    doc = _doc()
    doc["data_class"] = data_class
    path = root.joinpath(*where, "txns.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _refuse_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    def read(*_: Any) -> Any:
        raise AssertionError("private bytes were read before authorization")
    monkeypatch.setattr(po, "read_bounded_json", read)


@pytest.mark.parametrize("record", [
    "{not json", "[]",
    _ratified(capability="OWNER_PRIVATE_OBSERVATION_AUTHORIZED"),
    _ratified(status="PROPOSED_NOT_RATIFIED"), _ratified(status="REVOKED"), _ratified(status="ratified"),
    _ratified(ratified_by="CODING_AGENT"), _ratified(ratified_by=None),
    _ratified(ratified_on=None), _ratified(ratified_on=""), _ratified(ratified_on="today"),
    _ratified(ratified_on="2026-13-40"), _ratified(ratified_on="20260101"), _ratified(ratified_on=20260101),
    _ratified(scope_schemas=[]), _ratified(scope_schemas=["ACASH_PRIVATE_OBSERVATION_SNAPSHOT_V1_2"]),
    _ratified(scope_schemas="ACASH_CANONICAL_TRANSACTIONS_V1"),
], ids=["unparseable", "not_object", "snapshot_capability", "proposed", "revoked", "lowercase_status",
        "agent_ratifier", "no_ratifier", "no_date", "empty_date", "word_date", "impossible_date", "compact_date",
        "numeric_date", "empty_scope", "other_schema", "scope_not_list"])
def test_malformed_transaction_odr_refuses_before_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                          record: Any) -> None:
    path = _private_batch(tmp_path, monkeypatch, record)
    _refuse_reads(monkeypatch)
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED") as err:
        tx.load_batch(path)
    assert not any(leak in str(err.value) for leak in ("T_OPEN", "SYN_TXN", "txns.json", str(tmp_path)))


def test_snapshot_odr_does_not_extend_to_transactions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _private_batch(tmp_path, monkeypatch, _ratified(status="PROPOSED_NOT_RATIFIED"))
    snapshot_odr = Path(__file__).resolve().parents[3] / po.AUTHORIZATION_RECORD
    (tmp_path / po.AUTHORIZATION_RECORD).write_text(snapshot_odr.read_text(encoding="utf-8"), encoding="utf-8")
    assert po.odr_state() == "RATIFIED"
    _refuse_reads(monkeypatch)
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        tx.load_batch(path)


def test_ratified_transaction_odr_loads_private_batch_until_revoked(tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    path = _private_batch(tmp_path, monkeypatch, _ratified())
    batch = tx.load_batch(path)
    assert batch.data_class == "OWNER_PRIVATE_OBSERVATION" and batch.transactions
    (tmp_path / tx.AUTHORIZATION_RECORD).write_text(json.dumps(_ratified(status="REVOKED")), encoding="utf-8")
    _refuse_reads(monkeypatch)
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        tx.load_batch(path)


def test_ratified_odr_still_refuses_private_batch_in_a_tracked_location(tmp_path: Path,
                                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    path = _private_batch(tmp_path, monkeypatch, _ratified(), where=("tests", "fixtures"))
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        tx.load_batch(path)


def test_synthetic_batch_in_private_location_is_not_read_without_odr(tmp_path: Path,
                                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    path = _private_batch(tmp_path, monkeypatch, _ratified(status="PROPOSED_NOT_RATIFIED"), data_class="SYNTHETIC")
    _refuse_reads(monkeypatch)
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        tx.load_batch(path)


def test_private_and_synthetic_batches_never_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    private = tx.load_batch(_private_batch(tmp_path, monkeypatch, _ratified()))
    synthetic = tx.parse_batch(_doc())
    with pytest.raises(DataContractError, match="TXN_DATA_CLASS_MIXED"):
        tx.merge_batches([private, synthetic])
