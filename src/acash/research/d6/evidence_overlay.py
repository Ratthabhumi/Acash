"""V37B Independent Evidence Overlay for corporate actions and distribution reconciliation.

Deterministic, offline, read-only evidence overlay separate from the canonical D6 dataset.
Matching results are computed from provider rows, never taken from evidence labels.
Annual financial totals, event-level components, event cash entitlements and tax-year
designations are separate scopes and are never merged into one record.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError

EVIDENCE_OVERLAY_FIELDS: Tuple[str, ...] = (
    "question_id",
    "symbol",
    "cusip",
    "share_class",
    "economic_event_id",
    "evidence_scope",
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

EVIDENCE_SCOPES: Tuple[str, ...] = (
    "ANNUAL_FINANCIAL_TOTAL",
    "EVENT_CASH_ENTITLEMENT",
    "EVENT_FINANCIAL_COMPONENT",
    "TAX_YEAR_DESIGNATION",
)
EVENT_SCOPES: Tuple[str, ...] = ("EVENT_CASH_ENTITLEMENT", "EVENT_FINANCIAL_COMPONENT")

EVIDENCE_CLASSES: Tuple[str, ...] = (
    "ISSUER_EVENT_MATCHED",
    "ISSUER_ANNUAL_TOTAL_CORROBORATED",
    "ISSUER_TAX_CLASSIFICATION_ONLY",
    "OCC_EVENT_CORROBORATED",
    "SECONDARY_INDICATION_ONLY",
    "CONFLICTING_EVIDENCE",
    "UNRESOLVED",
)
INDEPENDENT_EVENT_CLASSES: Dict[str, str] = {
    "ISSUER_EVENT_MATCHED": "MATCHED_ISSUER_DATE",
    "OCC_EVENT_CORROBORATED": "MATCHED_OCC_EVENT",
}

MATCHING_RESULTS: Tuple[str, ...] = (
    "MATCHED_ISSUER_DATE",
    "MATCHED_OCC_EVENT",
    "ANNUAL_TOTAL_CONSISTENT",
    "ANNUAL_CLASSIFICATION_DIFFERENCE",
    "ANNUAL_TOTAL_INCONSISTENT",
    "CONFLICTING_DATE",
    "CONFLICTING_AMOUNT",
    "CONFLICTING_COMPONENT",
    "AMBIGUOUS_MATCH",
    "SOURCE_NOT_AVAILABLE",
    "LOCAL_DATA_UNAVAILABLE",
    "NOT_APPLICABLE",
    "UNRESOLVED",
)
# Results that only reconcile_provider_distributions() may assign from provider rows.
COMPUTED_RESULTS: Tuple[str, ...] = (
    "MATCHED_ISSUER_DATE",
    "MATCHED_OCC_EVENT",
    "ANNUAL_TOTAL_CONSISTENT",
    "ANNUAL_CLASSIFICATION_DIFFERENCE",
    "ANNUAL_TOTAL_INCONSISTENT",
    "CONFLICTING_DATE",
    "CONFLICTING_AMOUNT",
    "CONFLICTING_COMPONENT",
)
POSITIVE_RESULTS: Tuple[str, ...] = (
    "MATCHED_ISSUER_DATE",
    "MATCHED_OCC_EVENT",
    "ANNUAL_TOTAL_CONSISTENT",
)

# No source has a verified grant for every rights dimension (public access, internal use,
# raw-byte retention, automated retrieval, derived data, public redistribution), so a
# blanket RIGHTS_PERMITTED is not representable.
RIGHTS_STATUSES: Tuple[str, ...] = (
    "RIGHTS_RESTRICTED",
    "RIGHTS_UNVERIFIED",
)

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
    "UNKNOWN",
    "NONE",
)

TAX_CLASSIFICATIONS: Tuple[str, ...] = (
    "QUALIFIED_SHORT_TERM_GAIN",
    "QUALIFIED_INTEREST_INCOME",
    "ORDINARY_DIVIDEND",
    "LONG_TERM_CAPITAL_GAIN",
    "UNKNOWN",
    "NONE",
)

# Annual financial highlights report per-share distributions to three decimals.
ANNUAL_ROUNDING_TOLERANCE = Decimal("0.0005")

_UNKNOWN = ("", "UNKNOWN", "NONE")


def _parse_date(value: str, field_name: str) -> Optional[date]:
    if value in _UNKNOWN:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DataContractError(f"OVERLAY_INVALID_DATE: {field_name} {value!r}.") from exc


def _parse_timestamp(value: str, field_name: str) -> Optional[datetime]:
    if value == "UNKNOWN":
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DataContractError(f"OVERLAY_INVALID_TIMESTAMP: {field_name} {value!r}.") from exc
    if parsed.tzinfo is None:
        raise DataContractError(f"OVERLAY_TIMESTAMP_WITHOUT_ZONE: {field_name} {value!r}.")
    return parsed


def _parse_amount(value: str, field_name: str) -> Optional[Decimal]:
    if value in _UNKNOWN:
        return None
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise DataContractError(f"OVERLAY_INVALID_AMOUNT: {field_name} {value!r}.") from exc
    if not d.is_finite() or d < Decimal(0):
        raise DataContractError(f"OVERLAY_BAD_AMOUNT: {field_name} {value!r}.")
    return d


def _check_enum(value: str, allowed: Tuple[str, ...], code: str) -> None:
    if value not in allowed:
        raise DataContractError(f"{code}: {value!r}.")


@dataclass(frozen=True)
class EvidenceOverlayRecord:
    question_id: str
    symbol: str
    cusip: str
    share_class: str
    economic_event_id: str
    evidence_scope: str
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
        if not self.provider_event_id.strip():
            raise DataContractError("OVERLAY_EMPTY_PROVIDER_EVENT_ID: use NONE explicitly.")
        _check_enum(self.evidence_scope, EVIDENCE_SCOPES, "OVERLAY_UNKNOWN_EVIDENCE_SCOPE")
        _check_enum(self.evidence_class, EVIDENCE_CLASSES, "OVERLAY_UNKNOWN_EVIDENCE_CLASS")
        _check_enum(self.matching_result, MATCHING_RESULTS, "OVERLAY_UNKNOWN_MATCHING_RESULT")
        if self.rights_status == "RIGHTS_PERMITTED":
            raise DataContractError(
                "OVERLAY_RIGHTS_PERMITTED_UNSUPPORTED: no per-dimension rights grant is verified."
            )
        _check_enum(self.rights_status, RIGHTS_STATUSES, "OVERLAY_UNKNOWN_RIGHTS_STATUS")
        _check_enum(
            self.historical_availability_status,
            HISTORICAL_AVAILABILITY_STATUSES,
            "OVERLAY_UNKNOWN_HISTORICAL_AVAILABILITY",
        )
        _check_enum(
            self.financial_component_type,
            FINANCIAL_COMPONENT_TYPES,
            "OVERLAY_UNKNOWN_FINANCIAL_COMPONENT",
        )
        _check_enum(self.tax_classification, TAX_CLASSIFICATIONS, "OVERLAY_UNKNOWN_TAX_CLASSIFICATION")

        ex = _parse_date(self.ex_date, "ex_date")
        _parse_date(self.record_date, "record_date")
        _parse_date(self.payable_date, "payable_date")
        amount = _parse_amount(self.cash_amount_per_share, "cash_amount_per_share")
        published = _parse_timestamp(self.publication_or_acceptance_time, "publication_or_acceptance_time")
        captured = _parse_timestamp(self.capture_time, "capture_time")
        if published is not None and captured is not None and captured < published:
            raise DataContractError(f"OVERLAY_CAPTURE_BEFORE_PUBLICATION: {self.economic_event_id}.")

        if self.tax_classification == "QUALIFIED_SHORT_TERM_GAIN" and self.evidence_scope != "TAX_YEAR_DESIGNATION":
            raise DataContractError(
                f"OVERLAY_QSG_WITHOUT_EVENT_PERCENTAGE: {self.economic_event_id} "
                "carries QSG outside a tax-year designation."
            )
        if self.matching_result in ("MATCHED_ISSUER_DATE", "MATCHED_OCC_EVENT"):
            if self.evidence_scope not in EVENT_SCOPES or ex is None:
                raise DataContractError(f"OVERLAY_MATCH_WITHOUT_EVENT_DATE: {self.economic_event_id}.")
            if INDEPENDENT_EVENT_CLASSES.get(self.evidence_class) != self.matching_result:
                raise DataContractError(
                    f"OVERLAY_MATCH_CLASS_INCONSISTENT: {self.economic_event_id} "
                    f"{self.evidence_class} cannot yield {self.matching_result}."
                )

        if self.evidence_scope in ("ANNUAL_FINANCIAL_TOTAL", "TAX_YEAR_DESIGNATION"):
            if (self.ex_date, self.record_date, self.payable_date) != ("UNKNOWN",) * 3:
                raise DataContractError(f"OVERLAY_ANNUAL_TOTAL_AS_EVENT: {self.economic_event_id} has event dates.")
            if self.provider_event_id != "NONE":
                raise DataContractError(
                    f"OVERLAY_ANNUAL_TOTAL_AS_EVENT: {self.economic_event_id} references a provider event."
                )
            if not (len(self.tax_year) == 4 and self.tax_year.isdigit()):
                raise DataContractError(f"OVERLAY_BAD_TAX_YEAR: {self.tax_year!r}.")
            if published is not None and published.date() <= date(int(self.tax_year), 12, 31):
                raise DataContractError(
                    f"OVERLAY_PUBLICATION_BEFORE_PERIOD_END: {self.economic_event_id} published "
                    f"{self.publication_or_acceptance_time} before period {self.tax_year} ended."
                )

        if self.evidence_scope == "ANNUAL_FINANCIAL_TOTAL":
            if self.financial_component_type != "FINANCIAL_STATEMENT_ANNUAL_TOTAL":
                raise DataContractError(f"OVERLAY_ANNUAL_COMPONENT_MISMATCH: {self.economic_event_id}.")
            if self.tax_classification not in ("UNKNOWN", "NONE"):
                raise DataContractError(
                    f"OVERLAY_ANNUAL_TAX_CLASSIFICATION: {self.economic_event_id} annual totals carry no tax designation."
                )
            if self.reporting_period != f"FY{self.tax_year}":
                raise DataContractError(f"OVERLAY_REPORTING_PERIOD_MISMATCH: {self.economic_event_id}.")
        elif self.evidence_scope == "TAX_YEAR_DESIGNATION":
            if self.cash_amount_per_share != "NONE" or self.financial_component_type != "NONE":
                raise DataContractError(f"OVERLAY_TAX_DESIGNATION_WITH_CASH: {self.economic_event_id}.")
            if self.matching_result != "NOT_APPLICABLE":
                raise DataContractError(f"OVERLAY_TAX_DESIGNATION_MATCHED: {self.economic_event_id}.")
        else:
            if self.financial_component_type in ("FINANCIAL_STATEMENT_ANNUAL_TOTAL", "NONE"):
                raise DataContractError(f"OVERLAY_ANNUAL_TOTAL_AS_EVENT: {self.economic_event_id}.")
            if amount is None:
                raise DataContractError(f"OVERLAY_EVENT_WITHOUT_AMOUNT: {self.economic_event_id}.")
            if self.evidence_class in INDEPENDENT_EVENT_CLASSES and ex is None:
                raise DataContractError(f"OVERLAY_EVENT_DATE_UNKNOWN: {self.economic_event_id}.")

    def to_dict(self) -> Dict[str, str]:
        return {k: getattr(self, k) for k in EVIDENCE_OVERLAY_FIELDS}


def validate_overlay_records(records: Sequence[EvidenceOverlayRecord]) -> None:
    seen_ids: set[str] = set()
    identities: set[Tuple[str, ...]] = set()
    cusip_of: Dict[str, str] = {}
    symbol_of: Dict[str, str] = {}
    for rec in records:
        if rec.economic_event_id in seen_ids:
            raise DataContractError(f"OVERLAY_DUPLICATE_ECONOMIC_EVENT_ID: {rec.economic_event_id}.")
        seen_ids.add(rec.economic_event_id)
        if rec.evidence_scope in EVENT_SCOPES and rec.provider_event_id != "NONE":
            identity: Tuple[str, ...] = (rec.evidence_scope, rec.provider_event_id, rec.financial_component_type)
        elif rec.evidence_scope in EVENT_SCOPES:
            identity = (rec.evidence_scope, rec.symbol, rec.ex_date, rec.financial_component_type, rec.cash_amount_per_share)
        else:
            identity = (rec.evidence_scope, rec.symbol, rec.tax_year)
        if identity in identities:
            raise DataContractError(f"OVERLAY_DUPLICATE_ECONOMIC_EVENT: {rec.economic_event_id} {identity}.")
        identities.add(identity)
        if cusip_of.setdefault(rec.symbol, rec.cusip) != rec.cusip or symbol_of.setdefault(rec.cusip, rec.symbol) != rec.symbol:
            raise DataContractError(f"OVERLAY_CUSIP_SYMBOL_CONFLICT: {rec.symbol} {rec.cusip}.")


def canonical_overlay_order(records: Sequence[EvidenceOverlayRecord]) -> List[EvidenceOverlayRecord]:
    """The single canonical order (by unique economic_event_id) for every export and digest."""
    validate_overlay_records(records)
    return sorted(records, key=lambda r: r.economic_event_id)


def export_overlay_to_csv(records: Sequence[EvidenceOverlayRecord]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(EVIDENCE_OVERLAY_FIELDS), lineterminator="\n")
    writer.writeheader()
    for rec in canonical_overlay_order(records):
        writer.writerow(rec.to_dict())
    return output.getvalue()


def export_overlay_to_json(records: Sequence[EvidenceOverlayRecord]) -> str:
    return json.dumps([r.to_dict() for r in canonical_overlay_order(records)], indent=2, sort_keys=True) + "\n"


def overlay_digest(records: Sequence[EvidenceOverlayRecord]) -> str:
    """SHA-256 of the canonical JSON export bytes."""
    return hashlib.sha256(export_overlay_to_json(records).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceReconciliationResult:
    records: Tuple[EvidenceOverlayRecord, ...]
    local_data_status: str
    real_event_matches: int
    event_conflicts: int
    event_unresolved: int
    annual_consistent: int
    annual_classification_differences: int
    annual_inconsistent: int
    annual_unsourced: int
    tax_designations: int
    imputed_payable_start: int
    bnd_imputed_start: int
    voo_imputed_start: int
    payable_matched: int
    payable_unresolved: int
    digest: str


def _index_provider_rows(provider_rows: Sequence[Mapping[str, str]]) -> Dict[str, Mapping[str, str]]:
    index: Dict[str, Mapping[str, str]] = {}
    for row in provider_rows:
        event_id = row.get("event_id", "")
        if not event_id:
            raise DataContractError("OVERLAY_PROVIDER_ROW_WITHOUT_EVENT_ID.")
        if event_id in index:
            raise DataContractError(f"OVERLAY_DUPLICATE_PROVIDER_EVENT_ID: {event_id}.")
        index[event_id] = row
    return index


def _match_event(rec: EvidenceOverlayRecord, row: Mapping[str, str]) -> str:
    if row["symbol"] != rec.symbol:
        raise DataContractError(f"OVERLAY_PROVIDER_IDENTITY_MISMATCH: {rec.economic_event_id} symbol.")
    for key in ("cusip", "share_class"):
        if row.get(key) and row[key] != getattr(rec, key):
            raise DataContractError(f"OVERLAY_PROVIDER_IDENTITY_MISMATCH: {rec.economic_event_id} {key}.")
    if row["ex_date"] != rec.ex_date:
        return "CONFLICTING_DATE"
    if rec.payable_date not in _UNKNOWN and row.get("payable_date") != rec.payable_date:
        return "CONFLICTING_DATE"
    if row.get("distribution_type") != rec.financial_component_type:
        return "CONFLICTING_COMPONENT"
    if Decimal(row["gross_amount"]) != Decimal(rec.cash_amount_per_share):
        return "CONFLICTING_AMOUNT"
    return INDEPENDENT_EVENT_CLASSES[rec.evidence_class]


def _annual_result(
    rec: EvidenceOverlayRecord,
    provider_rows: Sequence[Mapping[str, str]],
    candidate_ids: Sequence[str],
) -> str:
    """Compare a reported annual total with provider capital-gain rows.

    ANNUAL_CLASSIFICATION_DIFFERENCE: the total is explained only after adding provider rows that
    the overlay lists as unresolved candidates (provider labels them otherwise); no cash differs.
    """
    reported = Decimal(rec.cash_amount_per_share)
    in_year = [r for r in provider_rows if r["symbol"] == rec.symbol and r["ex_date"][:4] == rec.tax_year]
    provider_cg = sum(
        (Decimal(r["gross_amount"]) for r in in_year if r.get("distribution_type", "").startswith("CAPITAL_GAIN")),
        Decimal(0),
    )
    if abs(reported - provider_cg) <= ANNUAL_ROUNDING_TOLERANCE:
        return "ANNUAL_TOTAL_CONSISTENT"
    candidates = [r for r in in_year if r["event_id"] in candidate_ids]
    if candidates and abs(reported - provider_cg - sum((Decimal(r["gross_amount"]) for r in candidates), Decimal(0))) <= ANNUAL_ROUNDING_TOLERANCE:
        return "ANNUAL_CLASSIFICATION_DIFFERENCE"
    return "ANNUAL_TOTAL_INCONSISTENT"


def _computed_result(
    rec: EvidenceOverlayRecord,
    provider_rows: Optional[Sequence[Mapping[str, str]]],
    index: Dict[str, Mapping[str, str]],
    candidate_ids: Sequence[str],
) -> Optional[str]:
    """Data-derived result, or None when the record carries no checkable claim."""
    if rec.evidence_scope == "ANNUAL_FINANCIAL_TOTAL" and rec.cash_amount_per_share not in _UNKNOWN:
        if provider_rows is None:
            return "LOCAL_DATA_UNAVAILABLE"
        return _annual_result(rec, provider_rows, candidate_ids)
    if rec.evidence_scope in EVENT_SCOPES and rec.evidence_class in INDEPENDENT_EVENT_CLASSES:
        if rec.provider_event_id == "NONE":
            return "UNRESOLVED"
        if provider_rows is None:
            return "LOCAL_DATA_UNAVAILABLE"
        return _match_event(rec, index[rec.provider_event_id])
    return None


def reconcile_provider_distributions(
    provider_rows: Optional[Sequence[Mapping[str, str]]],
    overlay_records: Sequence[EvidenceOverlayRecord],
) -> EvidenceReconciliationResult:
    """Read-only comparison of provider rows against the evidence overlay.

    ``provider_rows=None`` means the local dataset is unavailable: no empirical match is
    asserted and every data-dependent result becomes LOCAL_DATA_UNAVAILABLE.
    """
    validate_overlay_records(overlay_records)
    rows: Sequence[Mapping[str, str]] = provider_rows if provider_rows is not None else ()
    index = _index_provider_rows(rows)
    if provider_rows is not None:
        for rec in overlay_records:
            if rec.provider_event_id != "NONE" and rec.provider_event_id not in index:
                raise DataContractError(
                    f"OVERLAY_UNKNOWN_PROVIDER_EVENT_ID: {rec.economic_event_id} -> {rec.provider_event_id}."
                )

    candidate_ids = [
        r.provider_event_id
        for r in overlay_records
        if r.evidence_scope == "EVENT_FINANCIAL_COMPONENT"
        and r.financial_component_type == "UNKNOWN"
        and r.provider_event_id != "NONE"
    ]
    resolved: List[EvidenceOverlayRecord] = []
    for rec in overlay_records:
        computed = _computed_result(rec, provider_rows, index, candidate_ids)
        if computed is None:
            if rec.matching_result in COMPUTED_RESULTS:
                raise DataContractError(
                    f"OVERLAY_CLAIMED_MATCH_UNSUPPORTED: {rec.economic_event_id} declares "
                    f"{rec.matching_result} without checkable event-level evidence."
                )
            resolved.append(rec)
            continue
        if rec.matching_result in POSITIVE_RESULTS and rec.matching_result != computed:
            raise DataContractError(
                f"OVERLAY_CLAIMED_MATCH_UNSUPPORTED: {rec.economic_event_id} declares "
                f"{rec.matching_result}; provider rows give {computed}."
            )
        resolved.append(replace(rec, matching_result=computed))

    events = [r for r in resolved if r.evidence_scope == "EVENT_FINANCIAL_COMPONENT"]
    annual = [r for r in resolved if r.evidence_scope == "ANNUAL_FINANCIAL_TOTAL"]
    payable = [r for r in resolved if r.question_id.startswith("Q_IMPUTED_PAYABLE_")]
    imputed = [r for r in rows if "IMPUTED" in r.get("payable_date_source", "")]
    ordered = canonical_overlay_order(resolved)
    return EvidenceReconciliationResult(
        records=tuple(ordered),
        local_data_status="LOCAL_DATA_UNAVAILABLE" if provider_rows is None else "LOCAL_DATA_CHECKED",
        real_event_matches=sum(r.matching_result in ("MATCHED_ISSUER_DATE", "MATCHED_OCC_EVENT") for r in events),
        event_conflicts=sum(r.matching_result.startswith("CONFLICTING_") for r in events),
        event_unresolved=sum(
            r.matching_result in ("UNRESOLVED", "SOURCE_NOT_AVAILABLE", "AMBIGUOUS_MATCH", "LOCAL_DATA_UNAVAILABLE")
            for r in events
        ),
        annual_consistent=sum(r.matching_result == "ANNUAL_TOTAL_CONSISTENT" for r in annual),
        annual_classification_differences=sum(
            r.matching_result == "ANNUAL_CLASSIFICATION_DIFFERENCE" for r in annual
        ),
        annual_inconsistent=sum(r.matching_result == "ANNUAL_TOTAL_INCONSISTENT" for r in annual),
        annual_unsourced=sum(r.matching_result == "SOURCE_NOT_AVAILABLE" for r in annual),
        tax_designations=sum(r.evidence_scope == "TAX_YEAR_DESIGNATION" for r in resolved),
        imputed_payable_start=len(imputed),
        bnd_imputed_start=sum(r["symbol"] == "BND" for r in imputed),
        voo_imputed_start=sum(r["symbol"] == "VOO" for r in imputed),
        payable_matched=sum(r.matching_result in POSITIVE_RESULTS for r in payable),
        payable_unresolved=sum(r.matching_result not in POSITIVE_RESULTS for r in payable),
        digest=overlay_digest(ordered),
    )


_BND_CUSIP = "921937835"
_CUSIPS = {"BND": _BND_CUSIP, "VOO": "922908363"}
_VANGUARD_PAGES = {
    "BND": "https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf",
    "VOO": "https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf",
}
_SEC_2019 = (
    "https://www.sec.gov/Archives/edgar/data/794105/000093247119006953/bondindex485bfinal.htm",
    "SEC-0000932471-19-006953",
    "2019-04-25T17:35:43-04:00",
)
_SEC_2021 = (
    "https://www.sec.gov/Archives/edgar/data/794105/000168386321002757/bondindex-20210429.htm",
    "SEC-0001683863-21-002757",
    "2021-04-28T17:37:00-04:00",
)
_SEC_2026 = (
    "https://www.sec.gov/Archives/edgar/data/794105/000079410526000106/f45031d1.htm",
    "SEC-0000794105-26-000106",
    "2026-04-27T17:36:08-04:00",
)
_OCC_48045 = ("https://infomemo.theocc.com/infomemos?number=48045", "OCC-48045")
_MIAX_49819 = (
    "https://www.miaxglobal.com/sites/default/files/alert-files/BND_Distribution_49819.pdf",
    "MIAX-OCC-49819",
)
_DIVIDEND_COM = ("https://www.dividend.com/etfs/bnd-vanguard-total-bond-market-etf/", "DIVIDEND-COM-BND")
_TRANSCRIBED = (
    "ETF Shares column, 'Distributions from Realized Capital Gains', read from the filing on 2026-10-30 "
    "(3 dp; '—' recorded as 0). Annual total does not establish event dates or ST/LT tax designation."
)


def _bnd(**fields: str) -> EvidenceOverlayRecord:
    base = {
        "symbol": "BND",
        "cusip": _BND_CUSIP,
        "share_class": "ETF",
        "record_date": "UNKNOWN",
        "payable_date": "UNKNOWN",
        "tax_classification": "UNKNOWN",
        "publication_or_acceptance_time": "UNKNOWN",
        "capture_time": "UNKNOWN",
        "historical_availability_status": "RETROSPECTIVE_CORROBORATION_ONLY",
        "rights_status": "RIGHTS_UNVERIFIED",
        "matching_result": "UNRESOLVED",
    }
    base.update(fields)
    return EvidenceOverlayRecord(**base)


def _annual(year: str, amount: str, sec: Tuple[str, str, str], gap: str) -> EvidenceOverlayRecord:
    return _bnd(
        question_id=f"Q_BND_CG_{year}",
        economic_event_id=f"BND-FY{year}-CG-ANNUAL",
        evidence_scope="ANNUAL_FINANCIAL_TOTAL",
        provider_event_id="NONE",
        source_title="Vanguard Bond Index Funds Form 485BPOS Financial Highlights",
        source_url=sec[0],
        source_document_id=sec[1],
        source_page_or_table="Financial Highlights: Total Bond Market Index Fund ETF Shares",
        reporting_period=f"FY{year}",
        tax_year=year,
        ex_date="UNKNOWN",
        cash_amount_per_share=amount,
        financial_component_type="FINANCIAL_STATEMENT_ANNUAL_TOTAL",
        publication_or_acceptance_time=sec[2],
        evidence_class="ISSUER_ANNUAL_TOTAL_CORROBORATED",
        remaining_gap=f"{_TRANSCRIBED} {gap}",
    )


def _event(
    suffix: str,
    ex: str,
    provider_event_id: str,
    amount: str,
    component: str,
    evidence_class: str,
    source: Tuple[str, str],
    title: str,
    payable: str,
    gap: str,
    record: str = "UNKNOWN",
) -> EvidenceOverlayRecord:
    return _bnd(
        question_id=f"Q_BND_EVENT_{ex.replace('-', '')}_{suffix}",
        economic_event_id=f"BND-{ex}-{suffix}",
        evidence_scope="EVENT_FINANCIAL_COMPONENT",
        provider_event_id=provider_event_id,
        source_title=title,
        source_url=source[0],
        source_document_id=source[1],
        source_page_or_table="Event distribution notice" if source[0] != "NONE" else "NONE",
        reporting_period=ex,
        tax_year=ex[:4],
        ex_date=ex,
        record_date=record,
        payable_date=payable,
        cash_amount_per_share=amount,
        financial_component_type=component,
        evidence_class=evidence_class,
        remaining_gap=gap,
    )


def build_v37b_evidence_overlay(
    provider_rows: Optional[Sequence[Mapping[str, str]]] = None,
) -> List[EvidenceOverlayRecord]:
    """Construct the V37B evidence claims; matching results come from reconcile_provider_distributions()."""
    no_annual = "Provider labels the candidate row DIVIDEND_CASH; no CAPITAL_GAIN row exists for this year."
    records: List[EvidenceOverlayRecord] = [
        _annual("2016", "0.036", _SEC_2019, no_annual),
        _annual("2017", "0.037", _SEC_2019, no_annual),
        _annual("2018", "0.019", _SEC_2019, no_annual),
        _annual("2019", "0", _SEC_2021, "No capital-gain distribution reported ('—')."),
        _annual(
            "2020",
            "0.143",
            _SEC_2021,
            "OCC 48045 components sum to 0.1436 (0.0006 above the display). FY2016 (0.0357 -> .036) shows "
            "rounding, while FY2020 total distributions 2.097 vs provider 2.0978 also look truncated; the "
            "presentation/basis difference is unresolved. No cash ledger change.",
        ),
        _annual("2021", "0.183", _SEC_2026, "Provider capital-gain rows: 2021-04-01 0.0534 (0.0034 ST + 0.05 LT) and 2021-12-23 0.13 LT."),
        _annual("2022", "0.059", _SEC_2026, "Provider capital-gain row: 2022-04-01 0.0593 LT."),
    ]
    for yr in ("2023", "2024", "2025"):
        records.append(_annual(yr, "0", _SEC_2026, "No capital-gain distribution reported."))

    none_src = ("NONE", "NONE")
    candidate_gap = (
        "Amount lies within 3-dp rounding of the FY{yr} annual realized-gain distribution, but no event-level "
        "source establishes its component type or tax character. No additional cash entitlement established."
    )
    for ex, pid, amt in (
        ("2016-12-22", "6fa27f80-92c5-4cb5-93c9-bf5c6c8a7982", "0.0357"),
        ("2017-12-26", "2071302f-3e51-44ff-979d-d6fd4b62396c", "0.037"),
        ("2018-04-02", "7b6168d6-9a2e-4ea5-8cc7-e2502f4293b0", "0.01916"),
    ):
        records.append(
            _event("CANDIDATE", ex, pid, amt, "UNKNOWN", "UNRESOLVED", none_src,
                   "No independent event-level source", "UNKNOWN", candidate_gap.format(yr=ex[:4]))
        )

    occ_note = (
        "OCC memo 48045 dated 2020-12-22 (read 2026-10-30; OCC calls it an unofficial summary): LT 0.1064 + "
        "ST 0.0372, record 2020-12-24, payable 2020-12-29, CUSIP 921937835. Time of availability to an "
        "automated strategy UNKNOWN."
    )
    occ_gap_st = (
        f"{occ_note} TY2020 1042-S states 100% of the fund's 2020 short-term capital-gain distributions are QSG; "
        "the tax statement's ST character for this component is not held, so tax character stays UNKNOWN."
    )
    occ_gap_lt = f"{occ_note} Tax designation not established."
    secondary_gap = "Secondary indication only; not independently verified at event level."
    records += [
        _event("ST", "2020-12-23", "eb13dcb4-6894-4184-a1db-29746b8d9435#short_term", "0.0372",
               "CAPITAL_GAIN_SHORT_TERM", "OCC_EVENT_CORROBORATED", _OCC_48045,
               "OCC Information Memo 48045", "2020-12-29", occ_gap_st, record="2020-12-24"),
        _event("LT", "2020-12-23", "eb13dcb4-6894-4184-a1db-29746b8d9435#long_term", "0.1064",
               "CAPITAL_GAIN_LONG_TERM", "OCC_EVENT_CORROBORATED", _OCC_48045,
               "OCC Information Memo 48045", "2020-12-29", occ_gap_lt, record="2020-12-24"),
        _event("ST", "2021-04-01", "09df29e0-38dc-4cfe-9d2f-a5ef791cdd1a#short_term", "0.0034",
               "CAPITAL_GAIN_SHORT_TERM", "SECONDARY_INDICATION_ONLY", _DIVIDEND_COM,
               "Dividend.com BND distribution history", "UNKNOWN", secondary_gap),
        _event("LT", "2021-04-01", "09df29e0-38dc-4cfe-9d2f-a5ef791cdd1a#long_term", "0.05",
               "CAPITAL_GAIN_LONG_TERM", "SECONDARY_INDICATION_ONLY", _DIVIDEND_COM,
               "Dividend.com BND distribution history", "UNKNOWN", secondary_gap),
        _event("LT", "2021-12-23", "da4043ec-4eee-44e3-a9f8-5d994f1f635d", "0.13",
               "CAPITAL_GAIN_LONG_TERM", "OCC_EVENT_CORROBORATED", _MIAX_49819,
               "MIAX alert relaying OCC Information Memo 49819", "2021-12-29",
               "MIAX/OCC 49819 dated 2021-12-22 (read 2026-10-30): LT 0.13, record 2021-12-27, payable "
               "2021-12-29, CUSIP 921937835. Not Vanguard issuer data; availability time UNKNOWN. "
               "Tax designation not established.", record="2021-12-27"),
        _event("LT", "2022-04-01", "6bcd4e25-c31a-49ce-97df-3ee25c524544", "0.0593",
               "CAPITAL_GAIN_LONG_TERM", "SECONDARY_INDICATION_ONLY", _DIVIDEND_COM,
               "Dividend.com BND distribution history", "UNKNOWN", secondary_gap),
    ]

    for tax_year, doc_name, listed in (
        ("2020", "1042sb-022021.pdf", True),
        ("2021", "1042sb-022022.pdf", True),
        ("2022", "1042sb-022023.pdf", False),
        ("2023", "1042sb-022024.pdf", False),
        ("2024", "1042sb-022025.pdf", False),
    ):
        records.append(
            _bnd(
                question_id=f"Q_QSG_BND_{tax_year}",
                economic_event_id=f"BND-QSG-TY{tax_year}",
                evidence_scope="TAX_YEAR_DESIGNATION",
                provider_event_id="NONE",
                source_title=f"Vanguard Form 1042-S supplement (tax year {tax_year})",
                source_url=f"https://investor.vanguard.com/content/dam/retail/us/en/pdfs/taxes/{doc_name}",
                source_document_id=doc_name,
                source_page_or_table="Qualified short-term gain fund listing",
                reporting_period=tax_year,
                tax_year=tax_year,
                ex_date="UNKNOWN",
                cash_amount_per_share="NONE",
                financial_component_type="NONE",
                tax_classification="QUALIFIED_SHORT_TERM_GAIN" if listed else "NONE",
                evidence_class="ISSUER_TAX_CLASSIFICATION_ONLY",
                matching_result="NOT_APPLICABLE",
                remaining_gap=(
                    f"Read 2026-10-30: Vanguard Total Bond Market Index Fund listed; the supplement states 100% of "
                    f"listed funds' {tax_year} short-term capital-gain distributions are QSG and refers to year-end "
                    "statements for amounts. Applies to ST components only; not to LT or annual totals. "
                    "Publication time UNKNOWN (PDF metadata is not publication evidence)."
                    if listed
                    else f"Read 2026-10-30: fund not found in the text-extracted {tax_year} listing; absence does "
                    "not prove zero capital gains or any component's character. Publication time UNKNOWN."
                ),
            )
        )

    for row in provider_rows or ():
        if "IMPUTED" not in row.get("payable_date_source", ""):
            continue
        sym, ex = row["symbol"], row["ex_date"]
        if sym not in _CUSIPS:
            raise DataContractError(f"OVERLAY_UNKNOWN_CUSIP_FOR_SYMBOL: {sym}.")
        records.append(
            EvidenceOverlayRecord(
                question_id=f"Q_IMPUTED_PAYABLE_{sym}_{ex.replace('-', '')}",
                symbol=sym,
                cusip=_CUSIPS[sym],
                share_class="ETF",
                economic_event_id=f"{sym}-PAYABLE-{ex}",
                evidence_scope="EVENT_CASH_ENTITLEMENT",
                provider_event_id=row["event_id"],
                source_title=f"Vanguard {sym} distribution history (web table)",
                source_url=_VANGUARD_PAGES[sym],
                source_document_id=f"VANGUARD-{sym}-DIST-TABLE",
                source_page_or_table="Historical distributions table",
                reporting_period=ex,
                tax_year=ex[:4],
                ex_date=ex,
                record_date="UNKNOWN",
                payable_date="UNKNOWN",
                cash_amount_per_share=row["gross_amount"],
                financial_component_type=row["distribution_type"],
                tax_classification="UNKNOWN",
                publication_or_acceptance_time="UNKNOWN",
                capture_time="UNKNOWN",
                historical_availability_status="UNAVAILABLE",
                evidence_class="UNRESOLVED",
                rights_status="RIGHTS_RESTRICTED",
                matching_result="SOURCE_NOT_AVAILABLE",
                remaining_gap=(
                    f"Imputed payable date {row['payable_date']} (ex+6d) remains unverified; "
                    "no lawful event-level issuer file is held."
                ),
            )
        )
    return records
