"""V84.2 acceptance: HOOD evidence must never be double-counted, replayed, or silently rounded."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from acash.invest import reconciliation as rc

CUTOFF = datetime(2026, 11, 2, 22, 57, tzinfo=timezone.utc)   # opening baseline observation time
HOOD = rc.OrderEvidence(order_id="ORD_HOOD_1", portfolio="NEWWAVE", security_id="HOOD", side="BUY",
                        executed_at=datetime(2026, 11, 2, 17, 32, 54, tzinfo=timezone.utc),
                        quantity=Decimal("1.1619192"), price=Decimal("86.0645"),
                        amount=Decimal("100.00"), currency="USD")
HOOD_HOLDINGS = rc.HoldingEvidence(portfolio="NEWWAVE", security_id="HOOD",
                                   quantity=Decimal("1.1619193"),
                                   observed_at=datetime(2026, 11, 3, 20, 40, tzinfo=timezone.utc),
                                   price=Decimal("83.84"))
BASELINE_WITH_HOOD = [rc.BaselinePosition("DIME_SECURITIES", "HOOD", Decimal("1.1619193"), "NEWWAVE")]
BASELINE_WITHOUT_HOOD = [rc.BaselinePosition("DIME_SECURITIES", "VOO", Decimal("1"), "NEWWAVE")]


def test_pre_baseline_purchase_already_in_baseline_is_evidence_only() -> None:
    row = rc.classify_order(HOOD, BASELINE_WITH_HOOD, [], CUTOFF)
    assert row["decision"] == rc.IN_BASELINE
    assert row["cash_effect"] == "NONE_EVIDENCE_ONLY" and row["evidence_only"] is True
    assert row["requires_owner_confirmation"] is False


def test_pre_baseline_purchase_absent_from_baseline_needs_owner_amendment() -> None:
    row = rc.classify_order(HOOD, BASELINE_WITHOUT_HOOD, [], CUTOFF)
    assert row["decision"] == rc.BASELINE_OMITTED
    assert row["requires_owner_confirmation"] is True
    assert row["cash_effect"] == "NONE_EVIDENCE_ONLY"  # never a second debit


def test_historical_transaction_is_linked_not_replayed() -> None:
    row = rc.classify_order(HOOD, BASELINE_WITH_HOOD, [], CUTOFF)
    assert row["pre_baseline"] is True and row["evidence_only"] is True
    assert row["decision"] != rc.POST_BASELINE_MISSING


def test_duplicate_transaction_prevention() -> None:
    row = rc.classify_order(HOOD, BASELINE_WITH_HOOD, ["ORD_HOOD_1"], CUTOFF)
    assert row["decision"] == rc.IN_JOURNAL
    assert "zero new cash movement" in row["detail"]


def test_fractional_precision_difference_is_reported_not_rounded() -> None:
    check = rc.compare_quantities(Decimal("1.1619192"), Decimal("1.1619193"))
    assert check["status"] == rc.DISPLAY_DIFFERENCE
    assert check["baseline"] == "1.1619192" and check["observed"] == "1.1619193"
    assert check["delta"] == "0.0000001" and check["policy"] == rc.PRECISION_POLICY


def test_substantive_difference_is_not_mistaken_for_precision() -> None:
    assert rc.compare_quantities(Decimal("1"), Decimal("2"))["status"] == rc.SUBSTANTIVE
    assert rc.compare_quantities(None, Decimal("1"))["status"] == rc.PENDING


def test_snapshot_date_and_baseline_cutoff_stay_separate() -> None:
    # The order is on 2026-11-02 17:32 but the baseline cutoff is 22:57 the same day.
    assert HOOD.executed_at <= CUTOFF
    later = rc.OrderEvidence(**{**HOOD.__dict__,
                                "order_id": "ORD_LATE",
                                "executed_at": datetime(2026, 11, 3, 2, 0, tzinfo=timezone.utc)})
    assert later.executed_at > CUTOFF
    assert rc.classify_order(later, BASELINE_WITH_HOOD, [], CUTOFF)["decision"] == rc.POST_BASELINE_MISSING


def test_portfolio_grouping_four_to_five() -> None:
    change = rc.grouping_change(["VOO", "BIL", "GLD", "QQQ"], ["VOO", "BIL", "GLD", "QQQ", "HOOD"])
    assert change["status"] == "PORTFOLIO_GROUPING_CHANGED"
    assert change["added"] == ["HOOD"] and change["removed"] == []
    assert (change["baseline_count"], change["observed_count"]) == (4, 5)


def test_no_duplicated_cash_debit_even_with_an_order_amount() -> None:
    for held in (BASELINE_WITH_HOOD, BASELINE_WITHOUT_HOOD):
        row = rc.classify_order(HOOD, held, [], CUTOFF)
        assert row["cash_effect"] == "NONE_EVIDENCE_ONLY"
    assert rc.CASH_SCOPE_POLICY.startswith("FCD_AND_SECURITIES_CASH_ARE_SEPARATE")


def test_no_fabricated_fee() -> None:
    assert HOOD.fee is None and HOOD.fee_status == "FEE_NOT_ESTABLISHED"
    with_fee = rc.OrderEvidence(**{**HOOD.__dict__, "fee": Decimal("0")})
    assert with_fee.fee_status == "FEE_ESTABLISHED"  # an explicit broker zero is different from unknown


def test_restart_and_replay_are_deterministic() -> None:
    args: tuple[Any, ...] = ([HOOD], [HOOD_HOLDINGS], BASELINE_WITHOUT_HOOD, [], CUTOFF)
    assert rc.reconcile(*args) == rc.reconcile(*args)


def test_owner_confirmation_required_before_baseline_amendment() -> None:
    preview = rc.plan_baseline_amendment(BASELINE_WITHOUT_HOOD[0], HOOD_HOLDINGS, CUTOFF)
    assert preview["requires_owner_confirmation"] is True and preview["applied"] is False
    assert preview["cash_effect"] == "NONE_EVIDENCE_ONLY"


def test_summary_is_sanitized_and_pending_until_evidence_is_complete() -> None:
    summary = rc.reconcile([HOOD], [HOOD_HOLDINGS], BASELINE_WITHOUT_HOOD, [], CUTOFF)
    assert summary["status"] == rc.PENDING
    assert summary["pending_owner_confirmation"] == ["ORD_HOOD_1"]
    text = json.dumps(summary)
    for forbidden in ("100.00", "86.0645", "83.84", "3278.03"):
        assert forbidden not in text


def test_module_never_writes_or_reaches_the_network() -> None:
    source = Path(str(rc.__file__)).read_text(encoding="utf-8")
    for banned in ("import socket", "import urllib", "requests", "open(", "write_text", "write_bytes"):
        assert banned not in source
    assert rc.PRECISION_POLICY.startswith("PRESERVE_BOTH")


def test_cli_reports_codes_only(tmp_path: Path) -> None:
    doc = {"cutoff": "2026-11-02T22:57:00+00:00",
           "orders": [{"order_id": "ORD_HOOD_1", "portfolio": "NEWWAVE", "security_id": "HOOD",
                       "side": "BUY", "executed_at": "2026-11-02T17:32:54+00:00",
                       "quantity": "1.1619192", "price": "86.0645", "amount": "100.00",
                       "currency": "USD", "fee": None}],
           "holdings": [{"portfolio": "NEWWAVE", "security_id": "HOOD", "quantity": "1.1619193",
                         "observed_at": "2026-11-03T20:40:00+00:00"}],
           "baseline": [{"account_ref": "DIME_SECURITIES", "security_id": "VOO", "quantity": "1"}],
           "journal_order_ids": []}
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "acash.invest.reconciliation", str(path)],
                         capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 1  # PENDING is not success
    assert "OPENING_BASELINE_POSITION_OMITTED" in out.stdout
    for forbidden in ("86.0645", "3278.03"):
        assert forbidden not in out.stdout
    assert rc.main([str(tmp_path / "missing.json")]) == 2
    assert rc.main([]) == 2
