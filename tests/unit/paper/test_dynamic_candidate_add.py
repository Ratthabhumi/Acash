"""Dynamic shadow candidate admission (V2 follow-up).

Late joiners are staged by an operator (SIGHUP / candidate-add file) and only
materialized at a finalized-bar boundary into a NEW observation cohort. Boot-time
slots keep the tournament cohort; late joiners are never silently ranked against
boot peers (single-member cohorts report rank = null).

Order of attack (AGENTS.md principle 14): happy path -> boundary -> rejection
matrix -> adversarial (capacity double-stage) -> golden catalog identity.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, cast

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.paper.runner import SignalSizingPolicy, SyntheticBar
from acash.paper.strategy import INFRASTRUCTURE_CANDIDATES_10SLOT
from acash.paper.tournament import (
    ShadowTournamentSupervisor,
    TournamentSlot,
    create_default_shadow_tournament,
    slot_ids_for_count,
)

_GIT = "a11995373bcb293135374e8c7dce6091963fea4a"
_T0 = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)


def _bar(minute: int) -> SyntheticBar:
    ts = _T0 + timedelta(minutes=minute)
    close = Decimal("50000") + Decimal(minute)  # monotonic -> LONG fills
    return SyntheticBar(
        timestamp_utc=ts,
        symbol="BTCUSDT",
        open=close - Decimal("1"),
        high=close + Decimal("10"),
        low=close - Decimal("10"),
        close=close,
        volume=Decimal("1.5"),
        feed_source="scripted.candidate.test",
        feed_source_id=f"BCAND-{minute}",
        received_at_utc=ts + timedelta(seconds=1),
        feed_sequence=minute,
        data_age_ms=1000,
    )


def _boot(
    tmp_path: Path,
    num_slots: int = 3,
    *,
    auto_mount: bool = False,
    mount_count: Optional[int] = None,
) -> ShadowTournamentSupervisor:
    return create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha=_GIT,
        num_slots=num_slots,
        auto_mount_infrastructure_candidates=auto_mount,
        infra_mount_count=mount_count,
        signal_sizing_policy=SignalSizingPolicy.INFRA_FIXED_QUANTITY,
        nav_sizing_notional_pct=Decimal("0"),
    )


def _run(supervisor: ShadowTournamentSupervisor, minutes: int) -> None:
    for m in range(1, minutes + 1):
        supervisor.process_bar(_bar(m))


def _run_since(
    supervisor: ShadowTournamentSupervisor, start_minute: int, count: int
) -> None:
    for m in range(start_minute, start_minute + count):
        supervisor.process_bar(_bar(m))


def _candidate_003() -> str:
    return INFRASTRUCTURE_CANDIDATES_10SLOT["B"].strategy_id


def _slot_dict(supervisor: ShadowTournamentSupervisor, slot_id: str) -> Dict[str, Any]:
    return cast(Dict[str, Any], supervisor.to_dict()["slots"][slot_id])


# A ---------------------------------------------------------------------------


def test_stage_before_materialize_semantics(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 5)
    result = supervisor.stage_candidate_add("B", _candidate_003())
    assert result == {
        "slotId": "B",
        "strategyId": _candidate_003(),
        "ok": True,
        "reason": "STAGED",
    }
    # Not yet materialized: B must still be honest UNASSIGNED.
    before = _slot_dict(supervisor, "B")
    assert before["status"] == "UNASSIGNED"
    assert before["observationKind"] == "NONE"
    assert before["cohortId"] is None
    assert supervisor.last_operator_action_results == []
    # Materialization happens at the next finalized-bar boundary.
    _run(supervisor, 1)
    after = _slot_dict(supervisor, "B")
    assert after["status"] == "RUNNING"
    assert after["observationKind"] == "LATE_JOIN"
    assert after["cohortId"] is not None
    assert after["cohortId"].startswith(f"{supervisor._tournament_id}:ADD:")
    admitted = supervisor.last_operator_action_results
    assert [r["reason"] for r in admitted] == ["ADMITTED"]
    assert admitted[0]["ok"] is True


# B ---------------------------------------------------------------------------


def test_materialization_at_bar_boundary_consumes_same_bar(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 6)
    stalled = supervisor._bar_count
    supervisor.stage_candidate_add("B", _candidate_003())
    supervisor.process_bar(_bar(7))  # this single bar both admits AND is consumed
    assert supervisor._bar_count == stalled + 1
    late = _slot_dict(supervisor, "B")
    boot = _slot_dict(supervisor, "A")
    assert late["lastBarUtc"] == boot["lastBarUtc"] == _bar(7).timestamp_utc.isoformat()


# C ---------------------------------------------------------------------------


def test_boot_slots_continuous_cohort(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 3)
    boot = _slot_dict(supervisor, "A")
    assert boot["observationKind"] == "CONTINUOUS"
    assert boot["cohortId"] == supervisor._tournament_id
    assert boot["comparisonWindowId"] == supervisor._tournament_id
    # Unassigned coordinates stay NONE with zero cohort provenance.
    for slot_id in ("B", "C"):
        unassigned = _slot_dict(supervisor, slot_id)
        assert unassigned["observationKind"] == "NONE"
        assert unassigned["cohortId"] is None


# D ---------------------------------------------------------------------------


def test_unassigned_slot_zero_provenance(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 3)
    unassigned = _slot_dict(supervisor, "C")
    assert unassigned["status"] == "UNASSIGNED"
    assert unassigned["observationKind"] == "NONE"
    assert unassigned["cohortId"] is None
    assert unassigned["comparisonWindowId"] is None
    assert unassigned["openPositions"] == []
    assert unassigned["recentFills"] == []
    lb = supervisor.to_dict()["leaderboard"]["rankedSlots"]
    # Honest exclusion: an UNASSIGNED slot with zero fills is never fabricated
    # into a leaderboard row (no rank, no phantom comparison).
    assert all(r["slotId"] != "C" for r in lb)


# E1 --------------------------------------------------------------------------


def test_rejection_matrix_stage_state(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    # Not running.
    supervisor.halt(reason="ctl-h", terminal_reason=None)
    assert (
        supervisor.stage_candidate_add("B", _candidate_003())["reason"]
        == "TOURNAMENT_NOT_RUNNING"
    )
    # Wrong slot shape / unknown coordinate.
    supervisor2 = _boot(tmp_path, 3)
    supervisor2.start()
    assert (
        supervisor2.stage_candidate_add("ZZ", _candidate_003())["reason"]
        == "INVALID_SLOT_ID"
    )
    assert (
        supervisor2.stage_candidate_add("D", _candidate_003())["reason"]
        == "UNKNOWN_SLOT"
    )


# E2 --------------------------------------------------------------------------


def test_rejection_matrix_runtime(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 3)
    # Occupied slot (A is boot-mounted).
    assert supervisor.stage_candidate_add("A", _candidate_003())["reason"] == "SLOT_OCCUPIED"
    # Unknown catalog identity.
    assert (
        supervisor.stage_candidate_add("B", "INFRA-NOT-IN-CATALOG-999")["reason"]
        == "UNKNOWN_STRATEGY_ID"
    )
    # Duplicate across two slots.
    assert supervisor.stage_candidate_add("B", _candidate_003())["ok"] is True
    assert (
        supervisor.stage_candidate_add("C", _candidate_003())["reason"]
        == "DUPLICATE_STRATEGY_ID"
    )
    # Unconfigured runtime (live tournament, but the operator gateway was never
    # wired into a slot builder / candidate resolver).
    unconfigured = _boot(tmp_path, 3)
    unconfigured.start()
    unconfigured._slot_builder = None
    unconfigured._candidate_resolver = None
    assert (
        unconfigured.stage_candidate_add("B", _candidate_003())["reason"]
        == "CANDIDATE_ADD_UNCONFIGURED"
    )


# F ---------------------------------------------------------------------------


def test_batch_cohort_identity(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 4)
    supervisor.start()
    _run(supervisor, 5)
    r1 = supervisor.stage_candidate_add("B", _candidate_003())
    r2 = supervisor.stage_candidate_add(
        "C", INFRASTRUCTURE_CANDIDATES_10SLOT["C"].strategy_id
    )
    assert r1["reason"] == r2["reason"] == "STAGED"
    _run(supervisor, 1)
    b_cohort = _slot_dict(supervisor, "B")["cohortId"]
    c_cohort = _slot_dict(supervisor, "C")["cohortId"]
    assert b_cohort == c_cohort
    assert b_cohort.startswith(f"{supervisor._tournament_id}:ADD:")
    assert _slot_dict(supervisor, "B")["comparisonWindowId"] == b_cohort
    assert _slot_dict(supervisor, "C")["comparisonWindowId"] == b_cohort


# G ---------------------------------------------------------------------------


def test_late_joiner_cohort_unranked_vs_boot_peers(tmp_path: Path) -> None:
    # num_slots=6, mount_count=3 -> A + B,C,D mounted at boot; E,F free.
    supervisor = _boot(tmp_path, 6, auto_mount=True, mount_count=3)
    supervisor.start()
    _run(supervisor, 45)
    # Boot cohort now has >= 2 comparable members -> ranked.
    boot_lb = supervisor.to_dict()["leaderboard"]["rankedSlots"]
    boot_ranks = [r["rank"] for r in boot_lb if r["slotId"] in ("A", "B", "C", "D")]
    assert boot_ranks and all(r is not None for r in boot_ranks)
    # Admit E as a late joiner with a trailer of new bars.
    supervisor.stage_candidate_add(
        "E", INFRASTRUCTURE_CANDIDATES_10SLOT["E"].strategy_id
    )
    _run_since(supervisor, 46, 12)
    lb = supervisor.to_dict()["leaderboard"]["rankedSlots"]
    e_row = next(r for r in lb if r["slotId"] == "E")
    assert e_row["rank"] is None  # single-member cohort, never apples-vs-oranges
    assert e_row["observationKind"] == "LATE_JOIN"
    assert e_row["cohortId"] != supervisor._tournament_id
    a_row = next(r for r in lb if r["slotId"] == "A")
    assert a_row["rank"] is not None


# H ---------------------------------------------------------------------------


def test_candidate_added_journal_propagation(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 5)
    supervisor.stage_candidate_add("B", _candidate_003())
    _run(supervisor, 1)
    runner_b = supervisor._slots["B"].runner
    assert runner_b is not None
    events = [
        e
        for e in runner_b.journal.read_all()
        if e.event_type.value == "CANDIDATE_ADDED"
    ]
    assert len(events) == 1
    assert events[0].payload.get("event") == "CANDIDATE_ADMITTED"
    assert events[0].payload.get("cohort_id") is not None
    assert events[0].payload.get("started_at_utc") is not None
    assert events[0].payload.get("baseline_nav_usd") == "1000.00"


# I ---------------------------------------------------------------------------


def test_clear_operator_action_results(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 5)
    supervisor.stage_candidate_add("B", _candidate_003())
    _run(supervisor, 1)
    assert len(supervisor.last_operator_action_results) == 1
    supervisor.clear_operator_action_results()
    assert supervisor.last_operator_action_results == []


# J ---------------------------------------------------------------------------


def test_no_candidate_stage_is_noop(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 7)
    supervisor.clear_operator_action_results()
    _run(supervisor, 3)
    assert supervisor.last_operator_action_results == []
    assert all(
        _slot_dict(supervisor, slot_id)["observationKind"] in ("CONTINUOUS", "NONE")
        for slot_id in ("A", "B", "C")
    )


# K ---------------------------------------------------------------------------


def test_materialized_candidate_matches_catalog_spec(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 5)
    candidate = INFRASTRUCTURE_CANDIDATES_10SLOT["B"]
    supervisor.stage_candidate_add("B", candidate.strategy_id)
    _run(supervisor, 1)
    runner = supervisor._slots["B"].runner
    assert runner is not None
    strategy = runner._strategy
    assert strategy.strategy_id == candidate.strategy_id
    assert strategy.strategy_version == candidate.strategy_version
    assert runner._config.signal_sizing_policy == SignalSizingPolicy.INFRA_FIXED_QUANTITY
    assert str(runner._config.nav_sizing_notional_pct) == "0"


# L ---------------------------------------------------------------------------


def test_duplicate_after_admission_rejected(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 5)
    supervisor.stage_candidate_add("B", _candidate_003())
    _run(supervisor, 1)
    active = supervisor.last_operator_action_results
    assert active[0]["reason"] == "ADMITTED"
    assert (
        supervisor.stage_candidate_add("C", _candidate_003())["reason"]
        == "DUPLICATE_STRATEGY_ID"
    )


# M ---------------------------------------------------------------------------


def test_capacity_exceeded_adversarial_double_stage(tmp_path: Path) -> None:
    """Staging the SAME free slot twice with different identities is caught at
    stage time by the capacity bound (active + staged >= num_slots)."""
    supervisor = _boot(tmp_path, 2)
    supervisor.start()
    _run(supervisor, 2)
    first = supervisor.stage_candidate_add("B", _candidate_003())
    assert first["ok"] is True
    second = supervisor.stage_candidate_add(
        "B", INFRASTRUCTURE_CANDIDATES_10SLOT["C"].strategy_id
    )
    assert second["reason"] == "CAPACITY_EXCEEDED"
    assert second["ok"] is False


# N ---------------------------------------------------------------------------


def test_unconfigured_materialize_fails_closed(tmp_path: Path) -> None:
    supervisor = _boot(tmp_path, 3)
    supervisor.start()
    _run(supervisor, 5)
    supervisor._slot_builder = None
    supervisor._candidate_resolver = None
    # Force the staging layer (as the operator file path would) and confirm the
    # materialization boundary raises instead of silently dropping the add.
    supervisor._pending_candidate_adds.append(
        {"slot_id": "B", "strategy_id": _candidate_003(), "staged_at_utc": "now"}
    )
    with pytest.raises(DataContractError):
        supervisor.process_bar(_bar(7))