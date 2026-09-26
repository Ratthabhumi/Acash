"""HYP_010 sponsor distribution-authority qualification (no price data).

Explicit per-symbol coverage model. Cadence assumptions (SPY/VEU/BIL quarterly,
AGG monthly) are documented and tested; a scope period without an authoritative
record is a coverage gap, never an implied zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError

REQUIRED_START: date = date(2016, 1, 1)
REQUIRED_END: date = date(2024, 12, 31)

SYMBOL_SPONSOR: Dict[str, str] = {
    "SPY": "STATE_STREET_SPDR_OFFICIAL",
    "BIL": "STATE_STREET_SPDR_OFFICIAL",
    "VEU": "VANGUARD_OFFICIAL",
    "AGG": "BLACKROCK_ISHARES_OFFICIAL",
    "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
}

QUARTERLY_SYMBOLS = frozenset({"SPY", "VEU"})
# BIL/AGG official schedule evidence: monthly distributions Feb-Dec plus a
# December extra; January systematically absent across the FULL authority
# history (BIL 2007-2026 workbook; AGG 2003-2026 page dataset) — schedule,
# not a scope-edge gap. A January ex-date anywhere in history contradicts it.
FEB_DEC_NO_JANUARY_SYMBOLS = frozenset({"AGG", "BIL"})
# ACWI official schedule: semi-annual distributions (June + December per the
# sponsor's stated distribution frequency). Each calendar half in scope must
# contain >= 1 ex-date; irregular/special distributions are accepted as extra
# records, never as substitutes for a missing half.
SEMIANNUAL_SYMBOLS = frozenset({"ACWI"})


@dataclass(frozen=True)
class SponsorDistributionRecord:
    symbol: str
    ex_date: date
    cash_amount: Decimal
    payable_date: date
    record_date: Optional[date] = None
    distribution_type: Optional[str] = None
    source_identity: str = ""
    affirmed_zero: bool = False


@dataclass
class SponsorDistributionAuthorityQualification:
    symbol: str
    official_sponsor: str
    required_start: date = REQUIRED_START
    required_end: date = REQUIRED_END
    authority_start: Optional[date] = None
    authority_end: Optional[date] = None
    records_count: int = 0
    all_ex_dates_valid: bool = False
    all_amounts_valid: bool = False
    all_payable_dates_valid: bool = False
    duplicate_ex_dates: Tuple[str, ...] = ()
    contradictory_records: Tuple[str, ...] = ()
    coverage_complete: bool = False
    coverage_gaps: Tuple[str, ...] = ()
    source_artifact_hashes: Tuple[str, ...] = ()
    classification: str = "NOT_QUALIFIED"


def _quarters_in_scope(start: date, end: date) -> List[str]:
    periods: List[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        periods.append(f"{year}-Q{(month - 1) // 3 + 1}")
        month += 3
        if month > 12:
            month = 1
            year += 1
    return periods


def _months_in_scope(start: date, end: date) -> List[str]:
    periods: List[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        periods.append(f"{year}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return periods


def _halves_in_scope(start: date, end: date) -> List[str]:
    periods: List[str] = []
    year, half = start.year, (start.month - 1) // 6 + 1
    end_key = (end.year, (end.month - 1) // 6 + 1)
    while (year, half) <= end_key:
        periods.append(f"{year}-H{half}")
        half += 1
        if half > 2:
            half = 1
            year += 1
    return periods


def parse_sponsor_records(
    symbol: str,
    raw_records: Sequence[Mapping[str, Any]],
    source_identity: str,
    official_sponsor: str,
) -> List[SponsorDistributionRecord]:
    """Parse + validate official sponsor records (fail closed, no inference)."""
    if symbol not in SYMBOL_SPONSOR:
        raise DataContractError(f"SPONSOR_SYMBOL_NOT_AUTHORIZED: {symbol}.")
    if official_sponsor != SYMBOL_SPONSOR[symbol]:
        raise DataContractError(
            f"SPONSOR_MISMATCH: {symbol} requires {SYMBOL_SPONSOR[symbol]}, got {official_sponsor}."
        )
    if "UNOFFICIAL" in source_identity.upper() or "YAHOO" in source_identity.upper():
        raise DataContractError(f"UNOFFICIAL_SOURCE_REJECTED: {source_identity}.")
    records: List[SponsorDistributionRecord] = []
    for raw in raw_records:
        try:
            ex = date.fromisoformat(str(raw["ex_date"]))
            amount = Decimal(str(raw["cash_distribution"]))
            payable = date.fromisoformat(str(raw["payable_date"]))
        except (KeyError, ValueError, InvalidOperation, TypeError) as exc:
            raise DataContractError(f"SPONSOR_MALFORMED_RECORD {symbol}: {exc}.") from exc
        if amount < Decimal("0"):
            raise DataContractError(f"SPONSOR_NEGATIVE_AMOUNT {symbol} {ex}.")
        # An explicitly affirmed zero (full ex/record/payable lineage present)
        # is valid authority for D=0 — economically consistent with near-zero
        # rate regimes — and is flagged rather than conflated with missing data.
        affirmed_zero = amount == Decimal("0")
        record_date = None
        if raw.get("record_date"):
            try:
                record_date = date.fromisoformat(str(raw["record_date"]))
            except ValueError as exc:
                raise DataContractError(f"SPONSOR_MALFORMED_RECORD_DATE {symbol}: {exc}.") from exc
        records.append(
            SponsorDistributionRecord(
                symbol=symbol,
                ex_date=ex,
                cash_amount=amount,
                payable_date=payable,
                record_date=record_date,
                distribution_type=str(raw["distribution_type"]) if raw.get("distribution_type") else None,
                source_identity=source_identity,
                affirmed_zero=affirmed_zero,
            )
        )
    return records


def qualify_sponsor_authority(
    symbol: str,
    official_sponsor: str,
    records: Sequence[SponsorDistributionRecord],
    source_artifact_hashes: Sequence[str] = (),
) -> SponsorDistributionAuthorityQualification:
    """Explicit coverage qualification over 2016-01-01..2024-12-31."""
    qual = SponsorDistributionAuthorityQualification(
        symbol=symbol, official_sponsor=official_sponsor
    )
    if symbol not in SYMBOL_SPONSOR or official_sponsor != SYMBOL_SPONSOR[symbol]:
        qual.classification = f"BLOCKED_{symbol}_DIVIDEND_AUTHORITY_SPONSOR_MISMATCH"
        return qual
    in_scope = [r for r in records if REQUIRED_START <= r.ex_date <= REQUIRED_END]
    if not in_scope:
        qual.classification = f"BLOCKED_{symbol}_DIVIDEND_AUTHORITY_NO_RECORDS"
        return qual
    qual.records_count = len(in_scope)
    qual.authority_start = min(r.ex_date for r in in_scope)
    qual.authority_end = max(r.ex_date for r in in_scope)
    qual.all_ex_dates_valid = True
    qual.all_amounts_valid = all(r.cash_amount >= Decimal("0") for r in in_scope)
    qual.all_payable_dates_valid = True  # payable is a required parsed date
    seen: Dict[date, Decimal] = {}
    dups: List[str] = []
    contra: List[str] = []
    for record in in_scope:
        if record.ex_date in seen:
            dups.append(record.ex_date.isoformat())
            if seen[record.ex_date] != record.cash_amount:
                contra.append(record.ex_date.isoformat())
        seen[record.ex_date] = record.cash_amount
    qual.duplicate_ex_dates = tuple(sorted(set(dups)))
    qual.contradictory_records = tuple(sorted(set(contra)))
    if symbol in QUARTERLY_SYMBOLS:
        expected_periods = _quarters_in_scope(REQUIRED_START, REQUIRED_END)
        covered = {f"{r.ex_date.year}-Q{(r.ex_date.month - 1) // 3 + 1}" for r in in_scope}
    elif symbol in SEMIANNUAL_SYMBOLS:
        expected_periods = _halves_in_scope(REQUIRED_START, REQUIRED_END)
        covered = {f"{r.ex_date.year}-H{(r.ex_date.month - 1) // 6 + 1}" for r in in_scope}
    elif symbol in FEB_DEC_NO_JANUARY_SYMBOLS:
        expected_periods = [
            p for p in _months_in_scope(REQUIRED_START, REQUIRED_END)
            if not p.endswith("-01")
        ]
        covered = {f"{r.ex_date.year}-{r.ex_date.month:02d}" for r in in_scope}
        january_anywhere = sorted({r.ex_date.isoformat() for r in records if r.ex_date.month == 1})
        if january_anywhere:
            qual.coverage_gaps = tuple(["JANUARY_EX_DATE_CONTRADICTS_FEB_DEC_SCHEDULE"])
            qual.source_artifact_hashes = tuple(source_artifact_hashes)
            qual.classification = f"BLOCKED_{symbol}_DIVIDEND_AUTHORITY_SCHEDULE_CONTRADICTION"
            return qual
    else:
        qual.classification = f"BLOCKED_{symbol}_DIVIDEND_AUTHORITY_UNKNOWN_CADENCE"
        return qual
    gaps = tuple(p for p in expected_periods if p not in covered)
    qual.coverage_gaps = gaps
    qual.source_artifact_hashes = tuple(source_artifact_hashes)
    if contra:
        qual.classification = f"BLOCKED_{symbol}_DIVIDEND_AUTHORITY_CONTRADICTORY_RECORDS"
    elif gaps:
        qual.classification = f"BLOCKED_{symbol}_DIVIDEND_AUTHORITY_COVERAGE_GAP"
    else:
        qual.coverage_complete = True
        qual.classification = f"{symbol}_DIVIDEND_AUTHORITY_QUALIFIED"
    return qual
