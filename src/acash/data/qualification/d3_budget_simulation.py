"""Offline HTTP-request and byte budget simulation for multi-symbol daily bars.

Pure arithmetic: no network, no credentials, no authority issuance. Alpaca's
multi-symbol bars endpoint applies ``limit`` to the total bar count across all
symbols in a page, and a ``next_page_token`` must be followed even when a page
is not full. The adverse scenario therefore adds trailing pages per adjustment
for a non-null token returned on an exactly full or short final page.

Bytes per bar are assumptions, not measurements; results are only as good as
those inputs and must be replaced by observed receipts before any authority
decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.lane_a_rehearsal import expected_session_dates

D5_PROPOSED_MAX_HTTP_REQUESTS = 32
D5_PROPOSED_MAX_OBSERVED_BYTES = 8_388_608


@dataclass(frozen=True)
class BudgetScenario:
    name: str
    page_limit: int
    bytes_per_bar: int
    page_overhead_bytes: int
    trailing_pages_per_adjustment: int


@dataclass(frozen=True)
class BudgetEstimate:
    scenario: str
    sessions: int
    bars_per_adjustment: int
    requests: int
    observed_bytes: int
    within_request_ceiling: bool
    within_byte_ceiling: bool


def simulate_bars_budget(
    *,
    symbols: Sequence[str],
    start: date,
    end: date,
    adjustments: Sequence[str],
    scenario: BudgetScenario,
    max_http_requests: int = D5_PROPOSED_MAX_HTTP_REQUESTS,
    max_observed_bytes: int = D5_PROPOSED_MAX_OBSERVED_BYTES,
) -> BudgetEstimate:
    if not symbols or len(set(symbols)) != len(symbols):
        raise DataContractError("D3_BUDGET_SYMBOLS_EMPTY_OR_DUPLICATE.")
    if not adjustments or len(set(adjustments)) != len(adjustments):
        raise DataContractError("D3_BUDGET_ADJUSTMENTS_EMPTY_OR_DUPLICATE.")
    if scenario.page_limit <= 0 or scenario.bytes_per_bar <= 0:
        raise DataContractError("D3_BUDGET_NON_POSITIVE_SCENARIO_PARAMETER.")
    if scenario.page_overhead_bytes < 0 or scenario.trailing_pages_per_adjustment < 0:
        raise DataContractError("D3_BUDGET_NEGATIVE_SCENARIO_PARAMETER.")
    sessions = len(expected_session_dates(start, end, NyseCa1Calendar()))
    if sessions == 0:
        raise DataContractError("D3_BUDGET_NO_SESSIONS.")
    bars = sessions * len(symbols)
    full_pages = -(-bars // scenario.page_limit)
    pages_per_adjustment = full_pages + scenario.trailing_pages_per_adjustment
    requests = pages_per_adjustment * len(adjustments)
    observed_bytes = len(adjustments) * (
        bars * scenario.bytes_per_bar
        + pages_per_adjustment * scenario.page_overhead_bytes
    )
    return BudgetEstimate(
        scenario=scenario.name,
        sessions=sessions,
        bars_per_adjustment=bars,
        requests=requests,
        observed_bytes=observed_bytes,
        within_request_ceiling=requests <= max_http_requests,
        within_byte_ceiling=observed_bytes <= max_observed_bytes,
    )


__all__ = [
    "BudgetEstimate",
    "BudgetScenario",
    "D5_PROPOSED_MAX_HTTP_REQUESTS",
    "D5_PROPOSED_MAX_OBSERVED_BYTES",
    "simulate_bars_budget",
]
