"""Budget simulation for the proposed four-ETF 2016-2025 daily raw/split retrieval."""

from __future__ import annotations

from datetime import date

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.d3_budget_simulation import (
    BudgetEstimate,
    BudgetScenario,
    simulate_bars_budget,
)

SYMBOLS = ("BIL", "BND", "GLD", "VOO")
ADJUSTMENTS = ("raw", "split")
START, END = date(2016, 1, 1), date(2025, 12, 31)

REALISTIC = BudgetScenario("REALISTIC", 1000, 130, 64, 0)
ADVERSE = BudgetScenario("ADVERSE", 1000, 200, 256, 1)
DEFAULT_LIMIT_UNFROZEN = BudgetScenario("ADVERSE_LIMIT_100", 100, 200, 256, 1)


def _run(
    scenario: BudgetScenario, adjustments: tuple[str, ...] = ADJUSTMENTS
) -> BudgetEstimate:
    return simulate_bars_budget(
        symbols=SYMBOLS, start=START, end=END, adjustments=adjustments, scenario=scenario
    )


def test_realistic_fits_proposed_ceilings() -> None:
    estimate = _run(REALISTIC)
    assert estimate.sessions == 2514
    assert estimate.bars_per_adjustment == 10_056
    assert estimate.requests == 22
    assert estimate.observed_bytes == 2 * (10_056 * 130 + 11 * 64)
    assert estimate.within_request_ceiling and estimate.within_byte_ceiling


def test_adverse_trailing_token_pages_still_fit() -> None:
    estimate = _run(ADVERSE)
    assert estimate.requests == 24
    assert estimate.observed_bytes == 2 * (10_056 * 200 + 12 * 256)
    assert estimate.within_request_ceiling and estimate.within_byte_ceiling


def test_byte_ceiling_breaks_near_417_bytes_per_bar() -> None:
    fits = _run(BudgetScenario("B416", 1000, 416, 256, 1))
    breaks = _run(BudgetScenario("B417", 1000, 417, 256, 1))
    assert fits.within_byte_ceiling and not breaks.within_byte_ceiling


def test_smaller_page_limit_or_third_adjustment_exceeds_requests() -> None:
    assert not _run(DEFAULT_LIMIT_UNFROZEN).within_request_ceiling
    assert not _run(ADVERSE, ("all", "raw", "split")).within_request_ceiling


@pytest.mark.parametrize(
    "kwargs",
    [
        {"symbols": ()},
        {"symbols": ("VOO", "VOO")},
        {"adjustments": ()},
        {"scenario": BudgetScenario("BAD", 0, 130, 0, 0)},
        {"scenario": BudgetScenario("BAD", 1000, 130, -1, 0)},
        {"start": date(2026, 1, 3), "end": date(2026, 1, 4)},
    ],
)
def test_malformed_inputs_fail_closed(kwargs: dict[str, object]) -> None:
    args: dict[str, object] = {
        "symbols": SYMBOLS,
        "start": START,
        "end": END,
        "adjustments": ADJUSTMENTS,
        "scenario": REALISTIC,
    }
    args.update(kwargs)
    with pytest.raises(DataContractError):
        simulate_bars_budget(**args)  # type: ignore[arg-type]
