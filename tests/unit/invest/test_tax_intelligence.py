"""Tax evidence: aggregates stay aggregates, pre-baseline trades stay candidates, nothing is assumed."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import tax_intelligence as tax

BASELINE = date(2026, 11, 2)
SUMMARY: Dict[str, Any] = {
    "tax_year": 2026, "covered_from": "2026-01-01", "covered_to": "2026-09-30",
    "funds_in_usd": "3475.59", "funds_out_usd": "6015.01",
    "gross_dividends_usd": "123.74", "withheld_usd": "12.05", "net_dividends_usd": "111.69",
    "source": "DIME_ANNUAL_SUMMARY", "observed_at": "2026-11-05T00:15:00+07:00", "publication_lag_days": 6,
}
TRADES: List[Dict[str, Any]] = [
    {"date": "2026-11-02", "security_id": "HOOD", "amount": "100.00", "amount_currency": "USD",
     "shares": "1.1619192", "price_per_share": "86.0645", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "GE", "amount": "100.00", "amount_currency": "USD",
     "shares": "0.3269861", "price_per_share": "305.3340", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "GEV", "amount": "100.00", "amount_currency": "USD",
     "shares": "0.1160463", "price_per_share": "860.3460", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "VOO", "amount": "3000.00", "amount_currency": "THB",
     "shares": "0.1271353", "price_per_share": "695.7940", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "CRWV", "amount": "1500.68", "amount_currency": "THB",
     "shares": "27.4028", "price_per_share": "54.7780", "price_currency": "USD", "status": "CANCELLED"},
]
CASH: List[Dict[str, Any]] = [
    {"date": "2026-10-30", "description": "Dime! USD +180.00", "kind": "deposit",
     "amount": "180.00", "currency": "USD"},
    {"date": "2026-10-30", "description": "META -180.00", "kind": "buy", "amount": "-180.00",
     "currency": "USD"},
    {"date": "2026-10-30", "description": "Dime! FCD -> Dime! USD internal transfer", "kind": "internal",
     "amount": "180.00", "currency": "USD"},
]


def test_annual_arithmetic_and_coverage_are_checked() -> None:
    doc = tax.build_evidence(SUMMARY, TRADES, CASH, BASELINE)
    checks = doc["annual_summary"]["checks"]
    assert checks["gross_equals_net_plus_withheld"] is True
    assert checks["coverage_complete_for_year"] is False
    assert checks["missing_months"] == 10
    assert checks["next_expected_update"] == "2026-11-06"
    assert checks["effective_withholding_ratio"] == "0.0974"
    assert checks["observed_ratio_is_not_a_treaty_rate"] is True


def test_broken_arithmetic_is_refused() -> None:
    broken = {**SUMMARY, "net_dividends_usd": "111.70"}
    with pytest.raises(DataContractError, match="TAX_EVIDENCE_ARITHMETIC_MISMATCH"):
        tax.parse_summary(broken)


def test_aggregates_never_become_journal_events() -> None:
    doc = tax.build_evidence(SUMMARY, TRADES, CASH, BASELINE)
    assert doc["staged_trades"]["accepted_for_journal"] == []
    assert all("event_class" not in e and e["verification_state"] == "STAGED_EVIDENCE"
               for e in doc["staged_trades"]["pre_baseline_candidates"])
    assert "DIVIDEND" not in str(doc["staged_trades"])


def test_pre_baseline_trades_are_candidates_not_new_events() -> None:
    staged = tax.stage_trades(TRADES, BASELINE)
    assert len(staged["pre_baseline_candidates"]) == 4  # every executed row is at or before the baseline
    assert all(c["reason"] == "PRE_BASELINE_CANDIDATE" for c in staged["pre_baseline_candidates"])
    later = tax.stage_trades([{**TRADES[0], "date": "2026-11-04"}], BASELINE)
    assert len(later["accepted_for_journal"]) == 1


def test_cancelled_order_creates_no_position() -> None:
    staged = tax.stage_trades(TRADES, BASELINE)
    rejected = {r["security_id"]: r for r in staged["rejected"]}
    assert rejected["CRWV"]["reason"] == "CANCELLED_ORDER" and rejected["CRWV"]["creates_position"] is False
    assert "CRWV" not in {c["security_id"] for c in staged["pre_baseline_candidates"]}


def test_duplicate_event_is_detected() -> None:
    first = tax.stage_trades([{**TRADES[0], "date": "2026-11-04"}], BASELINE)
    event_id = first["accepted_for_journal"][0]["event_id"]
    again = tax.stage_trades([{**TRADES[0], "date": "2026-11-04"}], BASELINE, [event_id])
    assert again["rejected"][0]["reason"] == "DUPLICATE_EVENT"


def test_ge_and_gev_are_separate_events() -> None:
    staged = tax.stage_trades(TRADES, BASELINE)
    symbols = [c["security_id"] for c in staged["pre_baseline_candidates"]]
    assert symbols.count("GE") == 1 and symbols.count("GEV") == 1


def test_thb_settled_trade_keeps_both_currencies_without_an_invented_rate() -> None:
    voo = [t for t in TRADES if t["security_id"] == "VOO"][0]
    staged = tax.stage_trades([voo], BASELINE)
    entry = staged["pre_baseline_candidates"][0]
    assert entry["amount_currency"] == "THB" and entry["price_currency"] == "USD"
    assert "fx_rate" not in entry and "thb_per_usd" not in entry


def test_internal_fcd_transfer_is_not_a_remittance() -> None:
    assert tax.classify_cash_flow("internal", "Dime! FCD -> Dime! USD") == "BROKER_ACCOUNT_INTERNAL_TRANSFER"
    assert tax.classify_cash_flow("deposit", "Dime! USD +180.00") == "UNMATCHED_TRANSFER"
    assert tax.classify_cash_flow("transfer", "remit to Thailand Kasikorn") != "BROKER_ACCOUNT_INTERNAL_TRANSFER"


def test_tax_liability_and_credit_stay_unverified() -> None:
    doc = tax.build_evidence(SUMMARY, TRADES, CASH, BASELINE)
    assert doc["tax_liability"]["status"] == "NOT_ESTABLISHED"
    assert doc["tax_liability"]["credit_eligibility"] == "CREDIT_ELIGIBILITY_UNVERIFIED"
    assert doc["readiness"]["historical_performance"] == "DATA_REQUIRED"
    assert doc["readiness"]["trade_history"] == "PARTIAL_EVIDENCE_ONLY"
    assert Decimal(doc["annual_summary"]["net_dividends_usd"]) == Decimal("111.69")


def test_smuggled_trade_fields_are_refused() -> None:
    with pytest.raises(DataContractError, match="unexpected trade field"):
        tax.stage_trades([{**TRADES[0], "fx_rate": "33.7"}], BASELINE)
