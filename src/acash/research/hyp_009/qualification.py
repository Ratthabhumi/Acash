"""HYP_009 dataset qualification: bar/dividend/split checks (fail closed)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Mapping, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.daily_models import DailyBar
from acash.data.qualification.hyp_009_daily_client import assert_split_raw_alignment
from acash.research.hyp_009.accounting import DividendEvent


def qualify_bar_series(
    expected_sessions: Sequence[date],
    split_bars: Sequence[DailyBar],
    raw_bars: Sequence[DailyBar],
) -> List[date]:
    """Validate both series against the calendar-derived expectation."""
    expected = list(expected_sessions)
    if not expected or expected != sorted(expected) or len(set(expected)) != len(expected):
        raise DataContractError("QUALIFY_EXPECTED_SESSIONS_CORRUPT.")
    for label, bars in (("split", split_bars), ("raw", raw_bars)):
        sessions = [bar.timestamp_utc.date() for bar in bars]
        if len(sessions) != len(expected):
            raise DataContractError(
                f"QUALIFY_{label.upper()}_COUNT_MISMATCH: {len(sessions)} != {len(expected)}."
            )
        if sorted(sessions) != expected:
            missing = sorted(set(expected) - set(sessions))
            extra = sorted(set(sessions) - set(expected))
            raise DataContractError(
                f"QUALIFY_{label.upper()}_SESSION_MISMATCH: missing={missing} extra={extra}."
            )
        if len(set(sessions)) != len(sessions):
            raise DataContractError(f"QUALIFY_{label.upper()}_DUPLICATE_SESSION.")
        for bar in bars:
            if bar.timestamp_utc.weekday() >= 5:
                raise DataContractError(
                    f"QUALIFY_{label.upper()}_WEEKEND_ROW: {bar.timestamp_utc.date()}."
                )
    return assert_split_raw_alignment(list(split_bars), list(raw_bars))


def qualify_dividends(
    records: Sequence[Mapping[str, object]],
    scope_start: date,
    scope_end: date,
) -> List[DividendEvent]:
    """Bind authoritative distribution records to ex-date/payable/amount events.

    The authority manifest legitimately spans wider history; records outside
    [scope_start, scope_end] are EXCLUDED (never admitted to the dataset),
    while every in-scope record is fully validated. Missing/incomplete in-scope
    data fails closed; no inference is performed.
    """
    events: List[DividendEvent] = []
    seen: Dict[date, Decimal] = {}
    for record in records:
        try:
            ex = date.fromisoformat(str(record["ex_date"]))
            payable = date.fromisoformat(str(record["payable_date"]))
            amount = Decimal(str(record["cash_distribution"]))
        except (KeyError, ValueError, InvalidOperation, TypeError) as exc:
            raise DataContractError(f"DIVIDEND_MALFORMED_RECORD: {exc}.") from exc
        if not (scope_start <= ex <= scope_end):
            continue
        if amount <= Decimal("0"):
            raise DataContractError(f"DIVIDEND_NONPOSITIVE_AMOUNT: {ex}.")
        if ex in seen and seen[ex] != amount:
            raise DataContractError(f"DIVIDEND_CONTRADICTORY_EX_DATE: {ex}.")
        seen[ex] = amount
        events.append(DividendEvent(ex_date=ex, payable_date=payable, amount_per_share=amount))
    return sorted(events, key=lambda event: event.ex_date)


def require_quarterly_authority_coverage(
    events: Sequence[DividendEvent],
    scope_start: date,
    scope_end: date,
) -> str:
    """Fail closed unless every calendar quarter in scope has >= 1 ex-date.

    SPY's sealed distribution history is quarterly; a scope quarter without an
    authoritative ex-date is an authority coverage gap, NOT a zero distribution.
    Never infer D=0 from absent authority.
    """
    if scope_start > scope_end:
        raise DataContractError("DIVIDEND_SCOPE_INVERTED.")
    covered = {(e.ex_date.year, (e.ex_date.month - 1) // 3) for e in events}
    year, month = scope_start.year, scope_start.month
    end_key = (scope_end.year, (scope_end.month - 1) // 3)
    missing: List[str] = []
    while (year, (month - 1) // 3) <= end_key:
        quarter = (month - 1) // 3
        if (year, quarter) not in covered:
            missing.append(f"{year}-Q{quarter + 1}")
        month += 3
        if month > 12:
            month = 1
            year += 1
    if missing:
        raise DataContractError(
            f"BLOCKED_DIVIDEND_AUTHORITY_COVERAGE_GAP: no authoritative ex-date for {missing}."
        )
    return "DIVIDEND_AUTHORITY_COVERAGE_COMPLETE"


def require_no_unbound_splits(
    sessions: Sequence[date],
    split_close: Mapping[date, Decimal],
    raw_close: Mapping[date, Decimal],
) -> str:
    """Fail closed if raw/split ratio implies a split without bound authority."""
    ratios: List[Tuple[date, Decimal]] = []
    for session in sessions:
        raw = raw_close.get(session)
        split = split_close.get(session)
        if raw is None or split is None or split <= Decimal("0") or raw <= Decimal("0"):
            raise DataContractError(f"SPLIT_CHECK_MISSING_PRICE: {session}.")
        ratios.append((session, raw / split))
    first = ratios[0][1]
    tolerance = first * Decimal("0.000001")
    changes = [
        session for session, ratio in ratios if abs(ratio - first) > tolerance
    ]
    if changes:
        raise DataContractError(
            f"BLOCKED_UNBOUND_SPLIT_AUTHORITY: ratio discontinuity at {changes}."
        )
    return "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"
