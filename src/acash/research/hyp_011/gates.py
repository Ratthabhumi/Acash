"""HYP_011 evidence-derived G6 and frozen verdicts (G1-G6 operators reused)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Tuple

from acash.research.hyp_009.gates import (
    GateInputs,
    GateOutcome,
    classify_m1_verdict,
    evaluate_gates,
)
from acash.research.hyp_011 import partitions as part

FROZEN_PROVIDER_CONTRACT_HASH: str = (
    "fc2f1e7525d9cb69e74ac4d1464acab4b4855ee2e0e4ed72208f2591af749edc"
)
FROZEN_REQUEST_SYMBOLS = ("ACWI", "AGG", "SPY")
FROZEN_REQUEST_FEED: str = "sip"
FROZEN_REQUEST_TIMEFRAME: str = "1Day"


@dataclass(frozen=True)
class HYP011ContractQualificationEvidence:
    """Concrete measured qualification values (no pre-computed booleans)."""

    provider_contract_hash_recomputed: str
    provider_contract_hash_authority: str
    request_symbols: Tuple[str, ...]
    request_feed: str
    request_timeframe: str
    request_start: date
    request_end: date
    expected_sessions: Tuple[date, ...]
    sessions_by_series: Tuple[Tuple[str, ...], ...]
    dividend_validated_counts: Tuple[int, ...]
    dividend_missing_payable_counts: Tuple[int, ...]
    split_determinations: Tuple[str, ...]
    page_shas_recorded: Tuple[str, ...]
    page_shas_recomputed: Tuple[str, ...]
    sealed_hash_pairs: Tuple[Tuple[str, str], ...]
    expected_rebalance_sessions: Tuple[date, ...]
    actual_rebalance_sessions: Tuple[date, ...]
    fee_authority_resolved: bool
    whole_share_integral: bool
    cash_never_negative: bool
    leverage_never_above_one: bool
    dividends_processed_count: int
    dividends_authority_count: int
    forbidden_access_counts: Tuple[int, int, int, int]


@dataclass(frozen=True)
class HYP011ContractQualification:
    provider_contract_pass: bool
    calendar_coverage_pass: bool
    series_alignment_pass: bool
    dividend_contract_pass: bool
    payable_date_contract_pass: bool
    split_contract_pass: bool
    response_scope_pass: bool
    provenance_hash_pass: bool
    serialization_integrity_pass: bool
    rebalance_schedule_pass: bool
    fee_authority_pass: bool
    accounting_invariants_pass: bool
    forbidden_partition_access_zero: bool

    @property
    def no_material_failure(self) -> bool:
        return all(
            [
                self.provider_contract_pass,
                self.calendar_coverage_pass,
                self.series_alignment_pass,
                self.dividend_contract_pass,
                self.payable_date_contract_pass,
                self.split_contract_pass,
                self.response_scope_pass,
                self.provenance_hash_pass,
                self.serialization_integrity_pass,
                self.rebalance_schedule_pass,
                self.fee_authority_pass,
                self.accounting_invariants_pass,
                self.forbidden_partition_access_zero,
            ]
        )


def derive_contract_qualification(
    evidence: HYP011ContractQualificationEvidence,
) -> HYP011ContractQualification:
    sessions_ok = (
        len(evidence.expected_sessions) > 0
        and tuple(evidence.expected_sessions)
        == tuple(sorted(set(evidence.expected_sessions)))
    )
    series_ok = (
        len(evidence.sessions_by_series) == 6
        and all(tuple(s) == evidence.expected_sessions for s in evidence.sessions_by_series)
    )
    return HYP011ContractQualification(
        provider_contract_pass=(
            evidence.provider_contract_hash_recomputed
            == evidence.provider_contract_hash_authority
            == FROZEN_PROVIDER_CONTRACT_HASH
            and tuple(evidence.request_symbols) == FROZEN_REQUEST_SYMBOLS
            and evidence.request_feed == FROZEN_REQUEST_FEED
            and evidence.request_timeframe == FROZEN_REQUEST_TIMEFRAME
            and evidence.request_start == part.HISTORICAL_START
            and evidence.request_end == part.HISTORICAL_END
        ),
        calendar_coverage_pass=sessions_ok,
        series_alignment_pass=sessions_ok and series_ok,
        dividend_contract_pass=(
            all(c > 0 for c in evidence.dividend_validated_counts)
            and all(c == 0 for c in evidence.dividend_missing_payable_counts)
        ),
        payable_date_contract_pass=all(
            c == 0 for c in evidence.dividend_missing_payable_counts
        ),
        split_contract_pass=all(
            d == "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"
            for d in evidence.split_determinations
        ),
        response_scope_pass=sessions_ok and series_ok,
        provenance_hash_pass=(
            len(evidence.page_shas_recorded) > 0
            and evidence.page_shas_recorded == evidence.page_shas_recomputed
        ),
        serialization_integrity_pass=(
            len(evidence.sealed_hash_pairs) > 0
            and all(p == r for p, r in evidence.sealed_hash_pairs)
        ),
        rebalance_schedule_pass=(
            len(evidence.expected_rebalance_sessions) == 9
            and evidence.actual_rebalance_sessions == evidence.expected_rebalance_sessions
        ),
        fee_authority_pass=evidence.fee_authority_resolved,
        accounting_invariants_pass=(
            evidence.whole_share_integral
            and evidence.cash_never_negative
            and evidence.leverage_never_above_one
            and evidence.dividends_processed_count == evidence.dividends_authority_count
            and evidence.dividends_processed_count > 0
        ),
        forbidden_partition_access_zero=(
            len(evidence.forbidden_access_counts) == 4
            and all(c == 0 for c in evidence.forbidden_access_counts)
        ),
    )


def classify_historical_verdict(outcome: GateOutcome, contract_valid: bool) -> str:
    if not contract_valid:
        return "BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT"
    if outcome.conjunction:
        return "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW"
    return "HISTORICAL_REPLICATION_NOT_SUPPORTED_NO_PROSPECTIVE_AUTHORIZATION"


__all__ = [
    "GateInputs",
    "GateOutcome",
    "HYP011ContractQualificationEvidence",
    "HYP011ContractQualification",
    "classify_historical_verdict",
    "classify_m1_verdict",
    "derive_contract_qualification",
    "evaluate_gates",
]
