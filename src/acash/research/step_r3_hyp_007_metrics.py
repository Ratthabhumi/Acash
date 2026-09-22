"""HYP_007 Step R3 Canonical Economic Metric & Accounting Definitions.

Authority:
- Zarattini, Aziz, Barbon (2024), SSRN 4824172 / Concretum Group Reference Implementation
- MEC-0015 Strategy Contract Audit & Profitability-First Intake
- MEC-0017 / HYP_007 Preregistration & Additive Governance Amendments
- Phase 14 Pre-R3 Human Authorization: AUTHORIZE_HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING

Strictly Enforces:
- Single canonical authority for simulated starting AUM ($100,000.00 accounting normalization).
- Zero capital authority ($0.00, NO_REAL_ORDERS = true).
- Daily net portfolio return formula: r_t = EndingAUM_t / EndingAUM_{t-1} - 1.
- Net total return: FinalAUM / InitialAUM - 1 (non-additive compounding).
- Annualized Sharpe: calculate_annualized_sharpe authority (252 periods, ddof=1, rf=0, fail-closed on zero variance).
- Peak-to-trough max drawdown on net end-of-day equity curve anchored at initial AUM.
- Completed trade definition: FLAT -> NONZERO -> FLAT, with directional flips (LONG <-> SHORT) closing 1 completed trade and opening 1 new trade.
- Fixed daily target shares: morning Open, prior-day AUM, and prior-day 15-day vol fix shares for the session; repeated same-direction signals do NOT churn.
- Daily AUM evolution: prior-day ending AUM determines next-day shares, zero intraday compounding.
- Independent baseline and 2x stress AUM paths.
- Excluded session 2023-06-05: 0 signal, 0 execution, 0 trade, 0 P&L, 15:59 close retained in daily close lineage under Outcome V1.
- Secondary benchmark reporting: SPY buy-and-hold does not substitute for or block G1–G7.
"""

from dataclasses import dataclass
from decimal import Decimal
import math
from typing import List, Sequence, Union

from acash.core.domain.exceptions import DataContractError
from acash.validation.deflated_sharpe import calculate_annualized_sharpe

# ---------------------------------------------------------------------------
# Starting AUM & Capital Authority Bounds
# ---------------------------------------------------------------------------

SIMULATED_STARTING_AUM_USD: Decimal = Decimal("100000.00")
SIMULATED_AUM_AUTHORITY_OUTCOME: str = "C_NO_PRIOR_VALUE_ESTABLISHED"
SIMULATED_AUM_CLASSIFICATION: str = "HUMAN_RATIFIED_PRE_RESULT_ACCOUNTING_NORMALIZATION"

REAL_CAPITAL_AUTHORITY_USD: Decimal = Decimal("0.00")
NO_REAL_ORDERS: bool = True
SEARCH_TRIAL_COUNT_K: int = 1

# ---------------------------------------------------------------------------
# Annualization & Statistical Parameters
# ---------------------------------------------------------------------------

PERIODS_PER_YEAR: int = 252
SHARPE_DDOF: int = 1
RISK_FREE_RATE: Decimal = Decimal("0.0")
SHARPE_ZERO_VARIANCE_BEHAVIOR: str = "FAIL_CLOSED_DATA_CONTRACT_ERROR"
SHARPE_AUTHORITY_FUNCTION: str = "acash.validation.deflated_sharpe.calculate_annualized_sharpe"

# ---------------------------------------------------------------------------
# Execution & Position Sizing Invariants
# ---------------------------------------------------------------------------

TARGET_SHARES_FIXED_FOR_SESSION: bool = True
SAME_DIRECTION_REPEAT_SIGNAL_BEHAVIOR: str = "NO_CHURN_HOLD_EXISTING"
OPPOSITE_SIGNAL_FLIP_BEHAVIOR: str = "CLOSE_CURRENT_POSITION_OPEN_NEW_POSITION"
COMPLETED_TRADE_DEFINITION: str = "ROUND_TRIP_FLAT_TO_FLAT_OR_FLIP_CLOSE"
BASELINE_AND_STRESS_HAVE_INDEPENDENT_AUM_PATHS: bool = True
AUM_REFERENCE_POLICY: str = "PRIOR_DAY_ENDING_AUM"

# ---------------------------------------------------------------------------
# Excluded Session Governance
# ---------------------------------------------------------------------------

EXCLUDED_SESSION_DATE: str = "2023-06-05"
EXCLUDED_SESSION_SIGNAL_ELIGIBLE: bool = False
EXCLUDED_SESSION_TRADE_ELIGIBLE: bool = False
EXCLUDED_SESSION_PERFORMANCE_ELIGIBLE: bool = False
EXCLUDED_SESSION_VOLATILITY_ELIGIBLE: bool = True  # Outcome V1: unadjusted 15:59 close retained in daily close lineage

# ---------------------------------------------------------------------------
# Benchmark Governance
# ---------------------------------------------------------------------------

BENCHMARK_STATUS: str = "SECONDARY_CONTEXT_ONLY_NOT_BLOCKING"
BENCHMARK_TOTAL_RETURN_METHODOLOGY: str = "RAW_SIP_WITH_SOVEREIGN_DIVIDEND_REINVESTMENT_OR_NOT_COMPUTED"

# ---------------------------------------------------------------------------
# Pure Calculation Functions
# ---------------------------------------------------------------------------

def calculate_daily_net_return(ending_aum_today: Decimal, prior_aum: Decimal) -> Decimal:
    """Calculate daily net portfolio return: r_t = EndingAUM_t / EndingAUM_{t-1} - 1.

    Args:
        ending_aum_today: Ending net AUM for day t (after all intraday P&L and frictions).
        prior_aum: Ending net AUM for day t-1 (or SIMULATED_STARTING_AUM_USD for t=1).

    Returns:
        Daily net return as Decimal.

    Raises:
        DataContractError: If prior_aum <= 0 or ending_aum_today <= 0.
    """
    if prior_aum <= Decimal("0.0"):
        raise DataContractError(f"Cannot compute daily net return: non-positive prior AUM {prior_aum}.")
    if ending_aum_today <= Decimal("0.0"):
        raise DataContractError(f"Cannot compute daily net return: non-positive ending AUM {ending_aum_today}.")
    return (ending_aum_today / prior_aum) - Decimal("1.0")


def calculate_net_total_return(final_aum: Decimal, initial_aum: Decimal) -> Decimal:
    """Calculate compounded net total portfolio return: FinalAUM / InitialAUM - 1.

    Args:
        final_aum: Final net AUM at end of evaluation period.
        initial_aum: Initial starting AUM (SIMULATED_STARTING_AUM_USD).

    Returns:
        Compounded net total return as Decimal.

    Raises:
        DataContractError: If initial_aum <= 0 or final_aum <= 0.
    """
    if initial_aum <= Decimal("0.0"):
        raise DataContractError(f"Cannot compute net total return: non-positive initial AUM {initial_aum}.")
    if final_aum <= Decimal("0.0"):
        raise DataContractError(f"Cannot compute net total return: non-positive final AUM {final_aum}.")
    return (final_aum / initial_aum) - Decimal("1.0")


def calculate_hyp_007_annualized_sharpe(daily_net_returns: Sequence[Union[Decimal, float]]) -> Decimal:
    """Calculate canonical annualized Sharpe ratio on daily net return series.

    Delegates strictly to single canonical authority `calculate_annualized_sharpe`
    in `acash.validation.deflated_sharpe`.

    Args:
        daily_net_returns: Sequence of per-day net simple returns.

    Returns:
        Annualized Sharpe ratio quantized to 18 decimals.

    Raises:
        DataContractError: If fewer than 2 observations, non-finite values, or zero variance.
    """
    return calculate_annualized_sharpe(daily_net_returns, periods_per_year=PERIODS_PER_YEAR)


def calculate_hyp_007_max_drawdown(net_equity_curve: Sequence[Decimal]) -> Decimal:
    """Calculate maximum peak-to-trough drawdown from net end-of-day equity curve.

    Formula:
        DD_t = 1 - Equity_t / max(Equity_0 ... Equity_t)
        MAX_DRAWDOWN = max(DD_t)

    Args:
        net_equity_curve: Sequence of net equity values starting with Initial AUM:
                          [Equity_0, Equity_1, ..., Equity_T].

    Returns:
        Maximum drawdown fraction as Decimal in [0.0, 1.0].

    Raises:
        DataContractError: If equity curve is empty or initial equity <= 0.
    """
    if not net_equity_curve:
        raise DataContractError("Cannot compute max drawdown on empty equity curve.")

    initial_eq = net_equity_curve[0]
    if initial_eq <= Decimal("0.0"):
        raise DataContractError(f"Cannot compute max drawdown: initial equity {initial_eq} <= 0.")

    peak = initial_eq
    max_dd = Decimal("0.0")

    for eq in net_equity_curve:
        if eq <= Decimal("0.0"):
            # Total ruin
            return Decimal("1.0")
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd

    return max_dd


def count_completed_trades_from_position_series(positions: Sequence[int]) -> int:
    """Count completed round-trip trades from a discrete sequence of position states.

    Position states are integer share counts (positive for LONG, negative for SHORT, 0 for FLAT).
    A completed trade is defined as:
    1. Transition from NONZERO to FLAT: closes 1 trade.
    2. Direct directional flip (positive -> negative or negative -> positive):
       closes the existing trade (1 completed trade) and opens a new trade.

    Args:
        positions: Sequence of position states (must start and end with FLAT / 0 for clean evaluation).

    Returns:
        Total count of completed trade episodes.
    """
    if not positions:
        return 0

    completed_trades = 0
    current_pos = positions[0]

    for next_pos in positions[1:]:
        if current_pos != 0:
            if next_pos == 0:
                # Closed position to flat
                completed_trades += 1
            elif (current_pos > 0 and next_pos < 0) or (current_pos < 0 and next_pos > 0):
                # Directional flip: closes existing trade, begins new trade
                completed_trades += 1
        current_pos = next_pos

    return completed_trades


# ---------------------------------------------------------------------------
# Canonical HYP_007 Acceptance Gates Authority (Sovereign R1 Preregistration)
# ---------------------------------------------------------------------------

G1_NET_TOTAL_RETURN_MIN_EXCLUSIVE: Decimal = Decimal("0.0")
G2_NET_SHARPE_MIN: Decimal = Decimal("1.00")
G3_MAX_DRAWDOWN_MAX: Decimal = Decimal("0.30")
G4_COMPLETED_TRADES_MIN: int = 100
G5_REQUIRE_NO_MATERIAL_CONTRACT_FAILURE: bool = True
G6_STRESS_NET_RETURN_MIN_EXCLUSIVE: Decimal = Decimal("0.0")
G7_STRESS_NET_SHARPE_MIN: Decimal = Decimal("0.75")


@dataclass(frozen=True)
class GateEvaluationResult:
    passed: bool
    gate_id: str
    metric_name: str
    observed_value: Union[Decimal, int, bool]
    threshold_value: Union[Decimal, int, bool]
    comparison_operator: str


@dataclass(frozen=True)
class Hyp007M1AcceptanceReport:
    all_passed: bool
    g1: GateEvaluationResult
    g2: GateEvaluationResult
    g3: GateEvaluationResult
    g4: GateEvaluationResult
    g5: GateEvaluationResult
    g6: GateEvaluationResult
    g7: GateEvaluationResult
    rejection_reasons: List[str]


def evaluate_hyp_007_m1_acceptance_gates(
    net_total_return: Decimal,
    net_annualized_sharpe: Decimal,
    max_drawdown: Decimal,
    completed_trades: int,
    no_material_contract_failure: bool,
    stress_net_return: Decimal,
    stress_net_sharpe: Decimal,
) -> Hyp007M1AcceptanceReport:
    """Evaluate the 7 sovereign HYP_007 M1 acceptance criteria fail-closed.

    Authority: docs/research/MEC-0017-HYP-007-strategy-preregistration.md Section 10
    and docs/phase14/hypotheses/HYP_007.json.
    All 7 gates must pass simultaneously (zero scoring, zero partial pass).
    """
    rejection_reasons: List[str] = []

    # G1: Net Total Return > 0.0
    g1_pass = net_total_return > G1_NET_TOTAL_RETURN_MIN_EXCLUSIVE
    if not g1_pass:
        rejection_reasons.append(f"G1_FAIL: Net total return {net_total_return} <= {G1_NET_TOTAL_RETURN_MIN_EXCLUSIVE}")
    g1 = GateEvaluationResult(
        passed=g1_pass,
        gate_id="G1",
        metric_name="NET_TOTAL_RETURN",
        observed_value=net_total_return,
        threshold_value=G1_NET_TOTAL_RETURN_MIN_EXCLUSIVE,
        comparison_operator=">",
    )

    # G2: Net Annualized Sharpe >= 1.00
    g2_pass = net_annualized_sharpe >= G2_NET_SHARPE_MIN
    if not g2_pass:
        rejection_reasons.append(f"G2_FAIL: Net Sharpe {net_annualized_sharpe} < {G2_NET_SHARPE_MIN}")
    g2 = GateEvaluationResult(
        passed=g2_pass,
        gate_id="G2",
        metric_name="NET_ANNUALIZED_SHARPE",
        observed_value=net_annualized_sharpe,
        threshold_value=G2_NET_SHARPE_MIN,
        comparison_operator=">=",
    )

    # G3: Max Drawdown <= 30.0% (0.30)
    g3_pass = max_drawdown <= G3_MAX_DRAWDOWN_MAX
    if not g3_pass:
        rejection_reasons.append(f"G3_FAIL: Max drawdown {max_drawdown} > {G3_MAX_DRAWDOWN_MAX}")
    g3 = GateEvaluationResult(
        passed=g3_pass,
        gate_id="G3",
        metric_name="MAX_DRAWDOWN",
        observed_value=max_drawdown,
        threshold_value=G3_MAX_DRAWDOWN_MAX,
        comparison_operator="<=",
    )

    # G4: Completed Trades >= 100
    g4_pass = completed_trades >= G4_COMPLETED_TRADES_MIN
    if not g4_pass:
        rejection_reasons.append(f"G4_FAIL: Completed trades {completed_trades} < {G4_COMPLETED_TRADES_MIN}")
    g4 = GateEvaluationResult(
        passed=g4_pass,
        gate_id="G4",
        metric_name="COMPLETED_TRADES",
        observed_value=completed_trades,
        threshold_value=G4_COMPLETED_TRADES_MIN,
        comparison_operator=">=",
    )

    # G5: No Material Contract Failure == True
    g5_pass = no_material_contract_failure is G5_REQUIRE_NO_MATERIAL_CONTRACT_FAILURE
    if not g5_pass:
        rejection_reasons.append("G5_FAIL: Material contract failure detected")
    g5 = GateEvaluationResult(
        passed=g5_pass,
        gate_id="G5",
        metric_name="NO_MATERIAL_CONTRACT_FAILURE",
        observed_value=no_material_contract_failure,
        threshold_value=G5_REQUIRE_NO_MATERIAL_CONTRACT_FAILURE,
        comparison_operator="==",
    )

    # G6: 2x Friction Stress Net Return > 0.0
    g6_pass = stress_net_return > G6_STRESS_NET_RETURN_MIN_EXCLUSIVE
    if not g6_pass:
        rejection_reasons.append(f"G6_FAIL: Stress net return {stress_net_return} <= {G6_STRESS_NET_RETURN_MIN_EXCLUSIVE}")
    g6 = GateEvaluationResult(
        passed=g6_pass,
        gate_id="G6",
        metric_name="2X_FRICTION_STRESS_NET_RETURN",
        observed_value=stress_net_return,
        threshold_value=G6_STRESS_NET_RETURN_MIN_EXCLUSIVE,
        comparison_operator=">",
    )

    # G7: 2x Friction Stress Net Sharpe >= 0.75
    g7_pass = stress_net_sharpe >= G7_STRESS_NET_SHARPE_MIN
    if not g7_pass:
        rejection_reasons.append(f"G7_FAIL: Stress Sharpe {stress_net_sharpe} < {G7_STRESS_NET_SHARPE_MIN}")
    g7 = GateEvaluationResult(
        passed=g7_pass,
        gate_id="G7",
        metric_name="2X_FRICTION_STRESS_NET_SHARPE",
        observed_value=stress_net_sharpe,
        threshold_value=G7_STRESS_NET_SHARPE_MIN,
        comparison_operator=">=",
    )

    all_passed = g1_pass and g2_pass and g3_pass and g4_pass and g5_pass and g6_pass and g7_pass

    return Hyp007M1AcceptanceReport(
        all_passed=all_passed,
        g1=g1,
        g2=g2,
        g3=g3,
        g4=g4,
        g5=g5,
        g6=g6,
        g7=g7,
        rejection_reasons=rejection_reasons,
    )
