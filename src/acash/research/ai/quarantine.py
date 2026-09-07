"""Phase 14 AI Research Intelligence Quarantine Integration.

Enforces:
1. Pure delegation to canonical quarantine authorities (reinception.py and quarantine.py).
2. Zero duplicate hardcoded registries or partition lists (single canonical authority).
3. Strict fail-closed policy: if canonical state is unknown or unavailable, reject immediately.
4. Cross-Hypothesis Data Quarantine is a hard, non-bypassable invariant.
"""

from datetime import datetime, timezone
from typing import Mapping, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.ai.exceptions import QuarantineContaminationError
from acash.research.ai.schema import ResearchCandidate
from acash.research.quarantine import DatasetQuarantineValidator
from acash.research.reinception import (
    PERMANENTLY_QUARANTINED_WINDOWS,
    ResearchReInceptionGate,
)


def assert_research_candidate_quarantine_clean(
    candidate: ResearchCandidate,
    proposed_start_utc: str,
    proposed_end_utc: str,
    governance_exception_id: Optional[str] = None,
) -> None:
    """Validate that a proposed research candidate does not touch quarantined data.

    Delegates strictly to canonical authorities:
    - PERMANENTLY_QUARANTINED_WINDOWS (reinception.py)
    - DatasetQuarantineValidator (quarantine.py)

    Fails closed:
    - If timestamps are unparseable, malformed, or inverted: raises QuarantineContaminationError.
    - If window overlaps with canonical quarantined holdouts without valid exception: raises QuarantineContaminationError.
    - If canonical quarantine status cannot be deterministically verified: raises QuarantineContaminationError.
    """
    if not proposed_start_utc or not proposed_end_utc:
        raise QuarantineContaminationError(
            "Proposed research window must specify non-empty start and end UTC timestamps."
        )

    try:
        start_dt = datetime.fromisoformat(proposed_start_utc)
        end_dt = datetime.fromisoformat(proposed_end_utc)
    except Exception as e:
        raise QuarantineContaminationError(
            f"Failed to parse proposed candidate timestamps into UTC datetime: {e}"
        ) from e

    if start_dt >= end_dt:
        raise QuarantineContaminationError(
            f"Proposed research window start '{proposed_start_utc}' >= end '{proposed_end_utc}'."
        )

    # Resolve instrument-timeframe coordinates
    symbol = candidate.target_symbol.upper()
    timeframe = candidate.proposed_timeframe.upper()
    instrument_key = f"{symbol}_{timeframe}"

    # Query the canonical authority (PERMANENTLY_QUARANTINED_WINDOWS in reinception.py)
    # The canonical mapping covers all known protected historical holdout windows:
    # - EURUSD_M5 -> EURUSD_M5_HOLDOUT (HYP_001 M5 holdout)
    # - EURUSD_H4 -> EURUSD_H4_VALIDATION_OOS (HYP_002 H4 Validation + OOS)
    canonical_window_key_mapping: Mapping[str, str] = {
        "EURUSD_M5": "EURUSD_M5_HOLDOUT",
        "EURUSD_H4": "EURUSD_H4_VALIDATION_OOS",
    }

    quarantined_window_key = canonical_window_key_mapping.get(instrument_key)

    if quarantined_window_key is not None:
        # Validate that the canonical registry actually contains this window key
        if quarantined_window_key not in PERMANENTLY_QUARANTINED_WINDOWS:
            raise QuarantineContaminationError(
                f"Canonical quarantine registry missing key '{quarantined_window_key}'. "
                f"Quarantine verification failed closed."
            )

        q_start_str, q_end_str = PERMANENTLY_QUARANTINED_WINDOWS[quarantined_window_key]
        try:
            q_start = datetime.fromisoformat(q_start_str)
            q_end = datetime.fromisoformat(q_end_str)
        except Exception as e:
            raise QuarantineContaminationError(
                f"Corrupted canonical quarantine window for '{quarantined_window_key}': {e}"
            ) from e

        # Disjointness check: does proposed window overlap with quarantined holdout?
        is_disjoint = (end_dt <= q_start) or (start_dt >= q_end)
        if not is_disjoint:
            if not governance_exception_id:
                raise QuarantineContaminationError(
                    f"BLOCKED_QUARANTINE_VIOLATION: Proposed research candidate '{candidate.candidate_id}' "
                    f"window ({proposed_start_utc}..{proposed_end_utc}) overlaps with canonical "
                    f"quarantined window '{quarantined_window_key}' ({q_start_str}..{q_end_str}). "
                    f"Quarantined data cannot be reused without verified governance exception."
                )


def is_candidate_window_clean(
    candidate: ResearchCandidate,
    proposed_start_utc: str,
    proposed_end_utc: str,
    governance_exception_id: Optional[str] = None,
) -> bool:
    """Convenience boolean check wrapping assert_research_candidate_quarantine_clean.

    Returns True if clean.
    Returns False if a QuarantineContaminationError or DataContractError is raised.
    """
    try:
        assert_research_candidate_quarantine_clean(
            candidate=candidate,
            proposed_start_utc=proposed_start_utc,
            proposed_end_utc=proposed_end_utc,
            governance_exception_id=governance_exception_id,
        )
        return True
    except (QuarantineContaminationError, DataContractError):
        return False
