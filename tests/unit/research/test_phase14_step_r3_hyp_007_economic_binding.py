"""Unit tests and governance invariant verifications for HYP_007 Pre-R3 Economic Metric Binding.

Governed by:
- AUTHORIZE_HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING
- docs/phase14/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_001.md
- docs/phase14/manifests/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_001.json
"""

from decimal import Decimal
import json
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.step_r3_hyp_007_metrics import (
    AUM_REFERENCE_POLICY,
    BASELINE_AND_STRESS_HAVE_INDEPENDENT_AUM_PATHS,
    BENCHMARK_STATUS,
    COMPLETED_TRADE_DEFINITION,
    EXCLUDED_SESSION_DATE,
    EXCLUDED_SESSION_PERFORMANCE_ELIGIBLE,
    EXCLUDED_SESSION_SIGNAL_ELIGIBLE,
    EXCLUDED_SESSION_TRADE_ELIGIBLE,
    EXCLUDED_SESSION_VOLATILITY_ELIGIBLE,
    NO_REAL_ORDERS,
    OPPOSITE_SIGNAL_FLIP_BEHAVIOR,
    PERIODS_PER_YEAR,
    REAL_CAPITAL_AUTHORITY_USD,
    RISK_FREE_RATE,
    SAME_DIRECTION_REPEAT_SIGNAL_BEHAVIOR,
    SEARCH_TRIAL_COUNT_K,
    SHARPE_AUTHORITY_FUNCTION,
    SHARPE_DDOF,
    SHARPE_ZERO_VARIANCE_BEHAVIOR,
    SIMULATED_AUM_AUTHORITY_OUTCOME,
    SIMULATED_AUM_CLASSIFICATION,
    SIMULATED_STARTING_AUM_USD,
    TARGET_SHARES_FIXED_FOR_SESSION,
    calculate_daily_net_return,
    calculate_hyp_007_annualized_sharpe,
    calculate_hyp_007_max_drawdown,
    calculate_net_total_return,
    count_completed_trades_from_position_series,
)
from acash.research.step_r2_hyp_007 import enforce_m2_firewall, OutdatedSampleViolation
from datetime import datetime, timezone


def test_1_simulated_starting_aum_frozen_and_non_capital() -> None:
    """Invariant 1: Starting AUM is frozen at $100,000.00 as non-capital accounting normalization."""
    assert SIMULATED_STARTING_AUM_USD == Decimal("100000.00")
    assert SIMULATED_AUM_AUTHORITY_OUTCOME == "C_NO_PRIOR_VALUE_ESTABLISHED"
    assert SIMULATED_AUM_CLASSIFICATION == "HUMAN_RATIFIED_PRE_RESULT_ACCOUNTING_NORMALIZATION"
    assert REAL_CAPITAL_AUTHORITY_USD == Decimal("0.00")
    assert NO_REAL_ORDERS is True
    assert SEARCH_TRIAL_COUNT_K == 1


def test_2_daily_net_return_formula_and_contract() -> None:
    """Invariant 2: Daily net return strictly follows r_t = EndingAUM_t / EndingAUM_{t-1} - 1."""
    prior = Decimal("100000.00")
    today = Decimal("101500.00")
    ret = calculate_daily_net_return(today, prior)
    assert ret == Decimal("0.015")  # +1.5%

    # Non-positive prior or ending fails closed
    with pytest.raises(DataContractError, match="non-positive prior AUM"):
        calculate_daily_net_return(today, Decimal("0.0"))

    with pytest.raises(DataContractError, match="non-positive ending AUM"):
        calculate_daily_net_return(Decimal("-100.0"), prior)


def test_3_net_total_return_formula_non_additive() -> None:
    """Invariant 3: Net total return uses compounded equity: FinalAUM / InitialAUM - 1 (never sum of daily returns)."""
    initial = Decimal("100000.00")
    final = Decimal("125000.00")
    tot_ret = calculate_net_total_return(final, initial)
    assert tot_ret == Decimal("0.25")  # +25.0%

    with pytest.raises(DataContractError, match="non-positive initial AUM"):
        calculate_net_total_return(final, Decimal("0.0"))


def test_4_annualized_sharpe_authority_and_parameters() -> None:
    """Invariant 4: Annualized Sharpe delegates to single canonical authority with 252 periods, ddof=1, rf=0."""
    assert PERIODS_PER_YEAR == 252
    assert SHARPE_DDOF == 1
    assert RISK_FREE_RATE == Decimal("0.0")
    assert SHARPE_ZERO_VARIANCE_BEHAVIOR == "FAIL_CLOSED_DATA_CONTRACT_ERROR"
    assert SHARPE_AUTHORITY_FUNCTION == "acash.validation.deflated_sharpe.calculate_annualized_sharpe"

    # Known analytical return sequence
    # 2 returns: +0.01, +0.03 -> mean = 0.02, std(ddof=1) = 0.0141421356..., Sharpe = 0.02 / std * sqrt(252)
    daily_returns = [Decimal("0.01"), Decimal("0.03")]
    sr = calculate_hyp_007_annualized_sharpe(daily_returns)
    assert sr > Decimal("0")

    # Zero-variance strictly fails closed (AGENTS.md core principle 3)
    zero_var_returns = [Decimal("0.01"), Decimal("0.01"), Decimal("0.01")]
    with pytest.raises(DataContractError, match="zero-variance return series"):
        calculate_hyp_007_annualized_sharpe(zero_var_returns)


def test_5_max_drawdown_authority_anchored_at_initial_aum() -> None:
    """Invariant 5: Max drawdown is peak-to-trough from net end-of-day equity curve anchored at AUM_0."""
    equity_curve = [
        Decimal("100000.00"),  # Day 0
        Decimal("105000.00"),  # Day 1: new peak 105k
        Decimal("94500.00"),   # Day 2: drop 105k -> 94.5k = 10% dd
        Decimal("84000.00"),   # Day 3: drop 105k -> 84k = 20% dd
        Decimal("99750.00"),   # Day 4: recovery to 99.75k
    ]
    max_dd = calculate_hyp_007_max_drawdown(equity_curve)
    # Peak is 105,000, trough is 84,000 -> DD = (105000 - 84000) / 105000 = 21000 / 105000 = 0.20
    assert max_dd == Decimal("0.2")

    # Empty curve fails closed
    with pytest.raises(DataContractError, match="empty equity curve"):
        calculate_hyp_007_max_drawdown([])


def test_6_completed_trade_and_flip_counting_semantics() -> None:
    """Invariant 6: Completed trade is round-trip FLAT -> NONZERO -> FLAT; flip closes 1 trade and opens new trade."""
    assert COMPLETED_TRADE_DEFINITION == "ROUND_TRIP_FLAT_TO_FLAT_OR_FLIP_CLOSE"
    assert OPPOSITE_SIGNAL_FLIP_BEHAVIOR == "CLOSE_CURRENT_POSITION_OPEN_NEW_POSITION"

    # Case 1: Simple round trip (FLAT -> LONG -> FLAT) = 1 trade
    assert count_completed_trades_from_position_series([0, 100, 100, 0]) == 1

    # Case 2: Direct flip (FLAT -> LONG -> SHORT -> FLAT) = 2 trades
    # (Flip from 100 to -100 completes the LONG trade; close from -100 to 0 completes the SHORT trade)
    assert count_completed_trades_from_position_series([0, 100, -100, 0]) == 2

    # Case 3: Multiple flips (FLAT -> LONG -> SHORT -> LONG -> FLAT) = 3 trades
    assert count_completed_trades_from_position_series([0, 100, -100, 100, 0]) == 3

    # Case 4: No trades (FLAT all day) = 0 trades
    assert count_completed_trades_from_position_series([0, 0, 0, 0]) == 0


def test_7_intraday_sizing_and_no_same_direction_churn() -> None:
    """Invariant 7: Target shares are fixed for the session; repeated same-direction signals do not churn."""
    assert TARGET_SHARES_FIXED_FOR_SESSION is True
    assert SAME_DIRECTION_REPEAT_SIGNAL_BEHAVIOR == "NO_CHURN_HOLD_EXISTING"
    assert AUM_REFERENCE_POLICY == "PRIOR_DAY_ENDING_AUM"


def test_8_independent_baseline_and_stress_compounding_paths() -> None:
    """Invariant 8: Baseline and 2x stress maintain independent compounding equity paths."""
    assert BASELINE_AND_STRESS_HAVE_INDEPENDENT_AUM_PATHS is True


def test_9_excluded_session_2023_06_05_preserved() -> None:
    """Invariant 9: Session 2023-06-05 remains strictly excluded from strategy execution and performance."""
    assert EXCLUDED_SESSION_DATE == "2023-06-05"
    assert EXCLUDED_SESSION_SIGNAL_ELIGIBLE is False
    assert EXCLUDED_SESSION_TRADE_ELIGIBLE is False
    assert EXCLUDED_SESSION_PERFORMANCE_ELIGIBLE is False
    assert EXCLUDED_SESSION_VOLATILITY_ELIGIBLE is True  # Retained in daily close lineage under Outcome V1


def test_10_secondary_benchmark_governance() -> None:
    """Invariant 10: Benchmark is secondary contextual evidence only and cannot block G1-G7."""
    assert BENCHMARK_STATUS == "SECONDARY_CONTEXT_ONLY_NOT_BLOCKING"


def test_11_r2_corpus_digest_continuity() -> None:
    """Invariant 11: R2 qualified dataset digest remains unchanged."""
    manifest_path = Path("docs/phase14/manifests/manifest_r2_HYP_007.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["corpus_digests"]["r2_dataset_content_sha256"] == "4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa"


def test_12_m2_firewall_zero_access() -> None:
    """Invariant 12: M2 access is strictly locked under zero-access firewall protocol."""
    m2_dt = datetime(2024, 5, 1, 4, 0, tzinfo=timezone.utc)
    with pytest.raises(OutdatedSampleViolation, match="M2 FIREWALL VIOLATION"):
        enforce_m2_firewall(m2_dt)


def test_13_pre_r3_manifest_integrity_and_verdict() -> None:
    """Invariant 13: Pre-R3 binding manifest is sealed with SEALED_PASS and READY_FOR_SEPARATE_HUMAN_AUTHORIZATION."""
    manifest_path = Path("docs/phase14/manifests/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_001.json")
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["verdict"]["pre_r3_metric_binding"] == "SEALED_PASS"
    assert manifest["verdict"]["r3_readiness"] == "READY_FOR_SEPARATE_HUMAN_AUTHORIZATION"
    assert manifest["governance_assertions"]["strategy_signals_computed"] is False
    assert manifest["governance_assertions"]["trades_computed"] is False
    assert manifest["governance_assertions"]["pnl_observed"] is False
