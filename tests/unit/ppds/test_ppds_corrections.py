"""ODR-006 append-only corrections: original evidence never changes; effective set resolves
deterministically from original + corrections (APPEND_ONLY_SUPERSEDE_BY_ID)."""

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.ppds import corrections as cr
from acash.ppds.transactions import parse_transaction, replay

ROW_BUY = {"transaction_id": "TX_AAAAAAAA", "account_ref": "ACC1", "event_type": "BUY",
           "trade_date": "2026-11-01", "security_id": "SYNA", "currency": "USD",
           "quantity": "10", "price": "100", "gross_amount": "1000", "net_cash": "-1000"}
ROW_SELL = {"transaction_id": "TX_BBBBBBBB", "account_ref": "ACC1", "event_type": "SELL",
            "trade_date": "2026-11-02", "security_id": "SYNA", "currency": "USD",
            "quantity": "4", "price": "110", "gross_amount": "440", "net_cash": "440"}
ROW_DEP = {"transaction_id": "TX_CCCCCCCC", "account_ref": "ACC1", "event_type": "DEPOSIT",
           "trade_date": "2026-11-03", "currency": "USD", "net_cash": "500"}


def _correction(cid: str, kind: str, target: str, reason: str = "r",
                replacement: Optional[Dict[str, Any]] = None, superseded_by: Optional[str] = None,
                confirmed_at: str = "2026-11-05T10:00:00Z") -> Dict[str, Any]:
    doc: Dict[str, Any] = {"correction_id": cid, "kind": kind, "target_id": target, "reason": reason,
                           "confirmed_by": "OWNER", "confirmed_at": confirmed_at}
    if replacement is not None:
        doc["replacement"] = replacement
    if superseded_by is not None:
        doc["superseded_by"] = superseded_by
    return doc


def test_void_removes_target_but_keeps_original_evidence() -> None:
    effective, audit = cr.resolve_effective([ROW_BUY, ROW_SELL],
                                            [cr.parse_correction(_correction("COR_VOIDAAAAA",
                                                                   cr.VOID_ENTERED_EVENT,
                                                                   "TX_AAAAAAAA"), 0)])
    ids = {r["transaction_id"] for r in effective}
    assert ids == {"TX_BBBBBBBB"}
    assert audit[0]["status"] == "APPLIED" and audit[0]["reason"] == "VOIDED"


def test_supersede_replaces_target_with_replacement() -> None:
    repl = dict(ROW_SELL, transaction_id="TX_SELLCORR", quantity="5", price="110",
                gross_amount="550", net_cash="550")
    effective, audit = cr.resolve_effective([ROW_BUY, ROW_SELL],
                                            [cr.parse_correction(_correction("COR_SUPAAAAA",
                                                                   cr.SUPERSEDE_ENTERED_EVENT,
                                                                   "TX_BBBBBBBB",
                                                                   replacement=repl), 0)])
    ids = {r["transaction_id"] for r in effective}
    assert ids == {"TX_AAAAAAAA", "TX_SELLCORR"}
    assert audit[0]["status"] == "APPLIED" and audit[0]["reason"] == "SUPERSEDED"


def test_double_application_is_rejected() -> None:
    corr = cr.parse_correction(_correction("COR_DUPAAAAA", cr.VOID_ENTERED_EVENT, "TX_AAAAAAAA"), 0)
    effective, audit = cr.resolve_effective([ROW_BUY], [corr, corr])
    assert effective == []
    statuses = {a["correction_id"]: a["status"] for a in audit}
    assert statuses["COR_DUPAAAAA"] == "REJECTED"
    assert "DOUBLE_APPLICATION" in str(audit[1]["reason"])


def test_nonexistent_target_is_rejected() -> None:
    _, audit = cr.resolve_effective([ROW_BUY],
                                    [cr.parse_correction(_correction("COR_NOPAAAAA",
                                                                   cr.VOID_ENTERED_EVENT,
                                                                   "TX_DOESNOTEXIST"), 0)])
    assert audit[0]["status"] == "REJECTED"
    assert "NONEEXISTENT_TARGET" in str(audit[0]["reason"])


def test_conflicting_supersession_of_same_target_is_rejected() -> None:
    repl = dict(ROW_SELL, transaction_id="TX_REPAAAAA", quantity="5", price="110",
                gross_amount="550", net_cash="550")
    repl2 = dict(ROW_SELL, transaction_id="TX_REPBBBBB", quantity="6", price="110",
                 gross_amount="660", net_cash="660")
    c1 = cr.parse_correction(_correction("COR_SUPAAAAA", cr.SUPERSEDE_ENTERED_EVENT, "TX_BBBBBBBB",
                                         replacement=repl), 0)
    c2 = cr.parse_correction(_correction("COR_SUPBBBBB", cr.SUPERSEDE_ENTERED_EVENT, "TX_BBBBBBBB",
                                         replacement=repl2, confirmed_at="2026-11-05T10:01:00Z"), 0)
    _, audit = cr.resolve_effective([ROW_BUY, ROW_SELL], [c1, c2])
    statuses = {a["correction_id"]: a["status"] for a in audit}
    assert statuses["COR_SUPAAAAA"] == "APPLIED"
    assert statuses["COR_SUPBBBBB"] == "REJECTED"
    assert "CONFLICTING_SUPERSESSION" in str(audit[1]["reason"])


def test_correction_of_already_voided_target_is_rejected() -> None:
    c_void = cr.parse_correction(_correction("COR_VOIDBBBBB", cr.VOID_ENTERED_EVENT, "TX_AAAAAAAA"), 0)
    c_revoid = cr.parse_correction(_correction("COR_REVOIDAAAA", cr.VOID_ENTERED_EVENT, "TX_AAAAAAAA",
                                               confirmed_at="2026-11-05T10:01:00Z"), 0)
    _, audit = cr.resolve_effective([ROW_BUY], [c_void, c_revoid])
    statuses = {a["correction_id"]: a["status"] for a in audit}
    assert statuses["COR_VOIDBBBBB"] == "APPLIED"
    assert statuses["COR_REVOIDAAAA"] == "REJECTED"
    assert "TARGET_ALREADY_VOIDED" in str(audit[1]["reason"])


def test_replacement_row_must_be_valid_transaction() -> None:
    """A replacement that is not a valid canonical transaction is refused at parse time."""
    bad = dict(ROW_SELL, transaction_id="TX_REPXAAA", event_type="NOT_A_REAL_EVENT")
    with pytest.raises(DataContractError):
        cr.parse_correction(_correction("COR_BADAAAAA", cr.SUPERSEDE_ENTERED_EVENT, "TX_BBBBBBBB",
                                        replacement=bad), 0)


def test_replacement_id_conflict_is_rejected() -> None:
    repl = dict(ROW_BUY, transaction_id="TX_AAAAAAAA")  # same id as an existing effective event
    _, audit = cr.resolve_effective([ROW_BUY, ROW_SELL],
                                    [cr.parse_correction(_correction("COR_CONFAAAAA",
                                                                   cr.SUPERSEDE_ENTERED_EVENT,
                                                                   "TX_BBBBBBBB",
                                                                   replacement=repl), 0)])
    assert audit[0]["status"] == "REJECTED"
    assert "REPLACEMENT_ID_CONFLICT" in str(audit[0]["reason"])


def test_deterministic_order_independent_of_input_order() -> None:
    c_void = cr.parse_correction(_correction("COR_VOIDCCCCC", cr.VOID_ENTERED_EVENT, "TX_AAAAAAAA",
                                             confirmed_at="2026-11-05T11:00:00Z"), 0)
    c_dep = cr.parse_correction(_correction("COR_DEPDDDDD", cr.VOID_ENTERED_EVENT, "TX_CCCCCCCC",
                                            confirmed_at="2026-11-05T09:00:00Z"), 0)
    eff1, _ = cr.resolve_effective([ROW_BUY, ROW_SELL, ROW_DEP], [c_void, c_dep])
    eff2, _ = cr.resolve_effective([ROW_BUY, ROW_SELL, ROW_DEP], [c_dep, c_void])
    assert {r["transaction_id"] for r in eff1} == {r["transaction_id"] for r in eff2} == {"TX_BBBBBBBB"}


def test_correction_chain_superseded_by_is_allowed_when_not_applied_yet() -> None:
    # superseded_by pointing to a correction applied earlier in the same batch is fine (chain),
    # pointing to one applied later would be a cycle under deterministic order.
    repl = dict(ROW_SELL, transaction_id="TX_REPZZZZ", quantity="2", price="110",
                gross_amount="220", net_cash="220")
    c1 = cr.parse_correction(_correction("COR_CHAINAAA", cr.SUPERSEDE_ENTERED_EVENT, "TX_BBBBBBBB",
                                         replacement=repl), 0)
    # c2 supersedes the replacement (target TX_REPZZZZ which now exists only effectively)
    c2 = cr.parse_correction(_correction("COR_CHAINBBB", cr.VOID_ENTERED_EVENT, "TX_REPZZZZ",
                                         confirmed_at="2026-11-05T10:01:00Z"), 0)
    effective, audit = cr.resolve_effective([ROW_BUY, ROW_SELL], [c1, c2])
    ids = {r["transaction_id"] for r in effective}
    assert ids == {"TX_AAAAAAAA"}
    assert all(a["status"] == "APPLIED" for a in audit)


def test_load_envelope_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "corrections.json"
    path.write_text(json.dumps({"schema": cr.CORRECTION_SCHEMA, "data_class": cr.CORRECTION_DATA_CLASS,
                                "corrections": []}), encoding="utf-8")
    env = cr.load_envelope(path)
    assert env["schema"] == cr.CORRECTION_SCHEMA and env["corrections"] == []


def test_effective_rows_replay_through_ppds() -> None:
    opening = {"transaction_id": "TX_OPENXXXX", "account_ref": "ACC1", "event_type": "DEPOSIT",
               "trade_date": "2026-10-30", "currency": "USD", "net_cash": "5000"}
    repl = dict(ROW_SELL, transaction_id="TX_SELLCORR", quantity="5", price="110",
                gross_amount="550", net_cash="550")
    effective, _ = cr.resolve_effective([opening, ROW_BUY, ROW_SELL],
                                        [cr.parse_correction(_correction("COR_RPLAAAAA",
                                                                   cr.SUPERSEDE_ENTERED_EVENT,
                                                                   "TX_BBBBBBBB",
                                                                   replacement=repl), 0)])
    txns = [parse_transaction(r, i) for i, r in enumerate(effective)]
    state = replay(txns, date(2026, 11, 10))
    assert state.lots[("ACC1", "SYNA")][0].quantity == 5  # corrected SELL quantity applies
