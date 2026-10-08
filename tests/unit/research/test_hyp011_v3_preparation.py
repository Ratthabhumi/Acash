"""Offline proposal regression checks; no authority issued or provider traffic."""
from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow_v3_preparation import (
    assess_missing_observation, prepare_initial_state,
)

ROOT = Path(__file__).resolve().parents[3]


def proposal() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads((ROOT / "docs/operations/HYP011_V3_UNISSUED_PROPOSAL.json").read_text())
    doc["activation_session"] = "2026-11-27"
    return doc


def test_preview_is_independent_and_zero_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("offline preflight attempted HTTP")
    monkeypatch.setattr(httpx.Client, "request", forbidden)
    doc = proposal()
    before = copy.deepcopy(doc)
    state = prepare_initial_state(doc, datetime(2026, 11, 26, tzinfo=timezone.utc), NyseCa1Calendar())
    assert doc == before
    assert state["observed_sessions"] == [] and state["observed_session_count"] == 0
    assert state["last_observation_sha256"] is None
    assert state["activation_authority_id"] is None
    assert "segment_activation_authority_sha256" not in state
    assert state["strategy"]["holdings"] == {"ACWI": 0, "AGG": 0}
    assert state["locks"]["capital_authority_usd"] == "0.00"


@pytest.mark.parametrize("field,value", [
    ("status", "AUTHORIZED"), ("segment_id", "HYP_011_PROSPECTIVE_V2"),
    ("authority_namespace", "AUTHORIZE_HYP011_V2_20261005"),
    ("state_namespace", "v2"), ("prior_state", "v2/state.json"),
    ("prior_authority", "2026-10-05"), ("miss_policy", "CONTINUE"),
    ("persistent", True), ("activation_session", "2026-10-05"),
    ("activation_session", "2026-11-26"), ("activation_session", None),
])
def test_v2_reuse_stale_and_catchup_rejected(field: str, value: Any) -> None:
    doc = proposal()
    doc[field] = value
    with pytest.raises(DataContractError):
        prepare_initial_state(doc, datetime(2026, 11, 26, tzinfo=timezone.utc), NyseCa1Calendar())


@pytest.mark.parametrize("key,value", [
    ("paper_authorized", True), ("live_authorized", True),
    ("capital_authority_usd", "100000.00"), ("no_real_orders", False),
    ("no_real_orders", 1),
])
def test_execution_locks_reject_real_authority(key: str, value: Any) -> None:
    doc = proposal()
    doc["locks"][key] = value
    with pytest.raises(DataContractError, match="V3_PROPOSAL_LOCKS"):
        prepare_initial_state(doc, datetime(2026, 11, 26, tzinfo=timezone.utc), NyseCa1Calendar())


def test_halfday_weekend_timezone_and_no_early_miss() -> None:
    calendar = NyseCa1Calendar()
    target = date(2026, 11, 27)  # NYSE half-day, after US DST ends.
    bangkok = ZoneInfo("Asia/Bangkok")
    pending = assess_missing_observation(target, datetime(2026, 11, 28, 1, 20, tzinfo=bangkok), calendar, False)
    assert pending["candidate_dispatch_utc"] == "2026-11-27T18:20:00+00:00"
    assert pending["status"] == "DISPATCH_ELAPSED_OBSERVATION_UNCONFIRMED"
    assert pending["next_open_utc"] == "2026-11-30T14:30:00+00:00"
    missed = assess_missing_observation(target, datetime(2026, 11, 30, 21, 30, tzinfo=bangkok), calendar, False)
    assert missed["status"] == "MISSED_UNOBSERVED"
    assert missed["sample_advancement"] == missed["network_requests"] == 0
    assert missed["host_online_at_dispatch"] == "UNKNOWN"
    present = assess_missing_observation(target, datetime(2026, 11, 30, 15, tzinfo=timezone.utc), calendar, True)
    assert present["status"] == "OBSERVATION_PRESENT_UNVERIFIED"


def test_naive_time_rejected() -> None:
    with pytest.raises(DataContractError):
        prepare_initial_state(proposal(), datetime(2026, 11, 26), NyseCa1Calendar())
    with pytest.raises(DataContractError):
        assess_missing_observation(date(2026, 11, 27), datetime(2026, 11, 28), NyseCa1Calendar(), False)
