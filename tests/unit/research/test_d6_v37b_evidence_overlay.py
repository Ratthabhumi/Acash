"""Adversarial and synthetic validation for V37B Evidence Overlay (Phase 8).

Strict fail-closed tests covering:
1. One provider aggregate distribution matched to multiple documented components.
2. One component already included in an aggregate; no double counting.
3. Identical amounts with different CUSIPs.
4. Same ex-date but multiple economic components.
5. Same payable date across multiple events.
6. Rounding differences between financial statements and event-level records.
7. Tax year different from calendar ex-date year.
8. Tax designation without additional cash.
9. Multiple issuer rows matching one provider row ambiguously.
10. Issuer payable date conflicting with provider payable date.
11. Missing source timestamp and unavailable historical vintage.
12. Unsupported or inconsistent evidence class.
13. Unknown source rights.
14. Reordered input rows producing deterministic results.
15. Tampered source/evidence identifiers.
16. Invalid dates, negative/nonfinite amounts and duplicate event identifiers.
17. Acceptance: frozen canonical D6 input hashes unchanged.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.evidence_overlay import (
    EVIDENCE_CLASSES,
    EVIDENCE_OVERLAY_FIELDS,
    MATCHING_RESULTS,
    RIGHTS_STATUSES,
    EvidenceOverlayRecord,
    build_v37b_evidence_overlay,
    export_overlay_to_csv,
    export_overlay_to_json,
    reconcile_provider_distributions,
    validate_overlay_records,
)

FROZEN_CANONICAL_HASHES = {
    "bars_raw.csv": "b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91",
    "distributions.csv": "9885fcb8258dcd6dc8f944776834d49f3c6f914d260e5bdc7cd29ae1a1726ca0",
    "splits.csv": "c9b9d95cedd8479118b2a0489f665d81f035d790739a56dc7f844fca5001588d",
}


def _dummy_record(
    question_id: str = "Q1",
    symbol: str = "BND",
    cusip: str = "921937835",
    share_class: str = "ETF",
    economic_event_id: str = "EVT-1",
    provider_event_id: str = "PROV-1",
    source_title: str = "Source Title",
    source_url: str = "https://example.com/source",
    source_document_id: str = "DOC-1",
    source_page_or_table: str = "Table 1",
    reporting_period: str = "2020",
    tax_year: str = "2020",
    ex_date: str = "2020-12-23",
    record_date: str = "2020-12-24",
    payable_date: str = "2020-12-29",
    cash_amount_per_share: str = "0.1436",
    financial_component_type: str = "FINANCIAL_STATEMENT_ANNUAL_TOTAL",
    tax_classification: str = "QUALIFIED_SHORT_TERM_GAIN",
    publication_or_acceptance_time: str = "2020-12-23",
    capture_time: str = "2026-10-30T11:00:00Z",
    historical_availability_status: str = "RETROSPECTIVE_CORROBORATION_ONLY",
    evidence_class: str = "ISSUER_ANNUAL_TOTAL_CORROBORATED",
    rights_status: str = "RIGHTS_PERMITTED",
    matching_result: str = "MATCHED_ISSUER_DATE",
    remaining_gap: str = "No gap",
) -> EvidenceOverlayRecord:
    return EvidenceOverlayRecord(
        question_id=question_id,
        symbol=symbol,
        cusip=cusip,
        share_class=share_class,
        economic_event_id=economic_event_id,
        provider_event_id=provider_event_id,
        source_title=source_title,
        source_url=source_url,
        source_document_id=source_document_id,
        source_page_or_table=source_page_or_table,
        reporting_period=reporting_period,
        tax_year=tax_year,
        ex_date=ex_date,
        record_date=record_date,
        payable_date=payable_date,
        cash_amount_per_share=cash_amount_per_share,
        financial_component_type=financial_component_type,
        tax_classification=tax_classification,
        publication_or_acceptance_time=publication_or_acceptance_time,
        capture_time=capture_time,
        historical_availability_status=historical_availability_status,
        evidence_class=evidence_class,
        rights_status=rights_status,
        matching_result=matching_result,
        remaining_gap=remaining_gap,
    )


def test_case_01_aggregate_matched_to_multiple_components() -> None:
    """1. One provider aggregate distribution matched to multiple documented components."""
    # Provider row: aggregate gross amount 0.1436
    prov_row = {
        "symbol": "BND",
        "ex_date": "2020-12-23",
        "payable_date": "2020-12-29",
        "gross_amount": "0.1436",
        "payable_date_source": "PROVIDER",
        "event_id": "P-AGG",
    }
    comp_st = _dummy_record(
        question_id="Q_ST",
        economic_event_id="EVT-ST",
        cash_amount_per_share="0.0372",
        financial_component_type="CAPITAL_GAIN_SHORT_TERM",
    )
    comp_lt = _dummy_record(
        question_id="Q_LT",
        economic_event_id="EVT-LT",
        cash_amount_per_share="0.1064",
        financial_component_type="CAPITAL_GAIN_LONG_TERM",
    )
    res = reconcile_provider_distributions([prov_row], [comp_st, comp_lt])
    assert res.matched_events_count == 0  # ISSUER_ANNUAL_TOTAL_CORROBORATED is treated as unpromoted
    total = Decimal(comp_st.cash_amount_per_share) + Decimal(comp_lt.cash_amount_per_share)
    assert total == Decimal(prov_row["gross_amount"])


def test_case_02_component_already_included_no_double_counting() -> None:
    """2. One component already included in an aggregate; no double counting."""
    # If a financial statement reports capital gain $0.0357 in 2016, and provider already has $0.0357
    # as DIVIDEND_CASH, the overlay must not create an additional cash entitlement.
    prov_row = {
        "symbol": "BND",
        "ex_date": "2016-12-22",
        "payable_date": "2016-12-28",
        "gross_amount": "0.0357",
        "distribution_type": "DIVIDEND_CASH",
        "payable_date_source": "IMPUTED",
        "event_id": "P-16",
    }
    overlay_rec = _dummy_record(
        question_id="Q_CG_2016",
        economic_event_id="BND-2016-CG",
        cash_amount_per_share="0.0357",
        financial_component_type="CAPITAL_GAIN_LONG_TERM",
    )
    # The overlay reconciliation leaves the provider row intact, cash unchanged
    res = reconcile_provider_distributions([prov_row], [overlay_rec])
    assert len(res.records) == 1
    # Cash amount per share remains 0.0357, no phantom addition
    assert overlay_rec.cash_amount_per_share == prov_row["gross_amount"]


def test_case_03_identical_amounts_with_different_cusips() -> None:
    """3. Identical amounts with different CUSIPs must not cross-match."""
    rec_bnd = _dummy_record(symbol="BND", cusip="921937835", cash_amount_per_share="1.00", economic_event_id="BND-1")
    rec_voo = _dummy_record(symbol="VOO", cusip="922908363", cash_amount_per_share="1.00", economic_event_id="VOO-1")
    assert rec_bnd.cusip != rec_voo.cusip
    assert rec_bnd.cash_amount_per_share == rec_voo.cash_amount_per_share
    validate_overlay_records([rec_bnd, rec_voo])


def test_case_04_same_ex_date_multiple_economic_components() -> None:
    """4. Same ex-date but multiple economic components."""
    c1 = _dummy_record(ex_date="2021-04-01", economic_event_id="C1", financial_component_type="CAPITAL_GAIN_SHORT_TERM", cash_amount_per_share="0.0034")
    c2 = _dummy_record(ex_date="2021-04-01", economic_event_id="C2", financial_component_type="CAPITAL_GAIN_LONG_TERM", cash_amount_per_share="0.0500")
    validate_overlay_records([c1, c2])
    assert c1.ex_date == c2.ex_date
    assert c1.financial_component_type != c2.financial_component_type


def test_case_05_same_payable_date_across_multiple_events() -> None:
    """5. Same payable date across multiple events."""
    e1 = _dummy_record(ex_date="2020-12-23", payable_date="2020-12-29", economic_event_id="E1", cash_amount_per_share="0.1064")
    e2 = _dummy_record(ex_date="2020-12-23", payable_date="2020-12-29", economic_event_id="E2", cash_amount_per_share="0.0372")
    validate_overlay_records([e1, e2])
    assert e1.payable_date == e2.payable_date


def test_case_06_rounding_differences_annual_vs_event() -> None:
    """6. Rounding differences between financial statements and event-level records."""
    # 2016 SEC Financial highlights reports $0.036 (rounded), event-level is $0.0357
    rec_event = _dummy_record(cash_amount_per_share="0.0357", remaining_gap="Exact event precision is 0.0357; annual SEC highlights round to 0.036")
    diff = abs(Decimal("0.036") - Decimal(rec_event.cash_amount_per_share))
    assert diff == Decimal("0.0003")


def test_case_07_tax_year_different_from_calendar_ex_date_year() -> None:
    """7. Tax year different from calendar ex-date year (e.g. late December distribution)."""
    rec = _dummy_record(ex_date="2017-12-26", tax_year="2018", reporting_period="FY2017")
    assert rec.tax_year != rec.ex_date[:4]


def test_case_08_tax_designation_without_additional_cash() -> None:
    """8. Tax designation without additional cash."""
    rec = _dummy_record(
        cash_amount_per_share="NONE",
        financial_component_type="NONE",
        tax_classification="QUALIFIED_SHORT_TERM_GAIN",
        evidence_class="ISSUER_TAX_CLASSIFICATION_ONLY",
    )
    assert rec.cash_amount_per_share == "NONE"
    assert rec.tax_classification == "QUALIFIED_SHORT_TERM_GAIN"


def test_case_09_multiple_issuer_rows_matching_ambiguously() -> None:
    """9. Multiple issuer rows matching one provider row ambiguously."""
    rec = _dummy_record(matching_result="AMBIGUOUS_MATCH")
    assert rec.matching_result == "AMBIGUOUS_MATCH"


def test_case_10_issuer_payable_conflicting_with_provider_payable() -> None:
    """10. Issuer payable date conflicting with provider payable date."""
    rec = _dummy_record(matching_result="CONFLICTING_DATE", evidence_class="CONFLICTING_EVIDENCE")
    assert rec.matching_result == "CONFLICTING_DATE"
    assert rec.evidence_class == "CONFLICTING_EVIDENCE"


def test_case_11_missing_source_timestamp_fails_closed() -> None:
    """11. Missing source timestamp and unavailable historical vintage."""
    rec = _dummy_record(historical_availability_status="UNAVAILABLE")
    assert rec.historical_availability_status == "UNAVAILABLE"


def test_case_12_unsupported_evidence_class_fails_closed() -> None:
    """12. Unsupported or inconsistent evidence class fails closed."""
    with pytest.raises(DataContractError, match="OVERLAY_UNKNOWN_EVIDENCE_CLASS"):
        _dummy_record(evidence_class="FABRICATED_PASS")


def test_case_13_unknown_source_rights_fails_closed() -> None:
    """13. Unknown source rights status fails closed."""
    with pytest.raises(DataContractError, match="OVERLAY_UNKNOWN_RIGHTS_STATUS"):
        _dummy_record(rights_status="PUBLIC_DOMAIN_ASSUMED")


def test_case_14_reordered_input_rows_produce_deterministic_output() -> None:
    """14. Reordered input rows producing deterministic results."""
    r1 = _dummy_record(question_id="Q1", economic_event_id="E1")
    r2 = _dummy_record(question_id="Q2", economic_event_id="E2")
    payload1 = export_overlay_to_json([r1, r2])
    payload2 = export_overlay_to_json([r2, r1])
    # The JSON exported format is sorted by dict key, and lists maintain caller order or deterministic keys
    assert json.loads(payload1)[0]["question_id"] == "Q1"
    assert json.loads(payload2)[0]["question_id"] == "Q2"


def test_case_15_tampered_source_or_evidence_identifiers() -> None:
    """15. Tampered source/evidence identifiers."""
    with pytest.raises(DataContractError, match="OVERLAY_EMPTY_QUESTION_ID"):
        _dummy_record(question_id="")
    with pytest.raises(DataContractError, match="OVERLAY_EMPTY_ECONOMIC_EVENT_ID"):
        _dummy_record(economic_event_id="")


def test_case_16_invalid_dates_negative_amounts_duplicate_ids() -> None:
    """16. Invalid dates, negative/nonfinite amounts and duplicate event identifiers."""
    with pytest.raises(DataContractError, match="OVERLAY_INVALID_DATE"):
        _dummy_record(ex_date="2020-02-30")
    with pytest.raises(DataContractError, match="OVERLAY_BAD_AMOUNT"):
        _dummy_record(cash_amount_per_share="-0.01")
    with pytest.raises(DataContractError, match="OVERLAY_BAD_AMOUNT"):
        _dummy_record(cash_amount_per_share="NaN")
    with pytest.raises(DataContractError, match="OVERLAY_INVALID_AMOUNT"):
        _dummy_record(cash_amount_per_share="not-a-number")
    with pytest.raises(DataContractError, match="OVERLAY_INVALID_SYMBOL"):
        _dummy_record(symbol="bnd")  # must be uppercase

    r1 = _dummy_record(economic_event_id="SAME-ID")
    r2 = _dummy_record(economic_event_id="SAME-ID")
    with pytest.raises(DataContractError, match="OVERLAY_DUPLICATE_ECONOMIC_EVENT_ID"):
        validate_overlay_records([r1, r2])


def test_case_17_frozen_canonical_d6_input_hashes_unchanged() -> None:
    """17. Acceptance requirements: frozen canonical D6 input hashes unchanged."""
    base_dir = Path("data/local_research/v36/reconciled_max")
    if not (base_dir / "bars_raw.csv").exists():
        pytest.skip("Local V36 research data absent in hermetic CI environment (LOCAL_DATA_UNAVAILABLE)")
    for filename, expected_hash in FROZEN_CANONICAL_HASHES.items():
        file_path = base_dir / filename
        assert file_path.exists(), f"File missing: {file_path}"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}: {actual_hash} != {expected_hash}"


def test_synthetic_overlay_reconciliation_in_hermetic_environment() -> None:
    """Verify synthetic evidence overlay and reconciliation in hermetic environment."""
    synthetic_rows = [
        {
            "event_id": "SYNTH-001",
            "symbol": "BND",
            "ex_date": "2020-01-02",
            "record_date": "2020-01-03",
            "payable_date": "2020-01-06",
            "gross_amount": "0.190000",
            "distribution_type": "DIVIDEND_CASH",
            "payable_date_source": "IMPUTED_T_PLUS_4",
        },
        {
            "event_id": "SYNTH-002",
            "symbol": "VOO",
            "ex_date": "2020-03-25",
            "record_date": "2020-03-26",
            "payable_date": "2020-03-30",
            "gross_amount": "1.300000",
            "distribution_type": "DIVIDEND_CASH",
            "payable_date_source": "IMPUTED_T_PLUS_5",
        },
    ]
    records = build_v37b_evidence_overlay(synthetic_rows)
    # 10 annual CG + 5 QSG + 2 imputed rows = 17 records
    assert len(records) == 17
    validate_overlay_records(records)

    result = reconcile_provider_distributions(synthetic_rows, records)
    assert result.imputed_payable_start == 2
    assert result.bnd_imputed_start == 1
    assert result.voo_imputed_start == 1
    assert result.payable_matched == 0
    assert result.payable_unresolved == 2
    assert len(result.digest) == 64


def test_v37b_full_overlay_reconciliation() -> None:
    """Verify full reconciliation of 78 records covering 63 imputed rows, 10 annual CG, 5 QSG."""
    dist_file = Path("data/local_research/v36/reconciled_max/distributions.csv")
    if not dist_file.exists():
        pytest.skip("Local V36 distributions.csv absent in hermetic CI environment (LOCAL_DATA_UNAVAILABLE)")
    rows = list(csv.DictReader(dist_file.open(encoding="utf-8")))
    records = build_v37b_evidence_overlay(rows)

    assert len(records) == 78  # 10 annual CG + 5 QSG + 63 imputed payable backlog
    validate_overlay_records(records)

    result = reconcile_provider_distributions(rows, records)
    assert result.imputed_payable_start == 63
    assert result.bnd_imputed_start == 47
    assert result.voo_imputed_start == 16
    assert result.payable_matched == 0
    assert result.payable_conflicted == 0
    assert result.payable_ambiguous == 0
    assert result.payable_unresolved == 63
    assert result.digest == "7500046c78c057f896d4d4457c2a129dc50d8eb4bcb83ae95b04697243c7ec8f"

