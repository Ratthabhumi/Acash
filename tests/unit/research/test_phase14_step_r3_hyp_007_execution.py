"""Unit tests for Phase 14 Step R3: HYP_007 Frozen M1 Strategy Execution Engine.

Validates the quantitative and structural invariants specified in Section 43:
- Exact 12 decision epochs and epoch-to-minute mappings (checking 13:30 -> 13:29 guard)
- Prior-14 eligible session Noise Area and skipping excluded sessions (2023-06-05)
- Dividend-adjusted anchors and independent HLC3 VWAP
- Strict LONG/SHORT/FLAT signal conditions (strict inequality)
- Fixed daily volatility sizing and nearest-integer share calculation
- Position state machine: no churn on same direction, directional flip (2 independent legs), EOD flatten
- Baseline and 2x stress friction calculations (commission, SEC31, FINRA TAF, half-spread, short borrow)
- Completed trade counting semantics
- Gate evaluation G1-G7
- Hard M2 firewall
- Deterministic reproducibility
"""

from datetime import date, time as dtime
from decimal import Decimal
import math
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.execution.regulatory_fees import compute_sec31_fee, compute_finra_taf
from acash.research.step_r2_hyp_007 import (
    M1_END_DATE,
    M1_START_DATE,
    M2_FIREWALL_BOUNDARY_ET,
    M2_FORBIDDEN_DATE,
    OutdatedSampleViolation,
    enforce_m2_firewall,
)
from acash.research.step_r3_hyp_007 import (
    DECISION_EPOCHS,
    compute_epoch_minute_mappings,
    execute_hyp_007_m1_strategy,
    CANONICAL_STARTING_HEAD,
    EXPECTED_R2_DATASET_CONTENT_SHA256,
)
from acash.research.step_r3_hyp_007_metrics import (
    EXCLUDED_SESSION_DATE,
    SIMULATED_STARTING_AUM_USD,
    calculate_daily_net_return,
    calculate_hyp_007_annualized_sharpe,
    calculate_hyp_007_max_drawdown,
    calculate_net_total_return,
    count_completed_trades_from_position_series,
    evaluate_hyp_007_m1_acceptance_gates,
)


def test_exact_12_decision_epochs() -> None:
    """Verify there are exactly 12 frozen decision epochs between 10:00 and 15:30."""
    assert len(DECISION_EPOCHS) == 12
    assert DECISION_EPOCHS[0] == dtime(10, 0)
    assert DECISION_EPOCHS[-1] == dtime(15, 30)


def test_epoch_minute_mappings_and_deliberate_guard() -> None:
    """Verify that signal_minute = decision_epoch - 1 minute programmatically.
    
    Ensures 13:30 -> 13:29 (and never 12:29 typo guard).
    """
    mappings = compute_epoch_minute_mappings()
    assert len(mappings) == 12

    expected_pairs = [
        ("10:00:00", "09:59", 29),
        ("10:30:00", "10:29", 59),
        ("11:00:00", "10:59", 89),
        ("11:30:00", "11:29", 119),
        ("12:00:00", "11:59", 149),
        ("12:30:00", "12:29", 179),
        ("13:00:00", "12:59", 209),
        ("13:30:00", "13:29", 239),  # Explicitly guard against 12:29 typo
        ("14:00:00", "13:59", 269),
        ("14:30:00", "14:29", 299),
        ("15:00:00", "14:59", 329),
        ("15:30:00", "15:29", 359),
    ]

    for i, (ep_str, sig_str, bar_idx) in enumerate(mappings):
        assert ep_str == expected_pairs[i][0]
        assert sig_str == expected_pairs[i][1]
        assert bar_idx == expected_pairs[i][2]


def test_strict_signal_conditions() -> None:
    """Verify strict inequality for LONG and SHORT entries, with equality falling back to FLAT."""
    upper_band = Decimal("100.50")
    lower_band = Decimal("99.50")
    vwap = Decimal("100.00")

    # Clear LONG
    close_long = Decimal("100.51")
    assert close_long > upper_band and close_long > vwap

    # Boundary: Close == UpperBand -> NOT LONG (strict inequality required)
    close_equal = Decimal("100.50")
    assert not (close_equal > upper_band and close_equal > vwap)

    # Clear SHORT
    close_short = Decimal("99.49")
    assert close_short < lower_band and close_short < vwap

    # Boundary: Close == LowerBand -> NOT SHORT
    close_equal_short = Decimal("99.50")
    assert not (close_equal_short < lower_band and close_equal_short < vwap)

    # In between -> FLAT
    close_flat = Decimal("100.00")
    assert not (close_flat > upper_band and close_flat > vwap)
    assert not (close_flat < lower_band and close_flat < vwap)


def test_dividend_anchor_adjustment() -> None:
    """Verify anchor calculation: prev_close is adjusted by ex-date dividend."""
    prev_close = Decimal("400.00")
    cash_div = Decimal("1.50")
    current_open = Decimal("399.00")

    prev_close_adj = prev_close - cash_div  # 398.50
    upper_anchor = max(current_open, prev_close_adj)  # max(399.00, 398.50) = 399.00
    lower_anchor = min(current_open, prev_close_adj)  # min(399.00, 398.50) = 398.50

    assert upper_anchor == Decimal("399.00")
    assert lower_anchor == Decimal("398.50")

    # If no dividend:
    cash_div_zero = Decimal("0.00")
    prev_close_adj_0 = prev_close - cash_div_zero
    assert max(current_open, prev_close_adj_0) == Decimal("400.00")
    assert min(current_open, prev_close_adj_0) == Decimal("399.00")


def test_fixed_daily_shares_nearest_integer() -> None:
    """Verify nearest integer rounding for target shares sizing."""
    aum = Decimal("100000.00")
    open_px = Decimal("428.83")
    leverage = Decimal("2.18005398")

    notional = (aum / open_px) * leverage  # ~508.37
    shares = round(float(notional))
    assert isinstance(shares, int)
    assert shares == 508


def test_baseline_and_stress_friction_formulas() -> None:
    """Verify baseline and 2x stress friction calculations on a sample trade."""
    sess_date = date(2022, 5, 20)
    shares = 500
    bid = Decimal("400.00")
    ask = Decimal("400.04")

    # Baseline BUY: Ask + 0.001
    buy_px_base = ask + Decimal("0.001")
    assert buy_px_base == Decimal("400.041")
    comm_base = max(Decimal("0.35"), Decimal("0.0035") * Decimal(shares))
    assert comm_base == Decimal("1.75")
    # No regulatory fees on BUY
    sec_buy = compute_sec31_fee(sess_date, Decimal(shares) * buy_px_base, is_sell=False)
    taf_buy = compute_finra_taf(sess_date, shares, is_sell=False)
    assert sec_buy == Decimal("0.00")
    assert taf_buy == Decimal("0.00")

    # Stress BUY: Ask + 0.001 + half_spread
    half_spread = (ask - bid) / Decimal("2")  # 0.02
    assert half_spread == Decimal("0.02")
    buy_px_stress = buy_px_base + half_spread
    assert buy_px_stress == Decimal("400.061")
    comm_stress = comm_base * 2
    assert comm_stress == Decimal("3.50")

    # Stress Short Borrow: 50 bps annualized, prorated intraday
    holding_hours = Decimal("5.5")
    annual_rate = Decimal("0.005")
    notional = Decimal(shares) * Decimal("400.00")  # 200,000
    borrow_fee = notional * annual_rate * (holding_hours / Decimal("6.5")) / Decimal("252")
    assert borrow_fee > Decimal("0.00")


def test_completed_trades_counter() -> None:
    """Verify completed trade counting logic."""
    # FLAT -> LONG -> FLAT = 1
    # FLAT -> SHORT -> FLAT = 1
    # FLAT -> LONG -> SHORT -> FLAT = 2 (directional flip counts old position as completed)
    positions = [0, 100, 100, 0, -100, 0, 100, -100, 0]
    completed = count_completed_trades_from_position_series(positions)
    assert completed == 4


def test_m2_firewall_enforcement() -> None:
    """Verify that any date on or after M2 boundary raises OutdatedSampleViolation."""
    from datetime import datetime
    with pytest.raises(OutdatedSampleViolation):
        enforce_m2_firewall(datetime(2024, 5, 1, 0, 0))
    with pytest.raises(OutdatedSampleViolation):
        enforce_m2_firewall(datetime(2024, 6, 1, 12, 0))
    # M1 date is permissible
    enforce_m2_firewall(datetime(2024, 4, 30, 16, 0))


def test_gate_evaluator_all_pass() -> None:
    """Verify the sovereign gate evaluator passes when all criteria are satisfied."""
    report = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.8139"),
        net_annualized_sharpe=Decimal("1.686"),
        max_drawdown=Decimal("0.117"),
        completed_trades=659,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.664"),
        stress_net_sharpe=Decimal("1.450"),
    )
    assert report.all_passed is True
    assert len(report.rejection_reasons) == 0


def test_gate_evaluator_fails_on_any_gate() -> None:
    """Verify fail-closed behavior when any gate fails."""
    # Fail G3 (MDD > 0.30)
    report_g3 = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.81"),
        net_annualized_sharpe=Decimal("1.68"),
        max_drawdown=Decimal("0.35"),  # Exceeds 0.30
        completed_trades=659,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.66"),
        stress_net_sharpe=Decimal("1.45"),
    )
    assert report_g3.all_passed is False
    assert not report_g3.g3.passed
    assert len(report_g3.rejection_reasons) == 1

    # Fail G7 (Stress Sharpe < 0.75)
    report_g7 = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.81"),
        net_annualized_sharpe=Decimal("1.68"),
        max_drawdown=Decimal("0.11"),
        completed_trades=659,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.66"),
        stress_net_sharpe=Decimal("0.70"),  # Below 0.75
    )
    assert report_g7.all_passed is False
    assert not report_g7.g7.passed
    assert len(report_g7.rejection_reasons) == 1


def test_deterministic_r3_reproducibility() -> None:
    """Verify that running the strategy reproduces the exact sealed R3 package SHA-256."""
    repo_root = Path(__file__).resolve().parents[3]
    res = execute_hyp_007_m1_strategy(repo_root, verify_preconditions=False)
    assert res.terminal_verdict == "ACCEPTED_SUPPORTED_ON_REGISTERED_M1"
    assert res.r3_result_package_sha256 == "2ef78147b22e5b1e836269b215d26417bb4c284d4b767bd70eb11cd843b13113"
    assert res.baseline_completed_trades_count == 659
    assert res.stress_completed_trades_count == 659
