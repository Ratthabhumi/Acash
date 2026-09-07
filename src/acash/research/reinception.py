"""Phase 8.5 Research Governance: Research Re-Inception Gate & Pre-Registration Validation.

Strictly enforces:
1. R1 Entry Control Only:
   This gate governs the transition from STANDING BY to RESEARCH INCEPTION (R1).
   It does NOT load market data, execute backtests, or evaluate alphas.
2. New Immutable Hypothesis Identity:
   Cannot reuse TERMINALLY_FALSIFIED hypothesis IDs (e.g., HYP_TSMOM_EURUSD_001).
   Cannot mutate existing sealed hypothesis specifications.
3. Declarative Data Contract:
   Data windows and partitions are declared as metadata; actual dataset acquisition belongs to R2.
   Zero Parquet/CSV file loading is performed in this module.
4. Search Space Cardinal Equality (Anti-HARKing):
   planned_trial_count MUST strictly equal the combinatorial cardinality of the declared parameter grid.
5. Governance Exception Integrity:
   Quarantined data windows cannot pass with just an exception ID string; the referenced
   GovernanceExceptionRecord must exist, be cryptographically valid, and explicitly authorize the proposal.
6. Decoupled Readiness Invariant:
   InceptionAuthorizationToken grants R1 registration rights ONLY.
   It hard-locks: capital_authority_usd == $0.00, is_strategy_qualified == False,
   is_paper_authorized == False, is_live_authorized == False.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.quarantine import (
    DatasetAvailabilityPlane,
    DatasetExposureState,
    DatasetQuarantineValidator,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
    SplitPolicy,
)


# ---------------------------------------------------------------------------
# 1. Enums and Registry of Terminal Hypotheses
# ---------------------------------------------------------------------------


class InceptionDecision(str, Enum):
    """Authoritative decision emitted by the Research Re-Inception Gate."""

    INCEPTION_AUTHORIZED = "INCEPTION_AUTHORIZED"
    REJECTED_PREREQUISITE_FAILED = "REJECTED_PREREQUISITE_FAILED"
    BLOCKED_QUARANTINE_VIOLATION = "BLOCKED_QUARANTINE_VIOLATION"
    BLOCKED_MUTATION_VIOLATION = "BLOCKED_MUTATION_VIOLATION"


# Sealed terminal hypotheses that can NEVER be resurrected or reused
TERMINAL_HYPOTHESIS_REGISTRY: Tuple[str, ...] = (
    "HYP_TSMOM_EURUSD_001",
    "HYP_TSMOM_EURUSD_HTF_002",
)

# Quarantined time windows that cannot be reused without valid governance exception
PERMANENTLY_QUARANTINED_WINDOWS: Mapping[str, Tuple[str, str]] = {
    # M5 holdout bars 6,060 to 9,999 from HYP_TSMOM_EURUSD_001
    "EURUSD_M5_HOLDOUT": ("2026-08-18T04:40:00+00:00", "2026-09-04T21:00:00+00:00"),
    # HYP_TSMOM_EURUSD_HTF_002 H4 protected spans: Validation (3751..4996) +
    # embargo_val_oos (4997..5008) + Blind OOS (5009..6230). NOT REUSABLE for HYP_003.
    "EURUSD_H4_VALIDATION_OOS": ("2023-05-29T16:00:00+00:00", "2024-12-31T20:00:00+00:00"),
}


# ---------------------------------------------------------------------------
# 2. Governance Exception Record DTO
# ---------------------------------------------------------------------------


class GovernanceExceptionRecord(BaseModel):
    """Cryptographically verifiable governance exception authorizing quarantined data access."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    exception_id: str
    authorized_hypothesis_id: str
    target_symbol: str
    target_timeframe: str
    quarantined_dataset_id: str
    rationale: str
    approved_by_operator: str
    approved_at_utc: str
    exception_digest: str

    def compute_canonical_digest(self) -> str:
        """Compute canonical SHA-256 over exception payload excluding digest."""
        payload = {
            "approved_at_utc": self.approved_at_utc,
            "approved_by_operator": self.approved_by_operator,
            "authorized_hypothesis_id": self.authorized_hypothesis_id,
            "exception_id": self.exception_id,
            "quarantined_dataset_id": self.quarantined_dataset_id,
            "rationale": self.rationale,
            "target_symbol": self.target_symbol,
            "target_timeframe": self.target_timeframe,
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @model_validator(mode="before")
    @classmethod
    def verify_digest_integrity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            stored_digest = data.get("exception_digest")
            if stored_digest is not None:
                payload = {
                    "approved_at_utc": data["approved_at_utc"],
                    "approved_by_operator": data["approved_by_operator"],
                    "authorized_hypothesis_id": data["authorized_hypothesis_id"],
                    "exception_id": data["exception_id"],
                    "quarantined_dataset_id": data["quarantined_dataset_id"],
                    "rationale": data["rationale"],
                    "target_symbol": data["target_symbol"],
                    "target_timeframe": data["target_timeframe"],
                }
                calc = hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                if stored_digest != calc:
                    raise DataContractError(
                        f"GOVERNANCE_EXCEPTION_DIGEST_CORRUPTED: Digest {stored_digest} != computed {calc}."
                    )
        return data


# ---------------------------------------------------------------------------
# 3. Research Inception Proposal DTO
# ---------------------------------------------------------------------------


class ResearchInceptionProposal(BaseModel):
    """Formal, declarative pre-registration proposal presented to the Re-Inception Gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_hypothesis_id: str
    candidate_hypothesis_version: str = "1.0.0"
    economic_rationale: str
    target_symbol: str
    target_timeframe: str
    feature_dependencies: List[str]
    parameter_search_grid: Dict[str, List[Any]]
    planned_trial_count: int
    target_horizons: List[int]
    primary_horizon: int
    expected_direction: ExpectedDirection
    invalidation_criteria: InvalidationCriteria
    cost_model: CostModelConfig
    proposed_dataset_id: str
    proposed_data_window: Tuple[str, str]  # (start_utc, end_utc)
    proposed_split_policy: SplitPolicy
    governance_exception_id: Optional[str] = None
    author: str = "QuantitativeResearchAgent"
    proposed_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def grid_cardinality(self) -> int:
        """Compute Cartesian product cardinality of the declared parameter grid."""
        if not self.parameter_search_grid:
            return 0
        card = 1
        for values in self.parameter_search_grid.values():
            if not values:
                return 0
            card *= len(values)
        return card

    def to_hypothesis_specification(self) -> HypothesisSpecification:
        """Convert approved proposal to immutable HypothesisSpecification for R1 registration."""
        param_json = json.dumps(
            {
                "search_grid": self.parameter_search_grid,
                "trial_count": self.planned_trial_count,
                "dataset_id": self.proposed_dataset_id,
                "data_window": list(self.proposed_data_window),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return HypothesisSpecification(
            hypothesis_id=self.candidate_hypothesis_id,
            hypothesis_version=self.candidate_hypothesis_version,
            economic_rationale=self.economic_rationale,
            target_symbol=self.target_symbol,
            feature_dependencies=self.feature_dependencies,
            parameter_config_json=param_json,
            expected_direction=self.expected_direction,
            target_horizons=self.target_horizons,
            primary_horizon=self.primary_horizon,
            invalidation_criteria=self.invalidation_criteria,
            registered_at_utc=self.proposed_at_utc,
            author=self.author,
        )


# ---------------------------------------------------------------------------
# 4. Inception Authorization Token DTO
# ---------------------------------------------------------------------------


class InceptionAuthorizationToken(BaseModel):
    """Immutable governance token certifying R1 pre-registration eligibility ONLY.

    CRITICAL ARCHITECTURAL INVARIANT (Constraint 4):
    This token authorizes Step R1 registration ONLY. It has ZERO methods or permissions
    to authorize trading, capital allocation, or strategy qualification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    token_id: str
    authorized_hypothesis_id: str
    proposal_sha256: str
    decision: InceptionDecision = InceptionDecision.INCEPTION_AUTHORIZED
    authorized_at_utc: str

    # Hard-locked invariants: NEVER mutable, NEVER upgradable
    capital_authority_usd: Decimal = Field(default=Decimal("0.00"), frozen=True)
    is_strategy_qualified: bool = Field(default=False, frozen=True)
    is_paper_authorized: bool = Field(default=False, frozen=True)
    is_live_authorized: bool = Field(default=False, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def enforce_strictly_zero_authority(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cap = data.get("capital_authority_usd", Decimal("0.00"))
            if not isinstance(cap, Decimal):
                cap = Decimal(str(cap))
            if cap != Decimal("0.00"):
                raise DataContractError(
                    f"INCEPTION_TOKEN_AUTHORITY_VIOLATION: Inception token cannot grant capital ${cap}."
                )
            if data.get("is_strategy_qualified") is True:
                raise DataContractError("INCEPTION_TOKEN_AUTHORITY_VIOLATION: Inception token cannot qualify strategy.")
            if data.get("is_paper_authorized") is True:
                raise DataContractError("INCEPTION_TOKEN_AUTHORITY_VIOLATION: Inception token cannot authorize paper trading.")
            if data.get("is_live_authorized") is True:
                raise DataContractError("INCEPTION_TOKEN_AUTHORITY_VIOLATION: Inception token cannot authorize live trading.")
        return data


# ---------------------------------------------------------------------------
# 5. Master Research Re-Inception Gate Validator
# ---------------------------------------------------------------------------


class ResearchReInceptionGate:
    """Master gatekeeper validating proposals to start a new Phase 8.5 research cycle."""

    @classmethod
    def evaluate_reinception_proposal(
        cls,
        proposal: ResearchInceptionProposal,
        existing_exceptions: Optional[Mapping[str, GovernanceExceptionRecord]] = None,
        hypotheses_dir: Optional[Path] = None,
    ) -> InceptionAuthorizationToken:
        """Validate an inception proposal against all 6 institutional governance invariants.

        Strictly enforces:
        1. New Immutable ID (no resurrection of TERMINAL_HYPOTHESIS_REGISTRY, no mutating sealed files).
        2. Cardinal Equality (planned_trial_count == search grid cardinality).
        3. Declarative Data Contract & Window completeness.
        4. Quarantine Boundary & Verified Governance Exception.
        5. Pre-Registration completeness (rationale >= 20 chars, horizons, invalidation bounds).
        6. Zero capital / zero trading authority.

        Raises:
            DataContractError: If any single governance invariant fails (fail-closed).
        """
        # -------------------------------------------------------------------
        # 1. NEW IMMUTABLE HYPOTHESIS ID CHECKS
        # -------------------------------------------------------------------
        hyp_id = proposal.candidate_hypothesis_id.strip()
        if not hyp_id:
            raise DataContractError("REINCEPTION_REJECTED: candidate_hypothesis_id cannot be empty.")

        if not re.match(r"^HYP_[A-Z0-9_]+$", hyp_id):
            raise DataContractError(
                f"REINCEPTION_REJECTED: candidate_hypothesis_id '{hyp_id}' does not match pattern '^HYP_[A-Z0-9_]+$'."
            )

        # Anti-Resurrection check
        if hyp_id in TERMINAL_HYPOTHESIS_REGISTRY:
            raise DataContractError(
                f"BLOCKED_MUTATION_VIOLATION: Hypothesis ID '{hyp_id}' is permanently TERMINALLY_FALSIFIED. "
                f"Resurrecting or modifying a terminally closed hypothesis is strictly forbidden. "
                f"De novo research requires a distinct hypothesis ID."
            )

        # Check existing sealed hypothesis collision on disk
        hyp_base_dir = hypotheses_dir or Path("docs/phase8.5/hypotheses")
        sealed_file = hyp_base_dir / f"{hyp_id}.json"
        if sealed_file.exists():
            raise DataContractError(
                f"BLOCKED_MUTATION_VIOLATION: Hypothesis file already exists at '{sealed_file}'. "
                f"Overwriting or re-registering an existing hypothesis ID is strictly forbidden."
            )

        # -------------------------------------------------------------------
        # 2. ANTI-HARKING SEARCH CARDINALITY CHECK (Constraint 2)
        # -------------------------------------------------------------------
        if not proposal.parameter_search_grid:
            raise DataContractError("ANTI_HARKING_REJECTED: parameter_search_grid cannot be empty.")

        cardinality = proposal.grid_cardinality
        if cardinality <= 0:
            raise DataContractError("ANTI_HARKING_REJECTED: parameter_search_grid cardinality must be > 0.")

        if proposal.planned_trial_count != cardinality:
            raise DataContractError(
                f"ANTI_HARKING_CARDINALITY_MISMATCH: Declared planned_trial_count ({proposal.planned_trial_count}) "
                f"does not match parameter_search_grid cardinality ({cardinality}). "
                f"Trial count K must strictly equal the declared search degrees of freedom."
            )

        # -------------------------------------------------------------------
        # 3. DECLARATIVE DATA CONTRACT & QUARANTINE BOUNDARY CHECKS
        # -------------------------------------------------------------------
        if not proposal.proposed_dataset_id.strip():
            raise DataContractError("DATA_CONTRACT_REJECTED: proposed_dataset_id cannot be empty.")

        start_utc, end_utc = proposal.proposed_data_window
        if not start_utc or not end_utc:
            raise DataContractError("DATA_CONTRACT_REJECTED: proposed_data_window must specify start and end UTC timestamps.")

        if start_utc >= end_utc:
            raise DataContractError(
                f"DATA_CONTRACT_REJECTED: proposed_data_window start '{start_utc}' >= end '{end_utc}'."
            )

        # Quarantine check against permanently protected holdout windows.
        # M5:     2026-08-18T04:40:00+00:00 to 2026-09-04T21:00:00+00:00 (HYP_001 holdout)
        # H4:     2023-05-29T16:00:00+00:00 to 2024-12-31T20:00:00+00:00 (HYP_002 Validation+OOS)
        window_key_by_instrument: Mapping[str, str] = {
            "EURUSD_M5": "EURUSD_M5_HOLDOUT",
            "EURUSD_H4": "EURUSD_H4_VALIDATION_OOS",
        }
        instrument_key = f"{proposal.target_symbol}_{proposal.target_timeframe.upper()}"
        quarantined_window_key = window_key_by_instrument.get(instrument_key)
        if quarantined_window_key is not None:
            q_start, q_end = PERMANENTLY_QUARANTINED_WINDOWS[quarantined_window_key]
            # Check if windows overlap
            if not (end_utc <= q_start or start_utc >= q_end):
                # Proposed window overlaps with quarantined holdout!
                if not proposal.governance_exception_id:
                    raise DataContractError(
                        f"BLOCKED_QUARANTINE_VIOLATION: Proposed data window ({start_utc}..{end_utc}) overlaps "
                        f"with permanently quarantined window '{quarantined_window_key}' ({q_start}..{q_end}). "
                        f"Quarantined data cannot be reused without an explicit, verified governance exception."
                    )

                # Constraint 3: Verify governance exception record
                exceptions = existing_exceptions or {}
                exc_id = proposal.governance_exception_id
                if exc_id not in exceptions:
                    raise DataContractError(
                        f"BLOCKED_QUARANTINE_VIOLATION: Governance exception '{exc_id}' not found in registry. "
                        f"Quarantined data access rejected fail-closed."
                    )

                exc_record = exceptions[exc_id]
                if exc_record.authorized_hypothesis_id != hyp_id:
                    raise DataContractError(
                        f"BLOCKED_QUARANTINE_VIOLATION: Exception '{exc_id}' authorizes "
                        f"'{exc_record.authorized_hypothesis_id}', not '{hyp_id}'."
                    )

                if exc_record.target_symbol != proposal.target_symbol or exc_record.target_timeframe != proposal.target_timeframe:
                    raise DataContractError(
                        f"BLOCKED_QUARANTINE_VIOLATION: Exception '{exc_id}' targets "
                        f"{exc_record.target_symbol} {exc_record.target_timeframe}, "
                        f"not {proposal.target_symbol} {proposal.target_timeframe}."
                    )

                # Verify exception digest
                expected_exc_digest = exc_record.compute_canonical_digest()
                if exc_record.exception_digest != expected_exc_digest:
                    raise DataContractError(
                        f"BLOCKED_QUARANTINE_VIOLATION: Exception '{exc_id}' digest corrupted: "
                        f"{exc_record.exception_digest} != {expected_exc_digest}."
                    )

        # -------------------------------------------------------------------
        # 4. PRE-REGISTRATION COMPLETENESS CHECKS
        # -------------------------------------------------------------------
        rationale = proposal.economic_rationale.strip()
        if len(rationale) < 20:
            raise DataContractError(
                f"PRE_REGISTRATION_REJECTED: economic_rationale too short ({len(rationale)} chars < 20). "
                f"A non-trivial structural economic theory is required."
            )

        if not proposal.feature_dependencies:
            raise DataContractError("PRE_REGISTRATION_REJECTED: feature_dependencies cannot be empty.")

        if not proposal.target_horizons:
            raise DataContractError("PRE_REGISTRATION_REJECTED: target_horizons cannot be empty.")

        if proposal.primary_horizon not in proposal.target_horizons:
            raise DataContractError(
                f"PRE_REGISTRATION_REJECTED: primary_horizon ({proposal.primary_horizon}) "
                f"must be in target_horizons ({proposal.target_horizons})."
            )

        # Invalidation bounds check
        if proposal.invalidation_criteria.min_in_sample_rank_ic <= Decimal("0.0"):
            raise DataContractError("PRE_REGISTRATION_REJECTED: min_in_sample_rank_ic must be strictly positive.")

        if proposal.invalidation_criteria.min_hac_t_stat < Decimal("1.50"):
            raise DataContractError("PRE_REGISTRATION_REJECTED: min_hac_t_stat must be >= 1.50.")

        # -------------------------------------------------------------------
        # 5. EMIT AUTHORIZATION TOKEN (Constraint 4)
        # -------------------------------------------------------------------
        proposal_dict = proposal.model_dump(mode="python")
        proposal_json = CanonicalConfigSerializer.to_canonical_json(proposal_dict)
        prop_sha256 = hashlib.sha256(proposal_json.encode("utf-8")).hexdigest()

        token_id = f"AUTH_INCEPTION_{hyp_id}_{prop_sha256[:16]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        return InceptionAuthorizationToken(
            token_id=token_id,
            authorized_hypothesis_id=hyp_id,
            proposal_sha256=prop_sha256,
            decision=InceptionDecision.INCEPTION_AUTHORIZED,
            authorized_at_utc=now_utc,
            capital_authority_usd=Decimal("0.00"),
            is_strategy_qualified=False,
            is_paper_authorized=False,
            is_live_authorized=False,
        )
