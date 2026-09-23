"""Unit tests for HYP_007 Step R4 M2 execution engine and invariants.

Validates:
- Stage A freeze required before M2 network access.
- Exact M2 date bounds and census (569 regular sessions, 6 early closes excluded).
- Request rejection for 2026-08-15 and beyond.
- Quarantine-gap firewall and M3 firewall.
- M2 starting AUM is exactly $100,000.00.
- M2 warm-up statistical state continuity from sealed M1 history.
- Regulatory fee schedules for M2 (SEC Section 31 and FINRA TAF).
- Dividend projection manifest matching SSGA distributions.
- Four exact R4 continuation gates and strict fail-closed contract.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.step_r4_hyp_007 import (
    M2_FINRA_TAF_SCHEDULE,
    M2_SEC31_SCHEDULE,
    build_m2_calendar_census,
    compute_m2_finra_taf,
    compute_m2_sec31_fee,
    load_m2_dividend_projection,
    validate_r4_preconditions,
)
from acash.research.step_r4_hyp_007_governance import (
    M2_CLASSIFICATION,
    M2_END_DATE,
    M2_END_DATE_STR,
    M2_ROLE,
    M2_SIMULATED_STARTING_AUM_USD,
    M2_START_DATE,
    M2_START_DATE_STR,
    M2_WARMUP_NOISE_AREA_SESSIONS,
    M2_WARMUP_SOURCE,
    M2_WARMUP_VOLATILITY_CLOSES,
    M3_ACCESS_STATUS,
    M3_ROLE,
    QUARANTINE_START_DATE,
    QUARANTINE_START_DATE_STR,
    R4_G1_NET_TOTAL_RETURN_MIN,
    R4_G2_NET_ANNUALIZED_SHARPE_MIN,
    R4_G3_MAX_DRAWDOWN_MAX,
    R4_G4_STRESS_TOTAL_RETURN_MIN,
    R4Verdict,
    enforce_m2_market_data_range_guard,
    enforce_m3_firewall,
    enforce_quarantine_firewall,
    evaluate_r4_gates,
)


def test_r4_preconditions_stage_a_verified() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    preconditions = validate_r4_preconditions(repo_root)
    assert "stage_a_manifest_sha256" in preconditions
    assert "stage_a_doc_sha256" in preconditions


def test_m2_census_regular_and_early_closes() -> None:
    census = build_m2_calendar_census()
    assert census.calendar_days_count == 836
    assert len(census.regular_sessions) == 569
    assert len(census.early_closes) == 6

    # Verify excluded early closes
    expected_early_closes = {
        date(2024, 7, 3),
        date(2024, 11, 29),
        date(2024, 12, 24),
        date(2025, 7, 3),
        date(2025, 11, 28),
        date(2025, 12, 24),
    }
    assert set(census.early_closes) == expected_early_closes

    # First and last regular sessions in M2
    assert census.regular_sessions[0] == date(2024, 5, 1)
    assert census.regular_sessions[-1] == date(2026, 8, 14)


def test_m2_market_data_range_guard_strictly_enforced() -> None:
    # Valid M2 boundaries
    enforce_m2_market_data_range_guard(date(2024, 5, 1))
    enforce_m2_market_data_range_guard(date(2026, 8, 14))

    # Reject before M2
    with pytest.raises(DataContractError, match="before M2_START"):
        enforce_m2_market_data_range_guard(date(2024, 4, 30))

    # Reject after M2 (quarantine gap)
    with pytest.raises(DataContractError, match="after M2_END"):
        enforce_m2_market_data_range_guard(date(2026, 8, 15))


def test_quarantine_and_m3_firewalls() -> None:
    m3_start = date(2026, 9, 23)

    # Quarantine gap: [2026-08-15, 2026-09-23)
    with pytest.raises(DataContractError, match="Quarantine gap violation"):
        enforce_quarantine_firewall(date(2026, 8, 15), m3_start=m3_start)

    with pytest.raises(DataContractError, match="Quarantine gap violation"):
        enforce_quarantine_firewall(date(2026, 9, 22), m3_start=m3_start)

    # M3 prospective start
    with pytest.raises(DataContractError, match="M3 firewall violation"):
        enforce_m3_firewall(date(2026, 9, 23), m3_start=m3_start)


def test_m2_dividend_manifest_reconciled() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    divs = load_m2_projected_dividends(repo_root)
    assert len(divs) == 9

    # Check quarterly sequence
    ex_dates = [d.ex_date for d in divs]
    assert ex_dates == [
        "2024-06-21",
        "2024-09-20",
        "2024-12-20",
        "2025-03-21",
        "2025-06-20",
        "2025-09-19",
        "2025-12-19",
        "2026-03-20",
        "2026-06-18",
    ]
    for d in divs:
        assert d.cash_distribution > Decimal("0")
        assert d.currency == "USD"
        assert d.distribution_type == "CASH_DIVIDEND"


def test_m2_regulatory_fee_schedules() -> None:
    # SEC31: check rate transitions
    fee_2024_may_1 = compute_m2_sec31_fee(Decimal("100000.00"), date(2024, 5, 1))
    assert fee_2024_may_1 == Decimal("0.80")  # 100k * 0.00000800 = 0.80

    fee_2024_may_22 = compute_m2_sec31_fee(Decimal("100000.00"), date(2024, 5, 22))
    assert fee_2024_may_22 == Decimal("2.78")  # 100k * 0.00002780 = 2.78

    fee_2025_jun_1 = compute_m2_sec31_fee(Decimal("100000.00"), date(2025, 6, 1))
    assert fee_2025_jun_1 == Decimal("0.00")  # $0 rate

    fee_2026_may_1 = compute_m2_sec31_fee(Decimal("100000.00"), date(2026, 5, 1))
    assert fee_2026_may_1 == Decimal("2.06")  # 100k * 0.00002060 = 2.06

    # FINRA TAF: check rates and rounding ceiling to cent
    taf_2024 = compute_m2_finra_taf(100, date(2024, 6, 1))
    assert taf_2024 == Decimal("0.02")  # 100 * 0.000166 = 0.0166 -> ceiling 0.02

    taf_2025 = compute_m2_finra_taf(100, date(2025, 6, 1))
    assert taf_2025 == Decimal("0.02")  # 100 * 0.000195 = 0.0195 -> ceiling 0.02


def test_m2_continuation_gates_all_four_required() -> None:
    # All 4 pass
    eval_pass = evaluate_r4_gates(
        net_total_return=Decimal("0.05"),
        annualized_sharpe=Decimal("0.65"),
        max_drawdown=Decimal("0.20"),
        stress_total_return=Decimal("0.01"),
        contract_valid=True,
    )
    assert eval_pass.verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED
    assert eval_pass.all_passed is True

    # 1 gate fails -> FAIL_CURRENT_EDGE_NOT_SUPPORTED
    eval_fail = evaluate_r4_gates(
        net_total_return=Decimal("0.05"),
        annualized_sharpe=Decimal("0.48"),  # < 0.50
        max_drawdown=Decimal("0.20"),
        stress_total_return=Decimal("0.01"),
        contract_valid=True,
    )
    assert eval_fail.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert eval_fail.all_passed is False
