"""HYP_011 V2 deployment-prep offline contract tests.

Fresh segment / external runtime state / NO activation.

Hermetic only: tmp_path state roots, zero network, no Homelab mutation,
no V1 evidence writes. Proves the V2 CLI/state-dir/segment contract and
the deployment-manifest binding before any deployment authorization.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow import assert_target_session_fresh
from acash.research.hyp_011.shadow_ops import (
    build_initial_state,
    verify_chain,
)

SEGMENT_ID_V2 = "HYP_011_PROSPECTIVE_V2"
V2_STATE_ROOT = "/var/lib/acash/hyp011/v2"


def _load_runner_module() -> Any:
    import importlib.util

    script_path = Path(__file__).resolve().parents[3] / "scripts" / "process_hyp_011_prospective_shadow.py"
    spec = importlib.util.spec_from_file_location("process_hyp_011_prospective_shadow_v2", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_v2_initial_state_fresh_and_locked() -> None:
    state = build_initial_state(segment_id=SEGMENT_ID_V2)
    assert state["segment_id"] == SEGMENT_ID_V2
    assert state["hypothesis_id"] == "HYP_011"
    # Fresh segment: no carried observations, ordinal starts at 1, S1 at 0/20.
    assert state["observed_sessions"] == []
    assert state["observed_session_count"] == 0
    # Economic identity: fresh simulated AUM, zero real capital.
    assert state["starting_aum"] == "100000.00"
    locks = state["locks"]
    assert locks["paper_authorized"] is False
    assert locks["live_authorized"] is False
    assert str(locks["capital_authority_usd"]) == "0.00"
    assert locks["no_real_orders"] is True


def test_v1_initial_state_has_no_segment() -> None:
    state = build_initial_state()
    assert "segment_id" not in state


def test_v1_state_rejected_in_v2_root(tmp_path: Path) -> None:
    # A V1 state document (no segment_id) must never validate as V2.
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(build_initial_state()), encoding="utf-8")
    with pytest.raises(DataContractError):
        verify_chain(tmp_path, expected_segment_id=SEGMENT_ID_V2)


def test_v2_state_rejected_without_segment_expectation(tmp_path: Path) -> None:
    # A V2 state document must never validate as a V1 (segment-less) root.
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(build_initial_state(segment_id=SEGMENT_ID_V2)), encoding="utf-8"
    )
    with pytest.raises(DataContractError):
        verify_chain(tmp_path)


def test_runner_rejects_relative_state_dir(tmp_path: Path) -> None:
    runner = _load_runner_module()
    with pytest.raises(DataContractError):
        runner.main(
            [
                "--state-dir",
                "relative/v2-state",
                "--segment-id",
                SEGMENT_ID_V2,
            ],
            _now_utc=datetime(2026, 9, 28, 15, 0, 0, tzinfo=timezone.utc),
            _state_dir=tmp_path,
        )


def test_runner_rejects_v1_evidence_overlap() -> None:
    runner = _load_runner_module()
    repo_root = Path(__file__).resolve().parents[3]
    v1_probe = repo_root / "data" / "hyp_011" / "prospective" / "v2probe"
    with pytest.raises(DataContractError):
        runner.main(
            [
                "--state-dir",
                str(v1_probe),
                "--segment-id",
                SEGMENT_ID_V2,
            ],
            _now_utc=datetime(2026, 9, 28, 15, 0, 0, tzinfo=timezone.utc),
        )


def test_runner_rejects_bad_segment_id(tmp_path: Path) -> None:
    runner = _load_runner_module()
    with pytest.raises(DataContractError):
        runner.main(
            [
                "--state-dir",
                str(tmp_path / "v2"),
                "--segment-id",
                "HYP_011_PROSPECTIVE_V1",
            ],
            _now_utc=datetime(2026, 9, 28, 15, 0, 0, tzinfo=timezone.utc),
        )


def test_runner_rejects_segment_without_state_dir() -> None:
    runner = _load_runner_module()
    with pytest.raises(DataContractError):
        runner.main(
            ["--segment-id", SEGMENT_ID_V2],
            _now_utc=datetime(2026, 9, 28, 15, 0, 0, tzinfo=timezone.utc),
        )


def test_v2_dry_run_zero_network_isolated(
    tmp_path: Path, capsys: Any, stage_c_b_absent: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner_module()
    monkeypatch.setattr(runner, "STAGE_C_RECOVERY_BINDING_PATH", stage_c_b_absent)
    v2_root = tmp_path / "v2-external"
    repo_root = Path(__file__).resolve().parents[3]
    v1_state = repo_root / "data" / "hyp_011" / "prospective" / "state.json"
    v1_before = v1_state.read_bytes() if v1_state.is_file() else None
    # V2 dry-run derives its target SOLELY from the SegmentActivationAuthority
    # (here: fresh prospective session 2026-09-29), never from V1 machinery.
    activation_path = tmp_path / "segment_activation_authority.json"
    activation_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "segment_id": SEGMENT_ID_V2,
                "hypothesis_id": "HYP_011",
                "activation_session": "2026-09-29",
                "runtime_commit_sha": "e" * 40,
                "starting_aum": "100000.00",
                "paper_trading": False,
                "live_trading": False,
                "real_capital_authority_usd": "0.00",
                "no_real_orders": True,
                "authorized_at_utc": "2026-09-28T12:00:00+00:00",
                "authority_identity": "TEST_V2",
            }
        ),
        encoding="utf-8",
    )
    assert (
        runner.main(
            [
                "--state-dir",
                str(v2_root),
                "--segment-id",
                SEGMENT_ID_V2,
                "--segment-activation-authority",
                str(activation_path),
                "--runtime-sha",
                "e" * 40,
            ],
            _now_utc=datetime(2026, 9, 28, 15, 0, 0, tzinfo=timezone.utc),
        )
        == 0
    )
    out = capsys.readouterr().out
    assert f"STATE_DIR = {v2_root}" in out
    assert f"SEGMENT_ID = {SEGMENT_ID_V2}" in out
    assert "PRETEST" in out
    assert "EXPECTED_SESSION = 2026-09-29" in out
    assert "NETWORK_REQUESTS = 0" in out
    # Dry-run is read-only: no state materialized in the external root ...
    assert not (v2_root / "state.json").exists()
    # ... and V1 evidence bytes are untouched.
    if v1_before is not None:
        assert v1_state.read_bytes() == v1_before


def test_missed_session_contract_still_fail_closed() -> None:
    calendar = NyseCa1Calendar()
    # Target 2026-09-28 while the next session (2026-09-29) has already
    # opened: stale target must fail closed with zero network.
    with pytest.raises(DataContractError):
        assert_target_session_fresh(
            date(2026, 9, 28),
            calendar,
            datetime(2026, 9, 29, 15, 0, 0, tzinfo=timezone.utc),
        )


def test_v2_manifest_binding() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    ops = repo_root / "docs" / "operations"
    service = (ops / "acash-hyp011-v2.service").read_text(encoding="utf-8")
    assert "ReadWritePaths=/var/lib/acash/hyp011/v2" in service
    assert "EnvironmentFile=/etc/acash/hyp011-v2.env" in service
    assert "Restart=no" in service
    # No V1 unit names reused.
    assert "acash-hyp011-observation-0001" not in service
    wrapper = (ops / "acash-hyp011-v2.sh").read_text(encoding="utf-8")
    assert 'STATE_ROOT="${V2_STATE_ROOT:-/var/lib/acash/hyp011/v2}"' in wrapper
    assert 'SEGMENT_ID="HYP_011_PROSPECTIVE_V2"' in wrapper
    assert 'SECRETS_FILE="${V2_SECRETS_FILE:-/etc/acash/hyp011-v2.env}"' in wrapper
    assert "--deployment-preflight" in wrapper
    assert "DEPLOYMENT_PREFLIGHT = PASS" in wrapper
    assert "process_hyp_011_prospective_shadow.py" in wrapper
    assert "--state-dir" in wrapper
    assert "--segment-id" in wrapper
    timer = (ops / "acash-hyp011-v2.timer").read_text(encoding="utf-8")
    assert "AUTHORIZE_HYP_011_V2_ACTIVATION" in timer
    # Enabling the timer must never pull the service up immediately.
    assert "Requires=acash-hyp011-v2.service" not in timer
    assert "Unit=acash-hyp011-v2.service" in timer
    assert "RemainAfterElapse=false" in timer
    assert not any(
        line.strip().startswith("OnCalendar=")
        for line in timer.splitlines()
    )
    # The activation drop-in shape clears stale values before setting the
    # validated calendar-derived expression.
    assert "OnCalendar=" in timer
    assert (ops / "HYP_011_V2_HOMELAB_DEPLOYMENT.md").is_file()
    runbook = (ops / "HYP_011_V2_HOMELAB_DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "49b26f1" not in runbook
    assert "APPROVED_RUNTIME_SHA" in runbook
    assert not any(
        line.strip().startswith("Timezone=") for line in runbook.splitlines()
    )
    assert V2_STATE_ROOT == "/var/lib/acash/hyp011/v2"
