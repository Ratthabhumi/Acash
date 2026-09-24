"""Frozen G1-G6 evaluation (R1 gate contract). No rounding before evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Tuple

# Frozen R1 authority pins (tested byte-equal against manifest_r1_HYP_009.json).
FROZEN_PROVIDER_CONTRACT_HASH: str = (
    "1ed9892b4871a9c430b0770f6f691244661dec5257059dda9af5effb94ae55d6"
)
FROZEN_REQUEST_SYMBOL: str = "SPY"
FROZEN_REQUEST_FEED: str = "sip"
FROZEN_REQUEST_TIMEFRAME: str = "1Day"
FROZEN_NO_SPLIT_DETERMINATION: str = "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"


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
class ContractQualificationEvidence:
    """Concrete measured qualification values (no pre-computed booleans).

    Carries observed measurements plus independently-read authority pins; the
    frozen expectations live in module constants / partitions.py and are
    compared inside derive_contract_qualification.
    """

    provider_contract_hash_recomputed: str
    provider_contract_hash_authority: str
    request_symbol: str
    request_feed: str
    request_timeframe: str
    request_start: date
    request_end: date
    partition: str
    expected_sessions: Tuple[date, ...]
    split_sessions: Tuple[date, ...]
    raw_sessions: Tuple[date, ...]
    dividend_validated_count: int
    dividend_missing_payable_count: int
    split_determination: str
    page_shas_recorded: Tuple[str, ...]
    page_shas_recomputed: Tuple[str, ...]
    sealed_hash_pairs: Tuple[Tuple[str, str], ...]
    forbidden_access_counts: Tuple[int, int, int, int]


def derive_contract_qualification(
    evidence: ContractQualificationEvidence,
) -> ContractQualification:
    """Derive all ten flags by comparing evidence against frozen authority."""
    from acash.research.hyp_009 import partitions as part

    if evidence.partition == "M1":
        fetch_window = (part.AUTHORIZED_MIN_DATE, part.AUTHORIZED_MAX_DATE)
    elif evidence.partition == "M2":
        fetch_window = (part.M2_START, part.M2_END)
    else:
        raise ValueError(f"UNKNOWN_PARTITION: {evidence.partition}.")
    fetch_start, fetch_end = fetch_window
    window_start, window_end = fetch_start, fetch_end

    provider_pass = (
        evidence.provider_contract_hash_recomputed
        == evidence.provider_contract_hash_authority
        == FROZEN_PROVIDER_CONTRACT_HASH
        and evidence.request_symbol == FROZEN_REQUEST_SYMBOL
        and evidence.request_feed == FROZEN_REQUEST_FEED
        and evidence.request_timeframe == FROZEN_REQUEST_TIMEFRAME
        and evidence.request_start == fetch_start
        and evidence.request_end == fetch_end
    )
    expected_ordered = (
        len(evidence.expected_sessions) > 0
        and tuple(evidence.expected_sessions)
        == tuple(sorted(set(evidence.expected_sessions)))
    )
    coverage_pass = (
        expected_ordered
        and evidence.split_sessions == evidence.expected_sessions
        and evidence.raw_sessions == evidence.expected_sessions
    )
    alignment_pass = (
        len(evidence.split_sessions) > 0
        and evidence.split_sessions == evidence.raw_sessions
    )
    dividend_pass = (
        evidence.dividend_validated_count > 0
        and evidence.dividend_missing_payable_count == 0
    )
    payable_pass = evidence.dividend_missing_payable_count == 0
    split_pass = (
        evidence.split_determination == FROZEN_NO_SPLIT_DETERMINATION
    )
    scope_pass = (
        len(evidence.split_sessions) > 0
        and all(window_start <= s <= window_end for s in evidence.split_sessions)
        and all(window_start <= s <= window_end for s in evidence.raw_sessions)
    )
    provenance_pass = (
        len(evidence.page_shas_recorded) > 0
        and evidence.page_shas_recorded == evidence.page_shas_recomputed
    )
    serialization_pass = (
        len(evidence.sealed_hash_pairs) > 0
        and all(pinned == recomputed for pinned, recomputed in evidence.sealed_hash_pairs)
    )
    forbidden_pass = (
        len(evidence.forbidden_access_counts) == 4
        and all(count == 0 for count in evidence.forbidden_access_counts)
    )
    return ContractQualification(
        provider_contract_pass=provider_pass,
        calendar_coverage_pass=coverage_pass,
        split_raw_alignment_pass=alignment_pass,
        dividend_contract_pass=dividend_pass,
        payable_date_contract_pass=payable_pass,
        split_contract_pass=split_pass,
        response_scope_pass=scope_pass,
        provenance_hash_pass=provenance_pass,
        serialization_integrity_pass=serialization_pass,
        forbidden_partition_access_zero=forbidden_pass,
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


def classify_m2_verdict(outcome: GateOutcome, contract_valid: bool) -> str:
    """M2 verdict labels (§15): M2 failure is FAIL_CORE_EDGE, never M1's label."""
    if not contract_valid:
        return "BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT"
    if outcome.conjunction:
        return "M2_SUPPORTED_FOR_RECENT_STRESS_CONSIDERATION"
    return "FAIL_CORE_EDGE_NOT_SUPPORTED"
