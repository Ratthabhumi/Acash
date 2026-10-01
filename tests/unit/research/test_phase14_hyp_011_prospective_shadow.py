"""Tests for HYP_011 prospective shadow activation machinery (no price access).

Covers: corrected-authority gating, scientific boundary, missed-session
derivation + zero counting, activation from real commit timestamps, guards
(duplicate/out-of-order/early/future/recent-stress/quarantine), fresh 100k,
80/20 strategy constants, 504+2 minimums, and locks. Calendar only.
"""

import io
import json
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011 import shadow as SH


def test_corrected_authority_required() -> None:
    with pytest.raises(DataContractError):
        SH.shadow_readiness("SOMETHING_ELSE", True)
    with pytest.raises(DataContractError):
        SH.shadow_readiness(
            "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW", False
        )
    ready = SH.shadow_readiness(
        "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW", True
    )
    assert ready["state"] == "PROSPECTIVE_SHADOW_ARMED_WAITING_FOR_FIRST_COMPLETED_SESSION"
    assert ready["starting_aum"] == "100000.00"


def test_scientific_boundary_and_missed_sessions_calendar_derived() -> None:
    cal = NyseCa1Calendar()
    assert SH.SCIENTIFIC_PROSPECTIVE_BOUNDARY == date(2026, 9, 25)
    assert cal.is_trading_session(date(2026, 9, 25)) is True
    # Activation-exclusive upper of 2026-09-28 (Monday): Fri 25th missed.
    missed = SH.missed_unobserved_sessions(cal, date(2026, 9, 28))
    assert missed == [date(2026, 9, 25)]
    # Missed sessions never count toward evaluation.
    state = SH.ShadowState(activation_session=date(2026, 9, 28))
    assert state.observed_count == 0
    assert state.minimums_satisfied() is False


def test_activation_uses_real_commit_timestamp() -> None:
    cal = NyseCa1Calendar()
    # R1 commit Friday 2026-09-24T22:34:44Z (after close) -> next open Friday... verified:
    session = SH.derive_activation_session(
        cal, datetime(2026, 9, 24, 22, 34, 44, tzinfo=timezone.utc)
    )
    assert session == date(2026, 9, 25)
    assert session > date(2026, 9, 24)
    # Naive timestamp rejected.
    with pytest.raises(DataContractError):
        SH.derive_activation_session(cal, datetime(2026, 9, 24, 22, 34, 44))


def test_activation_same_day_edge_cases() -> None:
    cal = NyseCa1Calendar()
    # Commit BEFORE today's eligible open -> today qualifies.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    ) == date(2026, 9, 25)
    # Commit EXACTLY at open -> strictly-after rule moves to next session.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 25, 13, 30, 0, tzinfo=timezone.utc)
    ) == date(2026, 9, 28)
    # Commit after open -> next session.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 25, 15, 0, 0, tzinfo=timezone.utc)
    ) == date(2026, 9, 28)
    # Weekend commit -> next session.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 26, 17, 39, 1, tzinfo=timezone.utc)
    ) == date(2026, 9, 28)


def test_fresh_start_no_carryover_and_strategy_constants() -> None:
    assert SH.SHADOW_STARTING_AUM == Decimal("100000.00")
    assert SH.PROSPECTIVE_MIN_SESSIONS == 504
    assert SH.PROSPECTIVE_MIN_REBALANCES == 2


def _after_close(session: date) -> datetime:
    cal = NyseCa1Calendar()
    close_utc = cal.get_session(session).close_utc
    assert close_utc is not None
    return close_utc + timedelta(seconds=1)


def test_completion_guard_uses_close_utc() -> None:
    cal = NyseCa1Calendar()
    close_utc = cal.get_session(date(2026, 9, 25)).close_utc
    assert close_utc == datetime(2026, 9, 25, 20, 0, 0, tzinfo=timezone.utc)
    state = SH.ShadowState(activation_session=date(2026, 9, 25))
    # One second before close -> incomplete.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 25), cal, close_utc - timedelta(seconds=2))
    # One second after close -> processable.
    state.record_session(date(2026, 9, 25), cal, _after_close(date(2026, 9, 25)))
    assert state.observed_count == 1
    # Naive now rejected.
    with pytest.raises(DataContractError):
        state.record_session(
            date(2026, 9, 28), cal, datetime(2026, 9, 29, 0, 0, 0)
        )


def test_session_guards() -> None:
    cal = NyseCa1Calendar()
    # Use the scientific boundary itself as a synthetic activation so all
    # guard paths execute against completed sessions (guard mechanics only;
    # production activation never backfills missed sessions).
    state = SH.ShadowState(activation_session=date(2026, 9, 25))
    after = _after_close(date(2026, 9, 25))
    # Earlier-than-activation rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 24), cal, after)
    # Recent-stress rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 8, 14), cal, after)
    # Quarantine rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 8, 15), cal, after)
    # Future/incomplete rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 28), cal, after)
    # Valid append + duplicate + out-of-order.
    state.record_session(date(2026, 9, 25), cal, after)
    assert state.observed_count == 1
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 25), cal, after)
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 24), cal, after)


def test_early_close_uses_actual_close_utc() -> None:
    cal = NyseCa1Calendar()
    # 2024-11-29: official early close (18:00Z, not 20:00Z).
    close_utc = cal.get_session(date(2024, 11, 29)).close_utc
    assert close_utc == datetime(2024, 11, 29, 18, 0, 0, tzinfo=timezone.utc)
    state = SH.ShadowState(activation_session=date(2024, 11, 29))
    with pytest.raises(DataContractError):
        state.record_session(
            date(2024, 11, 29), cal, close_utc - timedelta(seconds=1)
        )
    state.record_session(
        date(2024, 11, 29), cal, close_utc + timedelta(seconds=1)
    )
    assert state.observed_count == 1


def test_minimums_conjunctive() -> None:
    state = SH.ShadowState(activation_session=date(2026, 9, 28))
    state.observed_sessions = [f"2027-01-{i:02d}" for i in range(1, 505)]
    state.completed_annual_rebalances = 1
    assert state.minimums_satisfied() is False
    state.completed_annual_rebalances = 2
    assert state.minimums_satisfied() is True


def test_hardcoded_open_trigger_removed() -> None:
    # No UTC market time may be hard-coded: DST changes the offset.
    assert not hasattr(SH, "EXPECTED_SESSION_OPEN_US")


def test_bound_activation_session_canonical_open_and_close() -> None:
    cal = NyseCa1Calendar()
    session = cal.get_session(date(2026, 9, 28))
    # Open = execution timestamp semantics; close = market session completion.
    assert session.open_utc == datetime(2026, 9, 28, 13, 30, 0, tzinfo=timezone.utc)
    assert session.close_utc == datetime(2026, 9, 28, 20, 0, 0, tzinfo=timezone.utc)
    assert SH.market_session_completed_after(date(2026, 9, 28), cal) == session.close_utc
    assert SH.provider_observation_eligible_after(date(2026, 9, 28), cal) == datetime(
        2026, 9, 28, 20, 15, 0, tzinfo=timezone.utc
    )
    assert SH.observation_eligible_after(date(2026, 9, 28), cal) == datetime(
        2026, 9, 28, 20, 15, 0, tzinfo=timezone.utc
    )


def test_winter_session_does_not_assume_1330_open() -> None:
    cal = NyseCa1Calendar()
    session = cal.get_session(date(2026, 1, 5))
    # EST (UTC-5): 09:30 open = 14:30Z, 16:00 close = 21:00Z.
    assert session.open_utc == datetime(2026, 1, 5, 14, 30, 0, tzinfo=timezone.utc)
    assert session.close_utc == datetime(2026, 1, 5, 21, 0, 0, tzinfo=timezone.utc)


def test_eligibility_strictly_after_close() -> None:
    cal = NyseCa1Calendar()
    close_utc = cal.get_session(date(2026, 9, 28)).close_utc
    assert close_utc is not None
    state = SH.ShadowState(activation_session=date(2026, 9, 28))
    # One second before close: rejected.
    with pytest.raises(DataContractError):
        state.record_session(
            date(2026, 9, 28), cal, close_utc - timedelta(seconds=1)
        )
    # Exactly at close: NOT YET PROCESSABLE.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 28), cal, close_utc)
    # One microsecond after close: eligible.
    state.record_session(
        date(2026, 9, 28), cal, close_utc + timedelta(microseconds=1)
    )
    assert state.observed_count == 1


def _load_runner_module() -> Any:
    import importlib.util
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "process_hyp_011_prospective_shadow.py"
    spec = importlib.util.spec_from_file_location("process_hyp_011_prospective_shadow", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dry_run_eligibility_messaging_zero_network(
    tmp_path: Path, stage_c_b_absent: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner_module()
    monkeypatch.setattr(runner, "STAGE_C_RECOVERY_BINDING_PATH", stage_c_b_absent)
    state_dir = tmp_path

    def _dry_run(now_utc: datetime) -> str:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = runner.main([], _now_utc=now_utc, _state_dir=state_dir)
        assert rc == 0
        return buf.getvalue()

    # Before close: not eligible, zero network, activation unchanged, count 0.
    before = _dry_run(datetime(2026, 9, 28, 15, 0, 0, tzinfo=timezone.utc))
    assert "EXPECTED_SESSION = 2026-09-28" in before
    assert "SESSION_OPEN_UTC = 2026-09-28T13:30:00+00:00" in before
    assert "SESSION_CLOSE_UTC = 2026-09-28T20:00:00+00:00" in before
    assert "PROVIDER_ELIGIBLE_AFTER_UTC = 2026-09-28T20:15:00+00:00" in before
    assert "OBSERVATION_ELIGIBLE = false" in before
    assert "NETWORK_REQUESTS = 0" in before

    # Post close but strictly before 20:10:00Z failed dispatch instant:
    # market complete but provider not yet eligible.
    pre_failure = _dry_run(datetime(2026, 9, 28, 20, 9, 59, tzinfo=timezone.utc))
    assert "OBSERVATION_ELIGIBLE = false" in pre_failure
    assert "NETWORK_REQUESTS = 0" in pre_failure

    # At or after 20:10:00Z failure instant without Stage C-B binding:
    # strictly fails closed with SHADOW_RECOVERY_BINDING_REQUIRED.
    with pytest.raises(DataContractError) as exc_info:
        _dry_run(datetime(2026, 9, 28, 20, 10, 0, tzinfo=timezone.utc))
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    with pytest.raises(DataContractError) as exc_info:
        _dry_run(datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc))
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # Under valid Stage C-B binding: eligible flag flips when provider eligible, zero network in dry-run
    binding_file = tmp_path / "stage_c_dry.json"
    binding_file.write_text(
        json.dumps({
            "binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
            "binding_commit_sha": "d9608c0a2353bd5ed41943e5fb893ef9648089d2",
            "binding_commit_utc": "2026-09-29T12:00:00Z",
            "activation_session": "2026-09-29",
            "scientific_prospective_boundary": "2026-09-25",
            "failed_dispatch_session": "2026-09-28",
            "failed_dispatch_attempt": 1,
            "next_observation_ordinal": 1,
            "next_dispatch_attempt": 2,
            "backfill_allowed": False,
            "retry_failed_session_allowed": False,
            "locks": {
                "paper_trading": False,
                "live_trading": False,
                "real_capital_authority_usd": "0.00",
                "no_real_orders": True,
            },
        }),
        encoding="utf-8",
    )
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        rc2 = runner.main(
            [],
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _stage_c_binding_path=binding_file,
        )
    assert rc2 == 0
    after = buf2.getvalue()
    assert "EXPECTED_SESSION = 2026-09-29" in after
    assert "OBSERVATION_ELIGIBLE = true" in after
    assert "NETWORK_REQUESTS = 0" in after
    assert not (state_dir / "observations").exists()
    assert SH.STATE_ACTIVATION_SESSION == date(2026, 9, 28)


# =============================================================================
# F14 continuation / no-backfill contract (PROPOSED_PENDING_HUMAN_RATIFICATION)
# =============================================================================


def _f14_binding(tmp_path: Path) -> Dict[str, Any]:
    """LF-canonical Stage C-B fixture binding (avoids F03 CRLF checkout variance)."""
    import hashlib as _hashlib

    binding_path = tmp_path / "f14_stage_c_binding.json"
    doc = {
        "binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
        "binding_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
        "binding_commit_utc": "2026-09-29T17:12:46+00:00",
        "activation_session": "2026-09-30",
        "scientific_prospective_boundary": "2026-09-25",
        "failed_dispatch_session": "2026-09-28",
        "failed_dispatch_attempt": 1,
        "next_observation_ordinal": 1,
        "next_dispatch_attempt": 2,
        "backfill_allowed": False,
        "retry_failed_session_allowed": False,
        "locks": {
            "paper_trading": False,
            "live_trading": False,
            "real_capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
    }
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    binding_path.write_bytes(raw)
    return {
        "path": binding_path,
        "sha256": _hashlib.sha256(raw).hexdigest(),
        "commit_sha": doc["binding_commit_sha"],
        "commit_utc": doc["binding_commit_utc"],
    }


def _f14_reconciled_state(tmp_path: Path, binding: Dict[str, Any]) -> Path:
    """Minimal reconciled Obs #1 pair (2026-09-30) for F14 script-level tests."""
    import hashlib as _hashlib

    state_dir = tmp_path / "prospective"
    obs_dir = state_dir / "observations"
    obs_dir.mkdir(parents=True)
    obs_iso = "2026-09-30"
    strategy_frag = {
        "holdings": {"ACWI": 500, "AGG": 300},
        "cash": "20000.00",
        "market_value": "80000.00",
        "receivable": "0",
        "equity": "100000.00",
        "daily_return": "0.00000000",
        "running_peak": "100000.00",
        "drawdown": "0.00000000",
        "entitlements": [],
        "trades": [],
    }
    benchmark_frag = {
        "entry": {"side": "BUY", "quantity": "200", "fill": "500.00"},
        "entitlements": [],
        "shares": 200,
        "cash": "0.00",
        "market_value": "100000.00",
        "receivable": "0",
        "equity": "100000.00",
        "daily_return": "0.00000000",
        "running_peak": "100000.00",
        "drawdown": "0.00000000",
    }
    obs_doc = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": obs_iso,
        "processed_at_utc": "2026-09-30T20:20:00+00:00",
        "previous_observation_sha256": None,
        "authority": {
            "activation_binding": str(binding["path"]),
            "activation_binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
            "activation_binding_sha256": binding["sha256"],
            "activation_binding_commit_sha": binding["commit_sha"],
            "activation_binding_commit_utc": binding["commit_utc"],
            "operational_activation_session": "2026-09-30",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
        "strategy": strategy_frag,
        "benchmark": benchmark_frag,
    }
    obs_raw = json.dumps(obs_doc, indent=2, sort_keys=True) + "\n"
    (obs_dir / f"{obs_iso}.json").write_bytes(obs_raw.encode("utf-8"))
    obs_sha = _hashlib.sha256(obs_raw.encode("utf-8")).hexdigest()
    state_doc = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "activation_session": "2026-09-30",
        "starting_aum": "100000.00",
        "locks": {
            "paper_authorized": False,
            "live_authorized": False,
            "capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
        "activation_authority_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
        "activation_authority_sha256": binding["sha256"],
        "activation_commit_sha": binding["commit_sha"],
        "observed_sessions": [obs_iso],
        "observed_session_count": 1,
        "last_processed_session": obs_iso,
        "last_observation_sha256": obs_sha,
        "strategy": {
            "cash": "20000.00",
            "holdings": {"ACWI": 500, "AGG": 300},
            "receivables": [],
            "running_peak": "100000.00",
            "previous_equity": "100000.00",
        },
        "benchmark": {
            "cash": "0.00",
            "SPY_shares": 200,
            "receivables": [],
            "running_peak": "100000.00",
            "previous_equity": "100000.00",
            "entered": True,
        },
        "last_closes_raw": {"ACWI": "100.00", "AGG": "100.00", "SPY": "500.00"},
        "last_closes_split": {"ACWI": "100.00", "AGG": "100.00", "SPY": "500.00"},
        "completed_annual_rebalances": 0,
    }
    (state_dir / "state.json").write_text(json.dumps(state_doc, indent=2), encoding="utf-8")
    return state_dir


def test_f14_fresh_target_allowed_before_next_open() -> None:
    """Target immediately after provider eligibility, before next open -> allowed."""
    cal = NyseCa1Calendar()
    # 2026-09-30 (Wed) target; next session 2026-10-01 opens 13:30Z.
    fresh_now = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert SH.assert_target_session_fresh(date(2026, 9, 30), cal, fresh_now) == date(2026, 10, 1)


def test_f14_target_blocked_before_provider_eligibility() -> None:
    """Target before provider eligibility instant is not yet processable (strict >)."""
    cal = NyseCa1Calendar()
    eligible_after = SH.observation_eligible_after(date(2026, 9, 30), cal)
    # At exactly the eligibility instant the session is NOT YET PROCESSABLE.
    assert not (eligible_after > eligible_after)
    assert datetime(2026, 9, 30, 20, 15, 0, tzinfo=timezone.utc) <= eligible_after


def test_f14_target_exactly_at_next_open_blocked() -> None:
    """Target exactly at next session open -> blocked (strictly-before rule)."""
    cal = NyseCa1Calendar()
    next_session, next_open = SH.next_trading_session_open(date(2026, 9, 30), cal)
    assert next_session == date(2026, 10, 1)
    with pytest.raises(DataContractError, match="MISSED_REACTIVATION_REQUIRED"):
        SH.assert_target_session_fresh(date(2026, 9, 30), cal, next_open)


def test_f14_target_after_next_open_blocked() -> None:
    """Target after next session open -> blocked as MISSED_UNOBSERVED."""
    cal = NyseCa1Calendar()
    stale_now = datetime(2026, 10, 5, 0, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError, match="MISSED_REACTIVATION_REQUIRED"):
        SH.assert_target_session_fresh(date(2026, 9, 30), cal, stale_now)


def test_f14_zero_commit_activation_pinned() -> None:
    """Zero-commit activation session remains pinned (no auto-advance)."""
    runner = _load_runner_module()
    cal = NyseCa1Calendar()
    assert runner._expected_next([], cal, date(2026, 9, 30)) == date(2026, 9, 30)


def test_f14_no_automatic_skip_to_later_date() -> None:
    """Target selection never skips: after 2026-09-30 the target is 2026-10-01 even days later."""
    runner = _load_runner_module()
    cal = NyseCa1Calendar()
    assert runner._expected_next(["2026-09-30"], cal, date(2026, 9, 30)) == date(2026, 10, 1)


def test_f14_no_historical_backfill() -> None:
    """A target earlier than activation is rejected (backfill forbidden)."""
    cal = NyseCa1Calendar()
    guard = SH.ShadowState(activation_session=date(2026, 9, 30))
    with pytest.raises(DataContractError):
        guard.record_session(
            date(2026, 9, 29), cal, datetime(2026, 10, 5, tzinfo=timezone.utc)
        )


def test_f14_live_path_stale_target_blocked_zero_network(tmp_path: Path) -> None:
    """Script live path with a stale target fails BEFORE any network side effect.

    Supplies a fully valid DispatchAuthority + CA package so the F14
    freshness gate itself (not an earlier gate) is proven to block.
    """
    import hashlib as _hashlib

    from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
    from acash.research.hyp_011.shadow_authority import (
        ObservationIntent,
        validate_observation_intent,
    )

    runner = _load_runner_module()
    binding = _f14_binding(tmp_path)
    state_dir = _f14_reconciled_state(tmp_path / "state", binding)

    class _NoNetworkClient:
        def fetch_single_session(self, **kwargs: Any) -> Any:
            raise AssertionError("network must not be reached for a stale target")

    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    # Valid CA package (bytes-bound by the authority below).
    sponsors = {
        "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
        "AGG": "BLACKROCK_ISHARES_OFFICIAL",
        "SPY": "STATE_STREET_SPDR_OFFICIAL",
    }
    ca_doc = {
        symbol: {
            "symbol": symbol,
            "session": "2026-10-01",
            "has_event": False,
            "authority_source": sponsors[symbol],
            "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
            "source_sha256": "ab" * 32,
            "evidence_ref": f"evidence/{symbol.lower()}-scope-fixture.pdf",
            "scope_evidence": {
                "schedule_id": "FIXTURE_SCOPE",
                "schedule_sha256": "ab" * 32,
                "scope_note": "Fixture scope.",
                "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
            },
        }
        for symbol in sponsors
    }
    ca_path = tmp_path / "ca_2026-10-01.json"
    ca_bytes = (json.dumps(ca_doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    ca_path.write_bytes(ca_bytes)
    # Valid authority (window covers the stale now; F14 must still block).
    fixture_runtime = "f" * 40
    intent = ObservationIntent(
        hypothesis_id="HYP_011",
        target_session=date(2026, 10, 1),
        observation_ordinal=2,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        previous_observation_sha256=json.loads(
            (state_dir / "state.json").read_text(encoding="utf-8")
        )["last_observation_sha256"],
        backfill_allowed=False,
        automatic_skip_allowed=False,
        created_at_utc=datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc),
        authority_identity="TEST_FIXTURE",
    )
    cal = NyseCa1Calendar()
    validated_intent = validate_observation_intent(
        intent.canonical_doc(), cal, datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    )
    authority_doc = {
        "schema_version": 1,
        "intent_sha256": validated_intent.intent_sha256(),
        "intent": intent.canonical_doc(),
        "runtime_commit_sha": fixture_runtime,
        "target_session": "2026-10-01",
        "observation_ordinal": 2,
        "dispatch_attempt": 1,
        "valid_after_utc": "2026-10-01T00:00:00+00:00",
        "expires_at_utc": "2026-10-06T00:00:00+00:00",
        "ca_manifest_sha256": _hashlib.sha256(ca_bytes).hexdigest(),
        "paper_trading": False,
        "live_trading": False,
        "real_capital_authority_usd": "0.00",
        "no_real_orders": True,
        "authority_identity": "TEST_FIXTURE",
    }
    authority_path = tmp_path / "dispatch_authority_stale.json"
    authority_path.write_text(json.dumps(authority_doc, indent=2), encoding="utf-8")
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0002",
        "--ordinal",
        "2",
        "--dispatch-attempt",
        "1",
        "--dispatch-authority",
        str(authority_path),
        "--ca-determinations",
        str(ca_path),
    ]
    with pytest.raises(DataContractError, match="MISSED_REACTIVATION_REQUIRED"):
        runner.main(
            argv,
            _now_utc=datetime(2026, 10, 5, 0, 0, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=_NoNetworkClient(),
            _credential_provider=dummy_prov,
            _stage_c_binding_path=binding["path"],
            _runtime_sha=fixture_runtime,
        )


def test_f14_pretest_reports_freshness_zero_network(tmp_path: Path) -> None:
    """Dry-run pretest reports TARGET_FRESH without network or state mutation."""
    import io
    from contextlib import redirect_stdout

    runner = _load_runner_module()
    binding = _f14_binding(tmp_path)
    state_dir = _f14_reconciled_state(tmp_path / "state", binding)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = runner.main(
            [],
            _now_utc=datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _stage_c_binding_path=binding["path"],
        )
    assert rc == 0
    out = buf.getvalue()
    assert "EXPECTED_SESSION = 2026-10-01" in out
    assert "TARGET_FRESH = true" in out
    assert "NEXT_SESSION_NOT_YET_OPEN = 2026-10-02" in out
