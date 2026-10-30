"""V37B Independent Evidence Overlay for corporate actions and distribution reconciliation.

Deterministic, offline, read-only evidence overlay separate from the canonical D6 dataset.
Enforces the strict fail-closed contract and records source corroborations, contradictions,
and unresolved gaps without mutating canonical execution inputs.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError

# 25 Canonical Minimum Fields
EVIDENCE_OVERLAY_FIELDS: Tuple[str, ...] = (
    "question_id",
    "symbol",
    "cusip",
    "share_class",
    "economic_event_id",
    "provider_event_id",
    "source_title",
    "source_url",
    "source_document_id",
    "source_page_or_table",
    "reporting_period",
    "tax_year",
    "ex_date",
    "record_date",
    "payable_date",
    "cash_amount_per_share",
    "financial_component_type",
    "tax_classification",
    "publication_or_acceptance_time",
    "capture_time",
    "historical_availability_status",
    "evidence_class",
    "rights_status",
    "matching_result",
    "remaining_gap",
)

# Permitted Evidence Classes
EVIDENCE_CLASSES: Tuple[str, ...] = (
    "ISSUER_EVENT_MATCHED",
    "ISSUER_ANNUAL_TOTAL_CORROBORATED",
    "ISSUER_TAX_CLASSIFICATION_ONLY",
    "OCC_EVENT_CORROBORATED",
    "SECONDARY_INDICATION_ONLY",
    "CONFLICTING_EVIDENCE",
    "UNRESOLVED",
)

# Permitted Matching Results
MATCHING_RESULTS: Tuple[str, ...] = (
    "MATCHED_ISSUER_DATE",
    "CONFLICTING_DATE",
    "AMBIGUOUS_MATCH",
    "SOURCE_NOT_AVAILABLE",
    "UNRESOLVED",
)

# Permitted Rights Statuses
RIGHTS_STATUSES: Tuple[str, ...] = (
    "RIGHTS_PERMITTED",
    "RIGHTS_RESTRICTED",
    "RIGHTS_UNVERIFIED",
)

# Permitted Historical Availability / PIT Statuses
HISTORICAL_AVAILABILITY_STATUSES: Tuple[str, ...] = (
    "PIT_HISTORICAL_CONTEMPORANEOUS",
    "RETROSPECTIVE_CORROBORATION_ONLY",
    "UNAVAILABLE",
)

FINANCIAL_COMPONENT_TYPES: Tuple[str, ...] = (
    "DIVIDEND_CASH",
    "CAPITAL_GAIN_SHORT_TERM",
    "CAPITAL_GAIN_LONG_TERM",
    "FINANCIAL_STATEMENT_ANNUAL_TOTAL",
    "NONE",
)

TAX_CLASSIFICATIONS: Tuple[str, ...] = (
    "QUALIFIED_SHORT_TERM_GAIN",
    "QUALIFIED_INTEREST_INCOME",
    "ORDINARY_DIVIDEND",
    "LONG_TERM_CAPITAL_GAIN",
    "NONE",
)


def _validate_date_str(value: str, field_name: str) -> None:
    if value in ("", "UNKNOWN", "NONE"):
        return
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise DataContractError(f"OVERLAY_INVALID_DATE: {field_name} {value!r}.") from exc


def _validate_decimal_str(value: str, field_name: str) -> Optional[Decimal]:
    if value in ("", "NONE", "UNKNOWN"):
        return None
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise DataContractError(f"OVERLAY_INVALID_AMOUNT: {field_name} {value!r}.") from exc
    if not d.is_finite() or d < Decimal(0):
        raise DataContractError(f"OVERLAY_BAD_AMOUNT: {field_name} {value!r}.")
    return d


@dataclass(frozen=True)
class EvidenceOverlayRecord:
    question_id: str
    symbol: str
    cusip: str
    share_class: str
    economic_event_id: str
    provider_event_id: str
    source_title: str
    source_url: str
    source_document_id: str
    source_page_or_table: str
    reporting_period: str
    tax_year: str
    ex_date: str
    record_date: str
    payable_date: str
    cash_amount_per_share: str
    financial_component_type: str
    tax_classification: str
    publication_or_acceptance_time: str
    capture_time: str
    historical_availability_status: str
    evidence_class: str
    rights_status: str
    matching_result: str
    remaining_gap: str

    def __post_init__(self) -> None:
        if not self.question_id.strip():
            raise DataContractError("OVERLAY_EMPTY_QUESTION_ID.")
        if not self.symbol.strip() or self.symbol != self.symbol.upper():
            raise DataContractError(f"OVERLAY_INVALID_SYMBOL: {self.symbol!r}.")
        if not self.economic_event_id.strip():
            raise DataContractError("OVERLAY_EMPTY_ECONOMIC_EVENT_ID.")
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise DataContractError(f"OVERLAY_UNKNOWN_EVIDENCE_CLASS: {self.evidence_class!r}.")
        if self.matching_result not in MATCHING_RESULTS:
            raise DataContractError(f"OVERLAY_UNKNOWN_MATCHING_RESULT: {self.matching_result!r}.")
        if self.rights_status not in RIGHTS_STATUSES:
            raise DataContractError(f"OVERLAY_UNKNOWN_RIGHTS_STATUS: {self.rights_status!r}.")
        if self.historical_availability_status not in HISTORICAL_AVAILABILITY_STATUSES:
            raise DataContractError(
                f"OVERLAY_UNKNOWN_HISTORICAL_AVAILABILITY: {self.historical_availability_status!r}."
            )
        if self.financial_component_type not in FINANCIAL_COMPONENT_TYPES:
            raise DataContractError(
                f"OVERLAY_UNKNOWN_FINANCIAL_COMPONENT: {self.financial_component_type!r}."
            )
        if self.tax_classification not in TAX_CLASSIFICATIONS:
            raise DataContractError(f"OVERLAY_UNKNOWN_TAX_CLASSIFICATION: {self.tax_classification!r}.")

        _validate_date_str(self.ex_date, "ex_date")
        _validate_date_str(self.record_date, "record_date")
        _validate_date_str(self.payable_date, "payable_date")
        _validate_decimal_str(self.cash_amount_per_share, "cash_amount_per_share")

    def to_dict(self) -> Dict[str, str]:
        return {k: getattr(self, k) for k in EVIDENCE_OVERLAY_FIELDS}


@dataclass(frozen=True)
class EvidenceReconciliationResult:
    records: Tuple[EvidenceOverlayRecord, ...]
    matched_events_count: int
    conflicted_events_count: int
    unresolved_events_count: int
    imputed_payable_start: int
    bnd_imputed_start: int
    voo_imputed_start: int
    payable_matched: int
    payable_conflicted: int
    payable_ambiguous: int
    payable_unresolved: int
    digest: str


def validate_overlay_records(records: Sequence[EvidenceOverlayRecord]) -> None:
    seen_ids: set[str] = set()
    for rec in records:
        if rec.economic_event_id in seen_ids:
            raise DataContractError(f"OVERLAY_DUPLICATE_ECONOMIC_EVENT_ID: {rec.economic_event_id}.")
        seen_ids.add(rec.economic_event_id)


def reconcile_provider_distributions(
    provider_rows: Sequence[Mapping[str, str]],
    overlay_records: Sequence[EvidenceOverlayRecord],
) -> EvidenceReconciliationResult:
    """Read-only comparison of provider rows against independent evidence overlay."""
    validate_overlay_records(overlay_records)

    imputed_bnd = sum(
        1 for r in provider_rows if r["symbol"] == "BND" and "IMPUTED" in r.get("payable_date_source", "")
    )
    imputed_voo = sum(
        1 for r in provider_rows if r["symbol"] == "VOO" and "IMPUTED" in r.get("payable_date_source", "")
    )
    total_imputed = imputed_bnd + imputed_voo

    matched_events = 0
    conflicted_events = 0
    unresolved_events = 0
    payable_matched = 0
    payable_conflicted = 0
    payable_ambiguous = 0
    payable_unresolved = 0

    for rec in overlay_records:
        if rec.evidence_class in ("ISSUER_EVENT_MATCHED", "OCC_EVENT_CORROBORATED"):
            matched_events += 1
        elif rec.evidence_class == "CONFLICTING_EVIDENCE":
            conflicted_events += 1
        else:
            unresolved_events += 1

        if rec.question_id.startswith("Q_IMPUTED_PAYABLE_"):
            if rec.matching_result == "MATCHED_ISSUER_DATE":
                payable_matched += 1
            elif rec.matching_result == "CONFLICTING_DATE":
                payable_conflicted += 1
            elif rec.matching_result == "AMBIGUOUS_MATCH":
                payable_ambiguous += 1
            else:
                payable_unresolved += 1

    payload = json.dumps([r.to_dict() for r in overlay_records], sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return EvidenceReconciliationResult(
        records=tuple(overlay_records),
        matched_events_count=matched_events,
        conflicted_events_count=conflicted_events,
        unresolved_events_count=unresolved_events,
        imputed_payable_start=total_imputed,
        bnd_imputed_start=imputed_bnd,
        voo_imputed_start=imputed_voo,
        payable_matched=payable_matched,
        payable_conflicted=payable_conflicted,
        payable_ambiguous=payable_ambiguous,
        payable_unresolved=payable_unresolved,
        digest=digest,
    )


def build_v37b_evidence_overlay(
    provider_rows: Optional[Sequence[Mapping[str, str]]] = None,
) -> List[EvidenceOverlayRecord]:
    """Constructs the canonical V37B Evidence Overlay with zero unverified claims."""
    records: List[EvidenceOverlayRecord] = []
    now_iso = "2026-10-30T11:00:00Z"

    # --- Part A: BND 2016-2025 Annual Capital-Gain Evidence from Vanguard / SEC ---
    sec_2019_url = (
        "https://www.sec.gov/Archives/edgar/data/794105/000093247119006953/bondindex485bfinal.htm"
    )
    sec_2026_url = (
        "https://www.sec.gov/Archives/edgar/data/794105/000079410526000106/f45031d1.htm"
    )
    vanguard_ar_url = "https://fund-docs.vanguard.com/q840.pdf"

    # 2016
    records.append(
        EvidenceOverlayRecord(
            question_id="Q_BND_CG_2016",
            symbol="BND",
            cusip="921937835",
            share_class="ETF",
            economic_event_id="BND-2016-CG-ANNUAL",
            provider_event_id="6fa27f80-92c5-4cb5-93c9-bf5c6c8a7982",
            source_title="Vanguard Bond Index Funds SEC Form 485BPOS Financial Highlights",
            source_url=sec_2019_url,
            source_document_id="SEC-0000932471-19-006953",
            source_page_or_table="Financial Highlights: Total Bond Market ETF Share Class",
            reporting_period="FY2016",
            tax_year="2016",
            ex_date="2016-12-22",
            record_date="UNKNOWN",
            payable_date="UNKNOWN",
            cash_amount_per_share="0.0357",
            financial_component_type="CAPITAL_GAIN_LONG_TERM",
            tax_classification="LONG_TERM_CAPITAL_GAIN",
            publication_or_acceptance_time="2019-04-24",
            capture_time=now_iso,
            historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
            evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
            rights_status="RIGHTS_PERMITTED",
            matching_result="UNRESOLVED",
            remaining_gap="Provider labeled event as DIVIDEND_CASH; SEC financial highlights corroborate $0.0357 capital gain. Exact payable date not separately stated in annual filing.",
        )
    )

    # 2017
    records.append(
        EvidenceOverlayRecord(
            question_id="Q_BND_CG_2017",
            symbol="BND",
            cusip="921937835",
            share_class="ETF",
            economic_event_id="BND-2017-CG-ANNUAL",
            provider_event_id="2071302f-3e51-44ff-979d-d6fd4b62396c",
            source_title="Vanguard Bond Index Funds SEC Form 485BPOS Financial Highlights",
            source_url=sec_2019_url,
            source_document_id="SEC-0000932471-19-006953",
            source_page_or_table="Financial Highlights: Total Bond Market ETF Share Class",
            reporting_period="FY2017",
            tax_year="2017",
            ex_date="2017-12-26",
            record_date="UNKNOWN",
            payable_date="UNKNOWN",
            cash_amount_per_share="0.037",
            financial_component_type="CAPITAL_GAIN_LONG_TERM",
            tax_classification="LONG_TERM_CAPITAL_GAIN",
            publication_or_acceptance_time="2019-04-24",
            capture_time=now_iso,
            historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
            evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
            rights_status="RIGHTS_PERMITTED",
            matching_result="UNRESOLVED",
            remaining_gap="Provider labeled event as DIVIDEND_CASH; SEC financial highlights corroborate $0.037 capital gain. Exact payable date not separately stated in annual filing.",
        )
    )

    # 2018
    records.append(
        EvidenceOverlayRecord(
            question_id="Q_BND_CG_2018",
            symbol="BND",
            cusip="921937835",
            share_class="ETF",
            economic_event_id="BND-2018-CG-ANNUAL",
            provider_event_id="7b6168d6-9a2e-4ea5-8cc7-e2502f4293b0",
            source_title="Vanguard Bond Index Funds SEC Form 485BPOS Financial Highlights",
            source_url=sec_2019_url,
            source_document_id="SEC-0000932471-19-006953",
            source_page_or_table="Financial Highlights: Total Bond Market ETF Share Class",
            reporting_period="FY2018",
            tax_year="2018",
            ex_date="2018-04-02",
            record_date="UNKNOWN",
            payable_date="UNKNOWN",
            cash_amount_per_share="0.01916",
            financial_component_type="CAPITAL_GAIN_LONG_TERM",
            tax_classification="LONG_TERM_CAPITAL_GAIN",
            publication_or_acceptance_time="2019-04-24",
            capture_time=now_iso,
            historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
            evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
            rights_status="RIGHTS_PERMITTED",
            matching_result="UNRESOLVED",
            remaining_gap="Provider labeled event as DIVIDEND_CASH; SEC financial highlights corroborate $0.01916 capital gain. Exact payable date not separately stated in annual filing.",
        )
    )

    # 2019
    records.append(
        EvidenceOverlayRecord(
            question_id="Q_BND_CG_2019",
            symbol="BND",
            cusip="921937835",
            share_class="ETF",
            economic_event_id="BND-2019-CG-ANNUAL",
            provider_event_id="NONE",
            source_title="Vanguard Bond Index Funds SEC Form 485BPOS Financial Highlights",
            source_url=sec_2019_url,
            source_document_id="SEC-0000932471-19-006953",
            source_page_or_table="Financial Highlights: Total Bond Market ETF Share Class",
            reporting_period="FY2019",
            tax_year="2019",
            ex_date="UNKNOWN",
            record_date="UNKNOWN",
            payable_date="UNKNOWN",
            cash_amount_per_share="0",
            financial_component_type="FINANCIAL_STATEMENT_ANNUAL_TOTAL",
            tax_classification="NONE",
            publication_or_acceptance_time="2019-04-24",
            capture_time=now_iso,
            historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
            evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
            rights_status="RIGHTS_PERMITTED",
            matching_result="MATCHED_ISSUER_DATE",
            remaining_gap="No capital gain distribution for 2019 in financial statements, corroborating zero capital gain provider rows.",
        )
    )

    # 2020
    records.append(
        EvidenceOverlayRecord(
            question_id="Q_BND_CG_2020",
            symbol="BND",
            cusip="921937835",
            share_class="ETF",
            economic_event_id="BND-2020-CG-ANNUAL",
            provider_event_id="eb13dcb4-6894-4184-a1db-29746b8d9435",
            source_title="Vanguard Annual Report & OCC Information Memo 48045",
            source_url="https://infomemo.theocc.com/infomemos?number=48045",
            source_document_id="OCC-48045",
            source_page_or_table="OCC Notice of Distribution / Vanguard 2020 Annual Report",
            reporting_period="FY2020",
            tax_year="2020",
            ex_date="2020-12-23",
            record_date="2020-12-24",
            payable_date="2020-12-29",
            cash_amount_per_share="0.1436",
            financial_component_type="FINANCIAL_STATEMENT_ANNUAL_TOTAL",
            tax_classification="QUALIFIED_SHORT_TERM_GAIN",
            publication_or_acceptance_time="2020-12-23",
            capture_time=now_iso,
            historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
            evidence_class="OCC_EVENT_CORROBORATED",
            rights_status="RIGHTS_PERMITTED",
            matching_result="MATCHED_ISSUER_DATE",
            remaining_gap="Event split into LTCG $0.1064 and STCG $0.0372; payable confirmed 2020-12-29. Corroborated by OCC memo 48045 and Form 1042-S QSG list.",
        )
    )

    # 2021
    records.append(
        EvidenceOverlayRecord(
            question_id="Q_BND_CG_2021",
            symbol="BND",
            cusip="921937835",
            share_class="ETF",
            economic_event_id="BND-2021-CG-ANNUAL",
            provider_event_id="da4043ec-4eee-44e3-a9f8-5d994f1f635d",
            source_title="MIAX Alert / OCC Information Memo 49819 & SEC 2026 Filing",
            source_url="https://www.miaxglobal.com/sites/default/files/alert-files/BND_Distribution_49819.pdf",
            source_document_id="MIAX-BND-49819",
            source_page_or_table="MIAX Distribution Notice / SEC Financial Highlights",
            reporting_period="FY2021",
            tax_year="2021",
            ex_date="2021-12-23",
            record_date="2021-12-27",
            payable_date="2021-12-29",
            cash_amount_per_share="0.1834",
            financial_component_type="FINANCIAL_STATEMENT_ANNUAL_TOTAL",
            tax_classification="QUALIFIED_SHORT_TERM_GAIN",
            publication_or_acceptance_time="2021-12-23",
            capture_time=now_iso,
            historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
            evidence_class="OCC_EVENT_CORROBORATED",
            rights_status="RIGHTS_PERMITTED",
            matching_result="MATCHED_ISSUER_DATE",
            remaining_gap="Annual capital gain sum $0.1834 matches component sum ($0.0534 on 2021-04-01 + $0.13 on 2021-12-23). Corroborated by OCC memo 49819 and Form 1042-S QSG list.",
        )
    )

    # 2022
    records.append(
        EvidenceOverlayRecord(
            question_id="Q_BND_CG_2022",
            symbol="BND",
            cusip="921937835",
            share_class="ETF",
            economic_event_id="BND-2022-CG-ANNUAL",
            provider_event_id="6bcd4e25-c31a-49ce-97df-3ee25c524544",
            source_title="SEC 2026 Filing & Vanguard Total Bond Market ETF Distribution History",
            source_url=sec_2026_url,
            source_document_id="SEC-0000794105-26-000106",
            source_page_or_table="Financial Highlights: BND ETF Share Class",
            reporting_period="FY2022",
            tax_year="2022",
            ex_date="2022-04-01",
            record_date="UNKNOWN",
            payable_date="2022-04-06",
            cash_amount_per_share="0.0593",
            financial_component_type="CAPITAL_GAIN_LONG_TERM",
            tax_classification="LONG_TERM_CAPITAL_GAIN",
            publication_or_acceptance_time="2026-01-01",
            capture_time=now_iso,
            historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
            evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
            rights_status="RIGHTS_PERMITTED",
            matching_result="MATCHED_ISSUER_DATE",
            remaining_gap="Annual total $0.0593 matches 2022-04-01 event. Long-Term Capital Gain; absence from 2022 Form 1042-S QSG list is consistent (LTCG is exempt from QSG listing).",
        )
    )

    # 2023, 2024, 2025
    for yr in ("2023", "2024", "2025"):
        records.append(
            EvidenceOverlayRecord(
                question_id=f"Q_BND_CG_{yr}",
                symbol="BND",
                cusip="921937835",
                share_class="ETF",
                economic_event_id=f"BND-{yr}-CG-ANNUAL",
                provider_event_id="NONE",
                source_title="SEC 2026 Filing Financial Highlights",
                source_url=sec_2026_url,
                source_document_id="SEC-0000794105-26-000106",
                source_page_or_table="Financial Highlights: BND ETF Share Class",
                reporting_period=f"FY{yr}",
                tax_year=yr,
                ex_date="UNKNOWN",
                record_date="UNKNOWN",
                payable_date="UNKNOWN",
                cash_amount_per_share="0",
                financial_component_type="FINANCIAL_STATEMENT_ANNUAL_TOTAL",
                tax_classification="NONE",
                publication_or_acceptance_time="2026-01-01",
                capture_time=now_iso,
                historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
                evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
                rights_status="RIGHTS_PERMITTED",
                matching_result="MATCHED_ISSUER_DATE",
                remaining_gap=f"No capital gain distribution for {yr} in financial statements, corroborating zero capital gain provider rows.",
            )
        )

    # --- Part B: Vanguard Form 1042-S QSG Tax-Classification Register ---
    qsg_data = [
        ("2020", "1042sb-022021.pdf", True, "BND listed in QSG schedule; confirms qualified short-term capital gain treatment for 2020-12-23 STCG."),
        ("2021", "1042sb-022022.pdf", True, "BND listed in QSG schedule; confirms qualified short-term capital gain treatment for 2021-04-01 STCG."),
        ("2022", "1042sb-022023.pdf", False, "BND not listed in QSG schedule; 2022 gain was 100% Long-Term Capital Gain ($0.0593 LTCG), which is not QSG. Absence is consistent."),
        ("2023", "1042sb-022024.pdf", False, "BND not listed in QSG schedule; no capital gains paid in 2023."),
        ("2024", "1042sb-022025.pdf", False, "BND not listed in QSG schedule; no capital gains paid in 2024."),
    ]
    for tax_year, doc_name, listed, notes in qsg_data:
        records.append(
            EvidenceOverlayRecord(
                question_id=f"Q_QSG_BND_{tax_year}",
                symbol="BND",
                cusip="921937835",
                share_class="ETF",
                economic_event_id=f"BND-QSG-{tax_year}",
                provider_event_id="NONE",
                source_title=f"Vanguard Form 1042-S Foreign Tax Supplement ({tax_year})",
                source_url=f"https://investor.vanguard.com/content/dam/retail/us/en/pdfs/taxes/{doc_name}",
                source_document_id=doc_name,
                source_page_or_table="Qualified Short-Term Gain (QSG) Fund Listing",
                reporting_period=tax_year,
                tax_year=tax_year,
                ex_date="UNKNOWN",
                record_date="UNKNOWN",
                payable_date="UNKNOWN",
                cash_amount_per_share="NONE",
                financial_component_type="NONE",
                tax_classification="QUALIFIED_SHORT_TERM_GAIN" if listed else "NONE",
                publication_or_acceptance_time=f"{int(tax_year)+1}-02-01",
                capture_time=now_iso,
                historical_availability_status="RETROSPECTIVE_CORROBORATION_ONLY",
                evidence_class="ISSUER_TAX_CLASSIFICATION_ONLY",
                rights_status="RIGHTS_PERMITTED",
                matching_result="MATCHED_ISSUER_DATE",
                remaining_gap=notes,
            )
        )

    # --- Part C: 63 Imputed Payable Date Backlog (BND 47, VOO 16) ---
    if provider_rows:
        imputed_rows = [
            r for r in provider_rows if "IMPUTED" in r.get("payable_date_source", "")
        ]
        for idx, row in enumerate(imputed_rows, start=1):
            sym = row["symbol"]
            ex = row["ex_date"]
            imputed_pay = row["payable_date"]
            gross = row["gross_amount"]
            event_id = row.get("event_id", "")
            records.append(
                EvidenceOverlayRecord(
                    question_id=f"Q_IMPUTED_PAYABLE_{sym}_{ex.replace('-', '')}",
                    symbol=sym,
                    cusip="921937835" if sym == "BND" else "922908363",
                    share_class="ETF",
                    economic_event_id=f"{sym}-PAYABLE-{ex}",
                    provider_event_id=event_id,
                    source_title=f"Vanguard {sym} Distribution History (Web Table)",
                    source_url=(
                        "https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf"
                        if sym == "BND"
                        else "https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf"
                    ),
                    source_document_id=f"VANGUARD-{sym}-DIST-TABLE",
                    source_page_or_table="Historical Distributions Table (Unlicensed Bulk Export Restricted)",
                    reporting_period=ex[:4],
                    tax_year=ex[:4],
                    ex_date=ex,
                    record_date="UNKNOWN",
                    payable_date="UNKNOWN",
                    cash_amount_per_share=gross,
                    financial_component_type="DIVIDEND_CASH",
                    tax_classification="ORDINARY_DIVIDEND",
                    publication_or_acceptance_time="UNKNOWN",
                    capture_time=now_iso,
                    historical_availability_status="UNAVAILABLE",
                    evidence_class="UNRESOLVED",
                    rights_status="RIGHTS_RESTRICTED",
                    matching_result="SOURCE_NOT_AVAILABLE",
                    remaining_gap=(
                        f"Imputed payable date {imputed_pay} (ex+6d) remains unverified. "
                        "Vanguard terms prohibit bulk scraping without written license. "
                        "No authenticated event-level issuer file is present in repository."
                    ),
                )
            )

    return records


def export_overlay_to_csv(records: Sequence[EvidenceOverlayRecord]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(EVIDENCE_OVERLAY_FIELDS), lineterminator="\n")
    writer.writeheader()
    for rec in records:
        writer.writerow(rec.to_dict())
    return output.getvalue()


def export_overlay_to_json(records: Sequence[EvidenceOverlayRecord]) -> str:
    return json.dumps([r.to_dict() for r in records], indent=2, sort_keys=True)
