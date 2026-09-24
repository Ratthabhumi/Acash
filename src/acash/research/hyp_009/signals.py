"""Frozen HYP_009 signal construction: causal total-return index + 10M SMA states.

Conventions (bound to the accounting clarification):
- TR_0 = 1.0 anchored immediately before the first session, with P_0 := P_first
  (no price change, only a possible first-session distribution). TR for the first
  session is therefore 1 + D_first / P_first (exactly 1.0 when D_first == 0).
- TR_t = TR_{t-1} * (P_t + D_t) / P_{t-1} for every later session, P from
  split-adjusted closes, D from authoritative ex-date cash distributions.
- Month-end signal level = TR on the final eligible session of the month.
- SMA10 = arithmetic mean of the current + prior 9 month-end levels.
- LONG iff level > SMA10, else CASH (equality -> CASH, no tolerance).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.research.hyp_009.partitions import month_end_sessions

LOOKBACK_MONTH_ENDS: int = 10


@dataclass(frozen=True)
class MonthSignal:
    decision_date: date
    signal_level: Decimal
    sma10: Decimal
    state: str
    prior_state: Optional[str]
    transition: bool


def build_total_return_index(
    sessions: Sequence[date],
    split_close: Mapping[date, Decimal],
    dividends: Mapping[date, Decimal],
) -> Dict[date, Decimal]:
    """Deterministic causal total-return index over an ordered session list."""
    if not sessions:
        raise DataContractError("TR_EMPTY_SESSIONS: no sessions supplied.")
    ordered = list(sessions)
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise DataContractError("TR_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    for session in ordered:
        if session not in split_close:
            raise DataContractError(f"TR_MISSING_SPLIT_CLOSE: {session}.")
        if split_close[session] <= Decimal("0"):
            raise DataContractError(f"TR_NONPOSITIVE_SPLIT_CLOSE: {session}.")
        amount = dividends.get(session, Decimal("0"))
        if amount < Decimal("0"):
            raise DataContractError(f"TR_NEGATIVE_DIVIDEND: {session}.")
    index: Dict[date, Decimal] = {}
    running = Decimal("1.0")
    prev_price = split_close[ordered[0]]
    for session in ordered:
        price = split_close[session]
        dist = dividends.get(session, Decimal("0"))
        running = running * (price + dist) / prev_price
        index[session] = running
        prev_price = price
    return index


def compute_signal_states(
    sessions: Sequence[date],
    split_close: Mapping[date, Decimal],
    dividends: Mapping[date, Decimal],
) -> List[MonthSignal]:
    """Month-end LONG/CASH states; needs >= 10 completed month-end observations."""
    ordered = list(sessions)
    month_ends = month_end_sessions(ordered)
    if len(month_ends) < LOOKBACK_MONTH_ENDS:
        raise DataContractError(
            f"WARMUP_INCOMPLETE: {len(month_ends)} month-ends < {LOOKBACK_MONTH_ENDS}."
        )
    index = build_total_return_index(ordered, split_close, dividends)
    levels = [index[month_end] for month_end in month_ends]
    signals: List[MonthSignal] = []
    prior_state: Optional[str] = None
    for i in range(LOOKBACK_MONTH_ENDS - 1, len(month_ends)):
        window = levels[i - LOOKBACK_MONTH_ENDS + 1 : i + 1]
        if len(window) != LOOKBACK_MONTH_ENDS:
            raise DataContractError("SMA_WINDOW_CORRUPT: expected exactly 10 levels.")
        sma = sum(window, Decimal("0")) / Decimal(LOOKBACK_MONTH_ENDS)
        level = levels[i]
        state = "LONG" if level > sma else "CASH"
        signals.append(
            MonthSignal(
                decision_date=month_ends[i],
                signal_level=level,
                sma10=sma,
                state=state,
                prior_state=prior_state,
                transition=(prior_state is not None and state != prior_state),
            )
        )
        prior_state = state
    return signals


def resolve_execution_dates(
    signals: Sequence[MonthSignal], m1_sessions: Sequence[date]
) -> Dict[date, Optional[date]]:
    """Next M1 session strictly after each decision; None when outside M1.

    A December-2020 signal whose execution would fall in January 2021 resolves
    to None (PENDING_NEXT_PARTITION_EXECUTION_NOT_EXECUTED) — the caller MUST
    NOT fetch 2021 data to satisfy it.
    """
    ordered = sorted(m1_sessions)
    if not ordered or len(set(ordered)) != len(ordered):
        raise DataContractError("EXECUTION_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    resolved: Dict[date, Optional[date]] = {}
    for signal in signals:
        execution: Optional[date] = None
        for session in ordered:
            if session > signal.decision_date:
                execution = session
                break
        resolved[signal.decision_date] = execution
    return resolved
