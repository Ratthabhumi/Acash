"""Adversarial validation for the V37B Evidence Overlay.

Matching results must be derived from provider rows; annual totals, event components,
cash entitlements and tax-year designations must stay separate; timestamps, rights and
serialization must not overstate evidence.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.evidence_overlay import (
    EvidenceOverlayRecord,
    build_v37b_evidence_overlay,
    export_overlay_to_csv,
    export_overlay_to_json,
    overlay_digest,
    reconcile_provider_distributions,
    validate_overlay_records,
)

FROZEN_CANONICAL_HASHES = {
    "bars_raw.csv": "b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91",
    "distributions.csv": "9885fcb8258dcd6dc8f944776834d49f3c6f914d260e5bdc7cd29ae1a1726ca0",
    "splits.csv": "c9b9d95cedd8479118b2a0489f665d81f035d790739a56dc7f844fca5001588d",
}
LOCAL_DIR = Path("data/local_research/v36/reconciled_max")
EVIDENCE_DIR = Path("docs/research/evidence")


def _event(**overrides: str) -> EvidenceOverlayRecord:
    fields = dict(
        question_id="Q1",
        symbol="BND",
        cusip="921937835",
        share_class="ETF",
        economic_event_id="EVT-1",
        evidence_scope="EVENT_FINANCIAL_COMPONENT",
        provider_event_id="PROV-1",
        source_title="OCC memo",
        source_url="https://example.com/memo",
        source_document_id="OCC-1",
        source_page_or_table="Notice",
        reporting_period="2020-12-23",
        tax_year="2020",
        ex_date="2020-12-23",
        record_date="UNKNOWN",
        payable_date="2020-12-29",
        cash_amount_per_share="0.0372",
        financial_component_type="CAPITAL_GAIN_SHORT_TERM",
        tax_classification="UNKNOWN",
        publication_or_acceptance_time="UNKNOWN",
        capture_time="UNKNOWN",
        historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
        evidence_class="OCC_EVENT_CORROBORATED",
        rights_status="RIGHTS_UNVERIFIED",
        matching_result="UNRESOLVED",
        remaining_gap="none",
    )
    fields.update(overrides)
    return EvidenceOverlayRecord(**fields)


def _annual(**overrides: str) -> EvidenceOverlayRecord:
    fields = dict(
        evidence_scope="ANNUAL_FINANCIAL_TOTAL",
        economic_event_id="BND-FY2021-CG-ANNUAL",
        provider_event_id="NONE",
        reporting_period="FY2021",
        tax_year="2021",
        ex_date="UNKNOWN",
        payable_date="UNKNOWN",
        cash_amount_per_share="0.183",
        financial_component_type="FINANCIAL_STATEMENT_ANNUAL_TOTAL",
        evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
        publication_or_acceptance_time="2026-04-27T17:36:08-04:00",
    )
    fields.update(overrides)
    return _event(**fields)


def _row(event_id: str = "PROV-1", **overrides: str) -> Dict[str, str]:
    row = {
        "symbol": "BND",
        "ex_date": "2020-12-23",
        "payable_date": "2020-12-29",
        "gross_amount": "0.0372",
        "distribution_type": "CAPITAL_GAIN_SHORT_TERM",
        "payable_date_source": "PROVIDER",
        "event_id": event_id,
    }
    row.update(overrides)
    return row


def _synthetic_ledger(records: List[EvidenceOverlayRecord]) -> List[Dict[str, str]]:
    """Synthetic provider rows mirroring each referenced event; candidates carry the provider's DIVIDEND_CASH label."""
    rows = []
    for rec in records:
        if rec.provider_event_id == "NONE":
            continue
        component = rec.financial_component_type
        rows.append(
            _row(
                rec.provider_event_id,
                ex_date=rec.ex_date,
                payable_date=rec.payable_date if rec.payable_date != "UNKNOWN" else rec.ex_date,
                gross_amount=rec.cash_amount_per_share,
                distribution_type="DIVIDEND_CASH" if component == "UNKNOWN" else component,
                payable_date_source="IMPUTED_EX_PLUS_6D" if component == "UNKNOWN" else "PROVIDER",
            )
        )
    return rows


# --- Defect reproductions ---------------------------------------------------------------


def test_annual_total_labelled_as_single_event_rejected() -> None:
    with pytest.raises(DataContractError, match="OVERLAY_ANNUAL_TOTAL_AS_EVENT"):
        _annual(cash_amount_per_share="0.1834", ex_date="2021-12-23")
    with pytest.raises(DataContractError, match="OVERLAY_ANNUAL_TOTAL_AS_EVENT"):
        _annual(provider_event_id="da4043ec")
    with pytest.raises(DataContractError, match="OVERLAY_ANNUAL_TOTAL_AS_EVENT"):
        _event(financial_component_type="FINANCIAL_STATEMENT_ANNUAL_TOTAL")


def test_provider_event_id_absent_from_ledger_fails_closed() -> None:
    rec = _event(provider_event_id="eb13dcb4-6894-4184-a1db-29746b8d9435")
    ledger = [_row("eb13dcb4-6894-4184-a1db-29746b8d9435#short_term")]
    with pytest.raises(DataContractError, match="OVERLAY_UNKNOWN_PROVIDER_EVENT_ID"):
        reconcile_provider_distributions(ledger, [rec])


def test_matching_identity_with_mismatched_amount_is_conflict() -> None:
    res = reconcile_provider_distributions([_row(gross_amount="0.0373")], [_event()])
    assert res.records[0].matching_result == "CONFLICTING_AMOUNT"
    assert res.real_event_matches == 0
    assert res.event_conflicts == 1


def test_same_amount_different_economic_event_is_not_a_match() -> None:
    res = reconcile_provider_distributions([_row(ex_date="2021-04-01")], [_event()])
    assert res.records[0].matching_result == "CONFLICTING_DATE"
    res = reconcile_provider_distributions([_row(distribution_type="CAPITAL_GAIN_LONG_TERM")], [_event()])
    assert res.records[0].matching_result == "CONFLICTING_COMPONENT"
    with pytest.raises(DataContractError, match="OVERLAY_PROVIDER_IDENTITY_MISMATCH"):
        reconcile_provider_distributions([_row(symbol="VOO")], [_event()])
    with pytest.raises(DataContractError, match="OVERLAY_PROVIDER_IDENTITY_MISMATCH"):
        reconcile_provider_distributions([_row(cusip="922908363")], [_event()])


def test_exact_event_match_requires_every_field() -> None:
    res = reconcile_provider_distributions([_row()], [_event()])
    assert res.records[0].matching_result == "MATCHED_OCC_EVENT"
    assert res.real_event_matches == 1
    res = reconcile_provider_distributions([_row(payable_date="2020-12-30")], [_event()])
    assert res.records[0].matching_result == "CONFLICTING_DATE"


def test_mixed_capital_gain_total_cannot_be_wholly_qsg() -> None:
    with pytest.raises(DataContractError, match="OVERLAY_QSG_WITHOUT_EVENT_PERCENTAGE"):
        _annual(tax_classification="QUALIFIED_SHORT_TERM_GAIN")
    with pytest.raises(DataContractError, match="OVERLAY_ANNUAL_TAX_CLASSIFICATION"):
        _annual(tax_classification="LONG_TERM_CAPITAL_GAIN")


def test_qsg_presence_without_event_percentage_rejected_on_events() -> None:
    with pytest.raises(DataContractError, match="OVERLAY_QSG_WITHOUT_EVENT_PERCENTAGE"):
        _event(tax_classification="QUALIFIED_SHORT_TERM_GAIN")


def test_missing_ex_date_cannot_be_matched() -> None:
    with pytest.raises(DataContractError, match="OVERLAY_MATCH_WITHOUT_EVENT_DATE"):
        _event(ex_date="UNKNOWN", evidence_class="UNRESOLVED", matching_result="MATCHED_ISSUER_DATE")
    with pytest.raises(DataContractError, match="OVERLAY_MATCH_WITHOUT_EVENT_DATE"):
        _annual(matching_result="MATCHED_ISSUER_DATE")
    with pytest.raises(DataContractError, match="OVERLAY_EVENT_DATE_UNKNOWN"):
        _event(ex_date="UNKNOWN")


def test_declared_match_without_checkable_evidence_rejected() -> None:
    secondary = _event(evidence_class="SECONDARY_INDICATION_ONLY", matching_result="CONFLICTING_DATE")
    with pytest.raises(DataContractError, match="OVERLAY_CLAIMED_MATCH_UNSUPPORTED"):
        reconcile_provider_distributions([_row()], [secondary])
    with pytest.raises(DataContractError, match="OVERLAY_MATCH_CLASS_INCONSISTENT"):
        _event(evidence_class="SECONDARY_INDICATION_ONLY", matching_result="MATCHED_OCC_EVENT")
    unsourced = _annual(cash_amount_per_share="UNKNOWN", matching_result="ANNUAL_TOTAL_CONSISTENT")
    with pytest.raises(DataContractError, match="OVERLAY_CLAIMED_MATCH_UNSUPPORTED"):
        reconcile_provider_distributions([], [unsourced])
    contradicted = _event(matching_result="MATCHED_OCC_EVENT")
    with pytest.raises(DataContractError, match="OVERLAY_CLAIMED_MATCH_UNSUPPORTED"):
        reconcile_provider_distributions([_row(gross_amount="0.04")], [contradicted])


def test_annual_total_compared_with_provider_capital_gains_within_rounding() -> None:
    rows = [
        _row("A", ex_date="2021-04-01", gross_amount="0.0534", distribution_type="CAPITAL_GAIN_LONG_TERM"),
        _row("B", ex_date="2021-12-23", gross_amount="0.13", distribution_type="CAPITAL_GAIN_LONG_TERM"),
        _row("C", ex_date="2021-12-23", gross_amount="0.140851", distribution_type="DIVIDEND_CASH"),
    ]
    assert reconcile_provider_distributions(rows, [_annual()]).annual_consistent == 1
    rows[0]["gross_amount"] = "0.0544"
    assert reconcile_provider_distributions(rows, [_annual()]).annual_inconsistent == 1


def test_publication_time_before_reporting_period_end_rejected() -> None:
    with pytest.raises(DataContractError, match="OVERLAY_PUBLICATION_BEFORE_PERIOD_END"):
        _annual(reporting_period="FY2019", tax_year="2019", publication_or_acceptance_time="2019-04-25T17:35:43-04:00")
    with pytest.raises(DataContractError, match="OVERLAY_TIMESTAMP_WITHOUT_ZONE"):
        _annual(publication_or_acceptance_time="2026-01-01T00:00:00")
    with pytest.raises(DataContractError, match="OVERLAY_TIMESTAMP_WITHOUT_ZONE"):
        _event(capture_time="2026-01-01")
    with pytest.raises(DataContractError, match="OVERLAY_INVALID_TIMESTAMP"):
        _event(capture_time="2026-10-30 at 11:00")
    with pytest.raises(DataContractError, match="OVERLAY_CAPTURE_BEFORE_PUBLICATION"):
        _annual(capture_time="2026-04-01T00:00:00+00:00")


def test_unverified_rights_cannot_be_promoted_to_permitted() -> None:
    with pytest.raises(DataContractError, match="OVERLAY_RIGHTS_PERMITTED_UNSUPPORTED"):
        _event(rights_status="RIGHTS_PERMITTED")
    with pytest.raises(DataContractError, match="OVERLAY_UNKNOWN_RIGHTS_STATUS"):
        _event(rights_status="PUBLIC_DOMAIN_ASSUMED")


def test_reordered_records_yield_byte_identical_outputs() -> None:
    records = build_v37b_evidence_overlay()
    reversed_records = list(reversed(records))
    assert export_overlay_to_json(records).encode() == export_overlay_to_json(reversed_records).encode()
    assert export_overlay_to_csv(records).encode() == export_overlay_to_csv(reversed_records).encode()
    ledger = _synthetic_ledger(records)
    a = reconcile_provider_distributions(ledger, records)
    b = reconcile_provider_distributions(list(reversed(ledger)), reversed_records)
    assert a.digest == b.digest == overlay_digest(a.records)
    assert a.records == b.records


def test_duplicate_economic_events_across_claims_rejected() -> None:
    with pytest.raises(DataContractError, match="OVERLAY_DUPLICATE_ECONOMIC_EVENT"):
        validate_overlay_records([_event(), _event(economic_event_id="EVT-2", question_id="Q2")])
    with pytest.raises(DataContractError, match="OVERLAY_DUPLICATE_ECONOMIC_EVENT_ID"):
        validate_overlay_records([_event(), _event(provider_event_id="PROV-2")])
    with pytest.raises(DataContractError, match="OVERLAY_DUPLICATE_PROVIDER_EVENT_ID"):
        reconcile_provider_distributions([_row(), _row()], [_event()])
    with pytest.raises(DataContractError, match="OVERLAY_CUSIP_SYMBOL_CONFLICT"):
        validate_overlay_records([_event(), _event(economic_event_id="E2", provider_event_id="P2", symbol="VOO")])


def test_unavailable_dataset_never_yields_empirical_pass() -> None:
    records = build_v37b_evidence_overlay()
    res = reconcile_provider_distributions(None, records)
    assert res.local_data_status == "LOCAL_DATA_UNAVAILABLE"
    assert res.real_event_matches == 0
    assert res.annual_consistent == 0 and res.annual_inconsistent == 0
    assert all(r.matching_result not in ("MATCHED_OCC_EVENT", "MATCHED_ISSUER_DATE") for r in res.records)


def test_malformed_fields_fail_closed() -> None:
    for bad, code in (
        ({"ex_date": "2020-02-30"}, "OVERLAY_INVALID_DATE"),
        ({"cash_amount_per_share": "-0.01"}, "OVERLAY_BAD_AMOUNT"),
        ({"cash_amount_per_share": "NaN"}, "OVERLAY_BAD_AMOUNT"),
        ({"cash_amount_per_share": "x"}, "OVERLAY_INVALID_AMOUNT"),
        ({"symbol": "bnd"}, "OVERLAY_INVALID_SYMBOL"),
        ({"question_id": ""}, "OVERLAY_EMPTY_QUESTION_ID"),
        ({"economic_event_id": ""}, "OVERLAY_EMPTY_ECONOMIC_EVENT_ID"),
        ({"provider_event_id": ""}, "OVERLAY_EMPTY_PROVIDER_EVENT_ID"),
        ({"evidence_class": "FABRICATED_PASS"}, "OVERLAY_UNKNOWN_EVIDENCE_CLASS"),
        ({"evidence_scope": "EVENT"}, "OVERLAY_UNKNOWN_EVIDENCE_SCOPE"),
        ({"cash_amount_per_share": "UNKNOWN"}, "OVERLAY_EVENT_WITHOUT_AMOUNT"),
    ):
        with pytest.raises(DataContractError, match=code):
            _event(**bad)
    with pytest.raises(DataContractError, match="OVERLAY_REPORTING_PERIOD_MISMATCH"):
        _annual(reporting_period="2021")
    with pytest.raises(DataContractError, match="OVERLAY_TAX_DESIGNATION_WITH_CASH"):
        _annual(evidence_scope="TAX_YEAR_DESIGNATION", reporting_period="2021", matching_result="NOT_APPLICABLE")


# --- Built overlay ----------------------------------------------------------------------


def test_built_overlay_scopes_and_claims_on_synthetic_ledger() -> None:
    records = build_v37b_evidence_overlay()
    assert len(records) == 24  # 10 annual + 9 event components + 5 tax-year designations
    assert all(r.capture_time == "UNKNOWN" for r in records)
    assert not any(r.publication_or_acceptance_time.startswith("2026-01-01") for r in records)
    res = reconcile_provider_distributions(_synthetic_ledger(records), records)
    by_id = {r.economic_event_id: r for r in res.records}
    assert res.real_event_matches == 3
    assert {k for k, r in by_id.items() if r.matching_result == "MATCHED_OCC_EVENT"} == {
        "BND-2020-12-23-ST",
        "BND-2020-12-23-LT",
        "BND-2021-12-23-LT",
    }
    assert res.event_unresolved == 6 and res.event_conflicts == 0
    assert (res.annual_consistent, res.annual_inconsistent, res.annual_unsourced) == (5, 3, 2)
    assert res.tax_designations == 5
    assert by_id["BND-FY2021-CG-ANNUAL"].ex_date == "UNKNOWN"
    assert by_id["BND-FY2020-CG-ANNUAL"].cash_amount_per_share == "UNKNOWN"
    assert by_id["BND-QSG-TY2020"].cash_amount_per_share == "NONE"


def test_frozen_canonical_d6_input_hashes_unchanged() -> None:
    if not (LOCAL_DIR / "bars_raw.csv").exists():
        pytest.skip("LOCAL_DATA_UNAVAILABLE: frozen-hash check not executed")
    for filename, expected in FROZEN_CANONICAL_HASHES.items():
        assert hashlib.sha256((LOCAL_DIR / filename).read_bytes()).hexdigest() == expected


def test_full_overlay_against_local_dataset_and_committed_artifacts() -> None:
    dist_file = LOCAL_DIR / "distributions.csv"
    if not dist_file.exists():
        pytest.skip("LOCAL_DATA_UNAVAILABLE: empirical reconciliation not executed")
    with dist_file.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    records = build_v37b_evidence_overlay(rows)
    assert len(records) == 87  # 10 annual + 9 event + 5 tax + 63 payable backlog
    res = reconcile_provider_distributions(rows, records)
    assert (res.imputed_payable_start, res.bnd_imputed_start, res.voo_imputed_start) == (63, 47, 16)
    assert (res.payable_matched, res.payable_unresolved) == (0, 63)
    assert (res.real_event_matches, res.event_conflicts, res.event_unresolved) == (3, 0, 6)
    assert (res.annual_consistent, res.annual_inconsistent, res.annual_unsourced) == (5, 3, 2)
    committed_json = (EVIDENCE_DIR / "v37b_evidence_overlay_20261030.json").read_bytes()
    committed_csv = (EVIDENCE_DIR / "v37b_evidence_overlay_20261030.csv").read_bytes()
    assert committed_json == export_overlay_to_json(res.records).encode()
    assert committed_csv == export_overlay_to_csv(res.records).encode()
    assert res.digest == hashlib.sha256(committed_json).hexdigest()
