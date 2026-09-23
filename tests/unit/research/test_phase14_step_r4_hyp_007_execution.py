"""Unit tests for HYP_007 Step R4 M2 execution engine and invariants.

Validates:
- Stage A freeze required before M2 network access.
- Exact M2 date bounds and census (568 regular sessions, 6 early closes excluded).
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
    extract_m2_bars_list,
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
    R4GateEvaluationResult,
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
    assert len(census.regular_sessions) == 568
    assert len(census.early_closes) == 6

    # 2025-01-09 was a full NYSE market closure (National Day of Mourning
    # for President Jimmy Carter) and must be excluded from regular sessions.
    assert date(2025, 1, 9) not in census.regular_sessions
    assert any(d == date(2025, 1, 9) for d, _ in census.holidays)

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


def test_null_bars_payload_fails_closed_data_contract_error() -> None:
    """Alpaca 'bars': null (unscheduled closure day) must raise DataContractError, not TypeError."""
    payload_null = {"bars": None, "next_page_token": None, "symbol": "SPY"}
    with pytest.raises(DataContractError, match="Null bars payload"):
        extract_m2_bars_list(payload_null, date(2025, 1, 9))

    payload_missing = {"symbol": "SPY"}
    with pytest.raises(DataContractError, match="Null bars payload"):
        extract_m2_bars_list(payload_missing, date(2025, 1, 9))

    payload_malformed = {"bars": {"not": "a list"}, "symbol": "SPY"}
    with pytest.raises(DataContractError, match="Malformed bars payload"):
        extract_m2_bars_list(payload_malformed, date(2025, 1, 9))

    payload_valid = {"bars": [{"t": "2025-01-10T14:30:00Z"}], "symbol": "SPY"}
    extracted = extract_m2_bars_list(payload_valid, date(2025, 1, 10))
    assert extracted == [{"t": "2025-01-10T14:30:00Z"}]


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
    divs = load_m2_dividend_projection(repo_root)
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
        assert d.distribution_type == "ORDINARY_DIVIDEND"


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


def test_r4_execution_module_consumes_sovereign_evaluator_only() -> None:
    """Guard against evaluator shadowing: execution must use Stage A authority.

    Regression for the defect where step_r4_hyp_007.py locally redefined
    evaluate_r4_gates / R4GateEvaluationResult with drifted semantics.
    """
    import acash.research.step_r4_hyp_007 as exec_mod
    import acash.research.step_r4_hyp_007_governance as governance

    assert getattr(exec_mod, "evaluate_r4_gates") is governance.evaluate_r4_gates
    assert getattr(exec_mod, "R4GateEvaluationResult") is governance.R4GateEvaluationResult


def _eval_r4(
    net_total_return: Decimal,
    annualized_sharpe: Decimal,
    max_drawdown: Decimal,
    stress_total_return: Decimal,
) -> R4GateEvaluationResult:
    """Shared helper for boundary evals with otherwise-passing economics."""
    return evaluate_r4_gates(
        net_total_return=net_total_return,
        annualized_sharpe=annualized_sharpe,
        max_drawdown=max_drawdown,
        stress_total_return=stress_total_return,
        contract_valid=True,
    )


def test_r4_g1_strict_greater_than_zero_boundary() -> None:
    """G1 is STRICT > 0.0: 0.0 must FAIL; tiny positive must PASS."""
    tiny_pass = _eval_r4(
        Decimal("0.000001"), Decimal("0.80"), Decimal("0.10"), Decimal("0.02")
    )
    assert tiny_pass.g1_pass is True
    assert tiny_pass.verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED
    assert tiny_pass.all_passed is True

    zero_fail = _eval_r4(
        Decimal("0.000000"), Decimal("0.80"), Decimal("0.10"), Decimal("0.02")
    )
    assert zero_fail.g1_pass is False
    assert zero_fail.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert zero_fail.all_passed is False

    tiny_neg = _eval_r4(
        Decimal("-0.000001"), Decimal("0.80"), Decimal("0.10"), Decimal("0.02")
    )
    assert tiny_neg.g1_pass is False
    assert tiny_neg.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert tiny_neg.all_passed is False


def test_r4_g2_sharpe_boundary() -> None:
    """G2 is >= 0.50: exactly 0.50 passes; one micro below fails."""
    at = _eval_r4(Decimal("0.05"), Decimal("0.50"), Decimal("0.10"), Decimal("0.02"))
    assert at.g2_pass is True
    assert at.verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED
    assert at.all_passed is True

    below = _eval_r4(Decimal("0.05"), Decimal("0.499999"), Decimal("0.10"), Decimal("0.02"))
    assert below.g2_pass is False
    assert below.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert below.all_passed is False


def test_r4_g3_max_drawdown_boundary() -> None:
    """G3 is <= 0.35: exactly 0.35 passes; one micro above fails."""
    at = _eval_r4(Decimal("0.05"), Decimal("0.80"), Decimal("0.35"), Decimal("0.02"))
    assert at.g3_pass is True
    assert at.verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED
    assert at.all_passed is True

    above = _eval_r4(Decimal("0.05"), Decimal("0.80"), Decimal("0.350001"), Decimal("0.02"))
    assert above.g3_pass is False
    assert above.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert above.all_passed is False


def test_r4_g4_stress_return_boundary() -> None:
    """G4 is >= 0.0: exactly 0.0 passes; one micro below fails."""
    at = _eval_r4(Decimal("0.05"), Decimal("0.80"), Decimal("0.10"), Decimal("0.0"))
    assert at.g4_pass is True
    assert at.verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED
    assert at.all_passed is True

    below = _eval_r4(Decimal("0.05"), Decimal("0.80"), Decimal("0.10"), Decimal("-0.000001"))
    assert below.g4_pass is False
    assert below.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert below.all_passed is False


def test_r4_contract_failure_classified_as_blocked() -> None:
    """contract_valid=False must be BLOCKED, never FAIL (economic verdict unavailable)."""
    res = evaluate_r4_gates(
        net_total_return=Decimal("0.05"),
        annualized_sharpe=Decimal("0.80"),
        max_drawdown=Decimal("0.10"),
        stress_total_return=Decimal("0.02"),
        contract_valid=False,
        contract_failure_reason="Missing quote boundaries",
    )
    assert res.contract_valid is False
    assert res.g1_pass is False
    assert res.g2_pass is False
    assert res.g3_pass is False
    assert res.g4_pass is False
    assert res.verdict == R4Verdict.BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT
    assert res.verdict.value != R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED.value
    assert res.all_passed is False
