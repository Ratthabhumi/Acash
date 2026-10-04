"""HYP_011 V2 unattended preflight gate tests.

Proves the elapse-time gating contract: the service runs the FULL
zero-network dispatch preflight via ExecStartPre before the live
ExecStart, so Authority B can arm the timer before session close while a
preflight failure still blocks all market-data transport.

Wrapper dispatch-argument tests execute the real wrapper with a stub
interpreter that records argv (needs `bash`; skipped otherwise). Template
and runbook text assertions always run. No network, no Homelab mutation.
"""

import getpass
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest


def _bash() -> str:
    exe = shutil.which("bash")
    if exe is None:
        pytest.skip("bash unavailable for wrapper execution tests")
        raise AssertionError("unreachable")
    try:
        probe = subprocess.run([exe, "--version"], capture_output=True, timeout=30)
    except OSError:
        pytest.skip("bash unavailable for wrapper execution tests")
        raise AssertionError("unreachable")
    if probe.returncode != 0:
        pytest.skip("bash unavailable for wrapper execution tests")
        raise AssertionError("unreachable")
    return exe


def _ops_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "operations"


def _service_lines() -> List[str]:
    return (_ops_dir() / "acash-hyp011-v2.service").read_text(encoding="utf-8").splitlines()


def _exec_start_pre() -> str:
    for line in _service_lines():
        if line.strip().startswith("ExecStartPre="):
            return line.strip()
    raise AssertionError("service template has no ExecStartPre")


def _exec_start() -> str:
    for line in _service_lines():
        if line.strip().startswith("ExecStart=") and not line.strip().startswith(
            "ExecStartPre="
        ):
            return line.strip()
    raise AssertionError("service template has no ExecStart")


def test_service_gates_dispatch_behind_preflight() -> None:
    pre = _exec_start_pre()
    start = _exec_start()
    # Preflight first, dispatch second.
    lines = _service_lines()
    pre_idx = next(
        i for i, line in enumerate(lines) if line.strip().startswith("ExecStartPre=")
    )
    start_idx = next(
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("ExecStart=")
        and not line.strip().startswith("ExecStartPre=")
    )
    assert pre_idx < start_idx
    # Modes are distinct and correct.
    assert "--local-preflight" in pre
    assert "--execute-network" not in pre
    assert "--execute-network" in start
    assert "--local-preflight" not in start
    # Bare mode flags only: no shell-style interpolation that could degrade
    # into empty expansions. Session bindings travel via drop-in Environment
    # and the wrapper builds both invocations deterministically from them
    # (proven by the stub-recording tests below).
    assert "${" not in pre
    assert "${" not in start
    assert pre.strip() == "ExecStartPre=/usr/local/sbin/acash-hyp011-v2 --local-preflight"
    assert start.strip() == "ExecStart=/usr/local/sbin/acash-hyp011-v2 --execute-network"
    # No retry anywhere: a failed gate stays failed.
    assert "Restart=no" in lines


def test_runbook_documents_elapse_time_gating() -> None:
    runbook = (
        _ops_dir() / "HYP_011_V2_HOMELAB_DEPLOYMENT.md"
    ).read_text(encoding="utf-8")
    # Pre-arm dispatch preflight is gone: it cannot pass before close.
    assert "arm the timer on a failed preflight" not in runbook
    assert "SHADOW_INCOMPLETE_SESSION" in runbook
    assert "ExecStartPre" in runbook
    assert "Post-Elapse" in runbook


@pytest.fixture
def dispatch_env(tmp_path: Path) -> Dict[str, Any]:
    """Synthetic dispatch environment with a stub interpreter recording argv."""
    repo = tmp_path / "repo"
    repo.mkdir()
    arglog = tmp_path / "argv.log"
    stub = tmp_path / "python-stub.sh"
    stub.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" >> "$ARGLOG"\n', encoding="utf-8")
    os.chmod(stub, 0o755)
    state_root = tmp_path / "v2state"
    state_root.mkdir()
    os.chmod(state_root, 0o700)
    secrets = tmp_path / "hyp011-v2.env"
    secrets.write_text(
        "ACASH_ALPACA_API_KEY_ID=SYNTH_ID\nACASH_ALPACA_API_SECRET=SYNTH_SEC\n",
        encoding="utf-8",
    )
    os.chmod(secrets, 0o600)
    env = dict(os.environ)
    env.update(
        {
            "ACASH_REPO": str(repo),
            "V2_STATE_ROOT": str(state_root),
            "V2_SECRETS_FILE": str(secrets),
            "V2_PYTHON_BIN": str(stub),
            "ACASH_EXPECTED_USER": getpass.getuser(),
            "SYSTEMCTL": "definitely-not-a-systemctl-binary",
            "ARGLOG": str(arglog),
            "AUTHORIZATION": "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001",
            "ORDINAL": "1",
            "DISPATCH_ATTEMPT": "1",
            "DISPATCH_AUTHORITY": str(tmp_path / "dispatch_authority.json"),
            "RUNTIME_SHA": "e" * 40,
            "SEGMENT_ACTIVATION_AUTHORITY": str(tmp_path / "activation.json"),
        }
    )
    return {"env": env, "arglog": arglog}


def _recorded_argv(dispatch_env: Dict[str, Any]) -> List[str]:
    content = dispatch_env["arglog"].read_text(encoding="utf-8")
    return [line for line in content.splitlines() if line]


def test_wrapper_preflight_omits_absent_ca_args(dispatch_env: Dict[str, Any]) -> None:
    proc = subprocess.run(
        [_bash(), str(_ops_dir() / "acash-hyp011-v2.sh"), "--local-preflight"],
        capture_output=True,
        text=True,
        timeout=60,
        env=dispatch_env["env"],
    )
    assert proc.returncode == 0
    argv = _recorded_argv(dispatch_env)
    # V2 ordinal 1 carries no CA file: no empty expansions, no fabrication.
    assert "--local-preflight" in argv
    assert "--execute-network" not in argv
    assert "--ca-determinations" not in argv
    assert "--ca-evidence-bundle" not in argv
    assert "" not in argv
    for flag in (
        "--state-dir",
        "--segment-id",
        "--authorization",
        "--ordinal",
        "--dispatch-attempt",
        "--dispatch-authority",
        "--runtime-sha",
        "--segment-activation-authority",
    ):
        assert flag in argv, flag


def test_wrapper_dispatch_includes_supplied_ca_args(
    dispatch_env: Dict[str, Any], tmp_path: Path
) -> None:
    ca_file = tmp_path / "ca.json"
    ca_file.write_text("{}", encoding="utf-8")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    dispatch_env["env"]["CA_DETERMINATIONS"] = str(ca_file)
    dispatch_env["env"]["CA_EVIDENCE_BUNDLE"] = str(bundle)
    proc = subprocess.run(
        [_bash(), str(_ops_dir() / "acash-hyp011-v2.sh"), "--execute-network"],
        capture_output=True,
        text=True,
        timeout=60,
        env=dispatch_env["env"],
    )
    assert proc.returncode == 0
    argv = _recorded_argv(dispatch_env)
    assert "--execute-network" in argv
    assert "--local-preflight" not in argv
    assert argv[argv.index("--ca-determinations") + 1] == str(ca_file)
    assert argv[argv.index("--ca-evidence-bundle") + 1] == str(bundle)


def test_wrapper_rejects_extra_args(dispatch_env: Dict[str, Any]) -> None:
    proc = subprocess.run(
        [
            _bash(),
            str(_ops_dir() / "acash-hyp011-v2.sh"),
            "--local-preflight",
            "--ordinal",
            "2",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=dispatch_env["env"],
    )
    assert proc.returncode != 0
    assert not dispatch_env["arglog"].exists()


def test_wrapper_rejects_missing_binding(dispatch_env: Dict[str, Any]) -> None:
    del dispatch_env["env"]["AUTHORIZATION"]
    proc = subprocess.run(
        [_bash(), str(_ops_dir() / "acash-hyp011-v2.sh"), "--local-preflight"],
        capture_output=True,
        text=True,
        timeout=60,
        env=dispatch_env["env"],
    )
    assert proc.returncode != 0
    assert not dispatch_env["arglog"].exists()
