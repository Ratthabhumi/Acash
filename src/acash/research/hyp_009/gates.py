"""Frozen G1-G6 evaluation (R1 gate contract). No rounding before evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GateInputs:
    baseline_net_total_return: Decimal
    baseline_net_annualized_sharpe: Decimal
    baseline_max_drawdown: Decimal
    benchmark_max_drawdown: Decimal
    stress_net_total_return: Decimal
    no_material_contract_failure: bool


@dataclass(frozen=True)
class GateOutcome:
    g1: bool
    g2: bool
    g3: bool
    g4: bool
    g5: bool
    g6: bool

    @property
    def conjunction(self) -> bool:
        return self.g1 and self.g2 and self.g3 and self.g4 and self.g5 and self.g6


def evaluate_gates(inputs: GateInputs) -> GateOutcome:
    """Exact frozen operators: G1 >0; G2 >=0.50; G3 <=0.35; G4 strict <; G5 >0; G6 True."""
    return GateOutcome(
        g1=inputs.baseline_net_total_return > Decimal("0"),
        g2=inputs.baseline_net_annualized_sharpe >= Decimal("0.50"),
        g3=inputs.baseline_max_drawdown <= Decimal("0.35"),
        g4=inputs.baseline_max_drawdown < inputs.benchmark_max_drawdown,
        g5=inputs.stress_net_total_return > Decimal("0"),
        g6=inputs.no_material_contract_failure is True,
    )


def classify_m1_verdict(outcome: GateOutcome, contract_valid: bool) -> str:
    if not contract_valid:
        return "BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT"
    if outcome.conjunction:
        return "M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION"
    return "M1_NOT_SUPPORTED_NO_M2_AUTHORIZATION"
