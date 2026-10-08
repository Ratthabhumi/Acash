"""Offline V3 proposal checks, not activation or dispatch authority.

No runner imports this module. It neither issues authority nor writes state.
Calendar, scheduling and initial economics use existing canonical helpers.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Dict, Mapping

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow import (
    candidate_schedule_time,
    next_trading_session_open,
)
from acash.research.hyp_011.shadow_ops import build_initial_state, validate_initial_state


def prepare_initial_state(
    proposal: Mapping[str, Any], now: datetime, calendar: NyseCa1Calendar,
) -> Dict[str, Any]:
    """Return an unissued, independent state preview; never executable authority."""
    if now.tzinfo is None:
        raise DataContractError("V3_PROPOSAL_NAIVE_TIME")
    if proposal.get("status") != "UNISSUED_PROPOSAL":
        raise DataContractError("V3_PROPOSAL_NOT_UNISSUED")
    segment = proposal.get("segment_id")
    if not isinstance(segment, str) or re.fullmatch(r"HYP_011_PROSPECTIVE_V3_[A-Z0-9_]+", segment) is None:
        raise DataContractError("V3_PROPOSAL_FRESH_NAMESPACE_REQUIRED")
    if proposal.get("authority_namespace") != "UNISSUED_" + segment:
        raise DataContractError("V3_PROPOSAL_AUTHORITY_NAMESPACE")
    if proposal.get("state_namespace") != segment.lower():
        raise DataContractError("V3_PROPOSAL_STATE_NAMESPACE")
    if proposal.get("prior_state") is not None or proposal.get("prior_authority") is not None:
        raise DataContractError("V3_PROPOSAL_PRIOR_LINEAGE_FORBIDDEN")
    if proposal.get("miss_policy") != "TERMINATE_NO_BACKFILL":
        raise DataContractError("V3_PROPOSAL_MISS_POLICY")
    if proposal.get("persistent") is not False:
        raise DataContractError("V3_PROPOSAL_CATCHUP_FORBIDDEN")
    locks = proposal.get("locks")
    if not isinstance(locks, dict) or (
        locks.get("paper_authorized") is not False
        or locks.get("live_authorized") is not False
        or locks.get("no_real_orders") is not True
        or locks.get("capital_authority_usd") != "0.00"
    ):
        raise DataContractError("V3_PROPOSAL_LOCKS")
    raw_session = proposal.get("activation_session")
    if not isinstance(raw_session, str):
        raise DataContractError("V3_PROPOSAL_SESSION_UNRESOLVED")
    try:
        target = date.fromisoformat(raw_session)
    except ValueError:
        raise DataContractError("V3_PROPOSAL_SESSION_INVALID") from None
    session = calendar.get_session(target)
    if session.open_utc is None or now.astimezone(timezone.utc) >= session.open_utc:
        raise DataContractError("V3_PROPOSAL_NOT_FUTURE_SESSION")
    state = build_initial_state(target, segment_id=segment)
    validate_initial_state(state, target)
    return state


def assess_missing_observation(
    target: date, now: datetime, calendar: NyseCa1Calendar,
    observation_present: bool,
) -> Dict[str, Any]:
    """Advisory classification from local evidence; no claim of host outage.

    Absence after dispatch is not yet a missed session. Only the next trading
    open makes it missed under F14. Input existence is not chain verification.
    Never advances a sample, writes evidence, triggers requests or resumes.
    """
    if now.tzinfo is None or type(observation_present) is not bool:
        raise DataContractError("V3_MISS_INVALID_INPUT")
    session = calendar.get_session(target)
    if session.open_utc is None:
        raise DataContractError("V3_MISS_NON_SESSION")
    dispatch = candidate_schedule_time(target, calendar)
    _, next_open = next_trading_session_open(target, calendar)
    instant = now.astimezone(timezone.utc)
    status = (
        "OBSERVATION_PRESENT_UNVERIFIED" if observation_present else
        "MISSED_UNOBSERVED" if instant >= next_open else
        "DISPATCH_ELAPSED_OBSERVATION_UNCONFIRMED" if instant >= dispatch else
        "NOT_DUE"
    )
    return {
        "target_session": target.isoformat(), "status": status,
        "candidate_dispatch_utc": dispatch.isoformat(),
        "next_open_utc": next_open.isoformat(),
        "sample_advancement": 0, "network_requests": 0,
        "host_online_at_dispatch": "UNKNOWN", "automatic_catchup": False,
    }
