"""Unit tests and boundary invariant verifications for HYP_007 Pre-R3 Acceptance Gate Reconciliation.

Governed by:
- AUTHORIZE_HYP_007_PRE_R3_GATE_RECONCILIATION_002
- docs/phase14/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_CORRECTION_002.md
- docs/phase14/manifests/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_CORRECTION_002.json
- docs/research/MEC-0017-HYP-007-strategy-preregistration.md Section 10
"""

from decimal import Decimal
import json
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.step_r3_hyp_007_metrics import (
    G1_NET_TOTAL_RETURN_MIN_EXCLUSIVE,
    G2_NET_SHARPE_MIN,
    G3_MAX_DRAWDOWN_MAX,
    G4_COMPLETED_TRADES_MIN,
    G5_REQUIRE_NO_MATERIAL_CONTRACT_FAILURE,
    G6_STRESS_NET_RETURN_MIN_EXCLUSIVE,
    G7_STRESS_NET_SHARPE_MIN,
    NO_REAL_ORDERS,
    REAL_CAPITAL_AUTHORITY_USD,
    calculate_hyp_007_annualized_sharpe,
    evaluate_hyp_007_m1_acceptance_gates,
)


def test_1_canonical_gate_threshold_constants() -> None:
    """Invariant 1: Acceptance gate constants match sovereign R1 preregistration exactly."""
    assert G1_NET_TOTAL_RETURN_MIN_EXCLUSIVE == Decimal("0.0")
    assert G2_NET_SHARPE_MIN == Decimal("1.00")
    assert G3_MAX_DRAWDOWN_MAX == Decimal("0.30")
    assert G4_COMPLETED_TRADES_MIN == 100
    assert G5_REQUIRE_NO_MATERIAL_CONTRACT_FAILURE is True
    assert G6_STRESS_NET_RETURN_MIN_EXCLUSIVE == Decimal("0.0")
    assert G7_STRESS_NET_SHARPE_MIN == Decimal("0.75")


def test_2_synthetic_boundary_g1_net_total_return() -> None:
    """Invariant 2: G1 threshold strictly requires Net Total Return > 0.0."""
    # Passing boundary: +0.000001
    r_pass = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.000001"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.000001"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_pass.g1.passed is True
    assert r_pass.all_passed is True

    # Failing boundary: exactly 0.0 (strictly exclusive)
    r_fail = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.0"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.000001"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_fail.g1.passed is False
    assert r_fail.all_passed is False
    assert any("G1_FAIL" in msg for msg in r_fail.rejection_reasons)


def test_3_synthetic_boundary_g2_net_annualized_sharpe() -> None:
    """Invariant 3: G2 threshold strictly requires Net Annualized Sharpe >= 1.00."""
    # Passing boundary: 1.00
    r_pass = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_pass.g2.passed is True
    assert r_pass.all_passed is True

    # Failing boundary: 0.999999
    r_fail = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("0.999999"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_fail.g2.passed is False
    assert r_fail.all_passed is False
    assert any("G2_FAIL" in msg for msg in r_fail.rejection_reasons)


def test_4_synthetic_boundary_g3_max_drawdown() -> None:
    """Invariant 4: G3 threshold strictly requires Max Drawdown <= 30.0% (0.30)."""
    # Passing boundary: exactly 0.30
    r_pass = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_pass.g3.passed is True
    assert r_pass.all_passed is True

    # Failing boundary: 0.300001
    r_fail = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.300001"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_fail.g3.passed is False
    assert r_fail.all_passed is False
    assert any("G3_FAIL" in msg for msg in r_fail.rejection_reasons)


def test_5_synthetic_boundary_g4_completed_trades() -> None:
    """Invariant 5: G4 threshold strictly requires Completed Trades >= 100."""
    # Passing boundary: 100
    r_pass = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_pass.g4.passed is True
    assert r_pass.all_passed is True

    # Failing boundary: 99
    r_fail = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=99,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_fail.g4.passed is False
    assert r_fail.all_passed is False
    assert any("G4_FAIL" in msg for msg in r_fail.rejection_reasons)


def test_6_synthetic_boundary_g5_no_material_contract_failure() -> None:
    """Invariant 6: G5 threshold strictly requires No Material Contract Failure == True."""
    # Passing: True
    r_pass = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_pass.g5.passed is True
    assert r_pass.all_passed is True

    # Failing: False
    r_fail = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=False,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_fail.g5.passed is False
    assert r_fail.all_passed is False
    assert any("G5_FAIL" in msg for msg in r_fail.rejection_reasons)


def test_7_synthetic_boundary_g6_stress_net_return() -> None:
    """Invariant 7: G6 threshold strictly requires 2x Stress Net Return > 0.0."""
    # Passing: +0.000001
    r_pass = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.000001"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_pass.g6.passed is True
    assert r_pass.all_passed is True

    # Failing: exactly 0.0
    r_fail = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.0"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_fail.g6.passed is False
    assert r_fail.all_passed is False
    assert any("G6_FAIL" in msg for msg in r_fail.rejection_reasons)


def test_8_synthetic_boundary_g7_stress_net_sharpe() -> None:
    """Invariant 8: G7 threshold strictly requires 2x Stress Net Sharpe >= 0.75."""
    # Passing boundary: 0.75
    r_pass = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.75"),
    )
    assert r_pass.g7.passed is True
    assert r_pass.all_passed is True

    # Failing boundary: 0.749999
    r_fail = evaluate_hyp_007_m1_acceptance_gates(
        net_total_return=Decimal("0.01"),
        net_annualized_sharpe=Decimal("1.00"),
        max_drawdown=Decimal("0.30"),
        completed_trades=100,
        no_material_contract_failure=True,
        stress_net_return=Decimal("0.01"),
        stress_net_sharpe=Decimal("0.749999"),
    )
    assert r_fail.g7.passed is False
    assert r_fail.all_passed is False
    assert any("G7_FAIL" in msg for msg in r_fail.rejection_reasons)


def test_9_all_seven_gates_conjunction_no_partial_pass() -> None:
    """Invariant 9: All 7 gates must pass simultaneously; any single failure causes terminal failure."""
    def run_eval(
        r: Decimal = Decimal("0.05"),
        sr: Decimal = Decimal("1.25"),
        dd: Decimal = Decimal("0.15"),
        trades: int = 150,
        no_fail: bool = True,
        s_r: Decimal = Decimal("0.02"),
        s_sr: Decimal = Decimal("0.85"),
    ) -> bool:
        return evaluate_hyp_007_m1_acceptance_gates(
            net_total_return=r,
            net_annualized_sharpe=sr,
            max_drawdown=dd,
            completed_trades=trades,
            no_material_contract_failure=no_fail,
            stress_net_return=s_r,
            stress_net_sharpe=s_sr,
        ).all_passed

    # All pass
    assert run_eval() is True

    # Break G1
    assert run_eval(r=Decimal("-0.01")) is False
    # Break G2
    assert run_eval(sr=Decimal("0.80")) is False
    # Break G3
    assert run_eval(dd=Decimal("0.35")) is False
    # Break G4
    assert run_eval(trades=50) is False
    # Break G5
    assert run_eval(no_fail=False) is False
    # Break G6
    assert run_eval(s_r=Decimal("-0.005")) is False
    # Break G7
    assert run_eval(s_sr=Decimal("0.60")) is False


def test_10_sharpe_zero_variance_audit() -> None:
    """Invariant 10: calculate_annualized_sharpe strictly raises DataContractError on zero variance."""
    # Flat return series has zero sample std
    flat_returns = [Decimal("0.005")] * 20
    with pytest.raises(DataContractError, match="zero-variance return series"):
        calculate_hyp_007_annualized_sharpe(flat_returns)


def test_11_correction_002_manifest_integrity() -> None:
    """Invariant 11: Correction 002 manifest is valid and correctly reconciles G3 and G7."""
    manifest_path = Path("docs/phase14/manifests/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_CORRECTION_002.json")
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["defect_reconciliation"]["effective_g3_reconciled"] == "<= 30.0% (0.30)"
    assert data["defect_reconciliation"]["effective_g7_reconciled"] == ">= 0.75"
    assert data["authoritative_acceptance_gates"]["G3"] == "MAX_DRAWDOWN <= 0.30"
    assert data["authoritative_acceptance_gates"]["G7"] == "2X_FRICTION_STRESS_NET_SHARPE >= 0.75"
    assert data["verdict"]["pre_r3_gate_reconciliation"] == "SEALED_PASS"
    assert data["verdict"]["r3_readiness"] == "READY_FOR_SEPARATE_HUMAN_AUTHORIZATION"
    assert REAL_CAPITAL_AUTHORITY_USD == Decimal("0.00")
    assert NO_REAL_ORDERS is True
