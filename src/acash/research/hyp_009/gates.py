"""Frozen G1-G6 evaluation (R1 gate contract). No rounding before evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ContractQualification:
    """Explicit M1 material-contract qualification state (G6 authority).

    Every flag must be derived from observed qualification outcomes — never
    injected as a literal. G6 is True only when ALL flags hold.
    """

    provider_contract_pass: bool
    calendar_coverage_pass: bool
    split_raw_alignment_pass: bool
    dividend_contract_pass: bool
    payable_date_contract_pass: bool
    split_contract_pass: bool
    response_scope_pass: bool
    provenance_hash_pass: bool
    serialization_integrity_pass: bool
    forbidden_partition_access_zero: bool

    @property
    def no_material_failure(self) -> bool:
        return all(
            [
                self.provider_contract_pass,
                self.calendar_coverage_pass,
                self.split_raw_alignment_pass,
                self.dividend_contract_pass,
                self.payable_date_contract_pass,
                self.split_contract_pass,
                self.response_scope_pass,
                self.provenance_hash_pass,
                self.serialization_integrity_pass,
                self.forbidden_partition_access_zero,
            ]
        )


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
