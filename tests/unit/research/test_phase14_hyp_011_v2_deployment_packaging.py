"""HYP_011 V2 deployment-packaging finalization tests.

Proves the Authority-A / Authority-B separation: no timer installed under
Authority A, the wrapper installs outside the repo, deployment preflight is
distinct from dispatch preflight (no runner, no activation authority, zero
network, secrets never printed), and every packaging contract fails closed.

Wrapper-execution tests need a working `bash` and are skipped otherwise
(CI provides one); template/runbook text assertions always run.
"""

import getpass
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest

SENTINEL_ID = "SENTINEL_KEY_ID_9f8e7d6c5b"
SENTINEL_SECRET = "SENTINEL_SECRET_1a2b3c4d5e"


def _bash() -> str:
    exe = shutil.which("bash")
    if exe is None:
        pytest.skip("bash unavailable for wrapper execution tests")
        raise AssertionError("unreachable")
    try:
        probe = subprocess.run(
            [exe, "--version"], capture_output=True, timeout=30
        )
    except OSError:
        pytest.skip("bash unavailable for wrapper execution tests")
        raise AssertionError("unreachable")
    if probe.returncode != 0:
        pytest.skip("bash unavailable for wrapper execution tests")
        raise AssertionError("unreachable")
    return exe


def _wrapper_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "operations"
        / "acash-hyp011-v2.sh"
    )


def _git(args: List[str], cwd: Path) -> None:
    subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        check=True,
        timeout=60,
    )


@pytest.fixture
def synth(tmp_path: Path) -> Dict[str, Any]:
    """Synthetic deployment environment (never the real repo, never /etc)."""
    repo = tmp_path / "repo"
    (repo / "docs" / "operations").mkdir(parents=True)
    (repo / "docs" / "operations" / "acash-hyp011-v2.service").write_text(
        "[Service]\n", encoding="utf-8"
    )
    (repo / "data" / "hyp_011" / "prospective").mkdir(parents=True)
    (repo / ".venv" / "bin").mkdir(parents=True)
    python_stub = repo / ".venv" / "bin" / "python"
    python_stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    os.chmod(python_stub, 0o755)
    _git(["init", "-q", str(repo)], tmp_path)
    (repo / "README.md").write_text("synthetic\n", encoding="utf-8")
    _git(["-C", str(repo), "add", "."], tmp_path)
    _git(
        [
            "-C",
            str(repo),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "synthetic",
        ],
        tmp_path,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.strip()
    state_root = tmp_path / "v2state"
    state_root.mkdir()
    os.chmod(state_root, 0o700)
    secrets = tmp_path / "hyp011-v2.env"
    secrets.write_text(
        f"ACASH_ALPACA_API_KEY_ID={SENTINEL_ID}\n"
        f"ACASH_ALPACA_API_SECRET={SENTINEL_SECRET}\n",
        encoding="utf-8",
    )
    os.chmod(secrets, 0o600)
    unit_dir = tmp_path / "systemd"
    unit_dir.mkdir()
    env = dict(os.environ)
    env.update(
        {
            "ACASH_REPO": str(repo),
            "V2_STATE_ROOT": str(state_root),
            "V2_SECRETS_FILE": str(secrets),
            "APPROVED_RUNTIME_SHA": head,
            "ACASH_EXPECTED_USER": getpass.getuser(),
            "SYSTEMD_UNIT_DIR": str(unit_dir),
            "SYSTEMCTL": "definitely-not-a-systemctl-binary",
        }
    )
    return {
        "repo": repo,
        "state_root": state_root,
        "secrets": secrets,
        "unit_dir": unit_dir,
        "env": env,
        "head": head,
    }


def _preflight(synth: Dict[str, Any]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [_bash(), str(_wrapper_path()), "--deployment-preflight"],
        capture_output=True,
        text=True,
        timeout=60,
        env=synth["env"],
    )


def test_deployment_preflight_pass(synth: Dict[str, Any]) -> None:
    proc = _preflight(synth)
    assert proc.returncode == 0
    assert "DEPLOYMENT_PREFLIGHT = PASS" in proc.stdout
    assert "NETWORK_REQUESTS = 0" in proc.stdout
    assert "V2_STATE_CREATED = false" in proc.stdout
    assert "V2_ACTIVATION_AUTHORITY_CREATED = false" in proc.stdout
    assert "V2_TIMER_INSTALLED = false" in proc.stdout
    # The synthetic repo has no runner at all: PASS proves the runner is
    # never invoked on the deployment-preflight path.
    assert not (synth["repo"] / "scripts").exists()
    # Nothing materialized in the external state root ...
    assert not (synth["state_root"] / "state.json").exists()
    # ... and secret values never appear on stdout.
    assert SENTINEL_ID not in proc.stdout
    assert SENTINEL_SECRET not in proc.stdout


def test_deployment_preflight_rejects_wrong_runtime_sha(
    synth: Dict[str, Any],
) -> None:
    synth["env"]["APPROVED_RUNTIME_SHA"] = "0" * 40
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_missing_runtime_sha(
    synth: Dict[str, Any],
) -> None:
    del synth["env"]["APPROVED_RUNTIME_SHA"]
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_dirty_checkout(
    synth: Dict[str, Any],
) -> None:
    (synth["repo"] / "uncommitted.txt").write_text("x", encoding="utf-8")
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_bad_state_mode(
    synth: Dict[str, Any],
) -> None:
    os.chmod(synth["state_root"], 0o755)
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_bad_state_owner(
    synth: Dict[str, Any],
) -> None:
    synth["env"]["ACASH_EXPECTED_USER"] = "definitely-not-the-owner"
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_bad_secrets_mode(
    synth: Dict[str, Any],
) -> None:
    os.chmod(synth["secrets"], 0o644)
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_missing_credential_name(
    synth: Dict[str, Any],
) -> None:
    synth["secrets"].write_text(
        f"ACASH_ALPACA_API_KEY_ID={SENTINEL_ID}\n", encoding="utf-8"
    )
    os.chmod(synth["secrets"], 0o600)
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_installed_timer(
    synth: Dict[str, Any],
) -> None:
    (synth["unit_dir"] / "acash-hyp011-v2.timer").write_text(
        "[Timer]\n", encoding="utf-8"
    )
    assert _preflight(synth).returncode != 0


def test_deployment_preflight_rejects_repo_nested_state_root(
    synth: Dict[str, Any],
) -> None:
    nested = synth["repo"] / "v2state"
    nested.mkdir()
    os.chmod(nested, 0o700)
    synth["env"]["V2_STATE_ROOT"] = str(nested)
    assert _preflight(synth).returncode != 0


def test_service_uses_installed_wrapper_path() -> None:
    service = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "operations"
        / "acash-hyp011-v2.service"
    ).read_text(encoding="utf-8")
    assert "ExecStart=/usr/local/sbin/acash-hyp011-v2 " in service
    assert "--segment-activation-authority" in service
    # The oneshot service must not introduce automatic startup: no real
    # [Install] section (mentions in comments do not count).
    assert not any(
        line.strip() == "[Install]" for line in service.splitlines()
    )


def test_runbook_authority_a_installs_no_timer() -> None:
    runbook = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "operations"
        / "HYP_011_V2_HOMELAB_DEPLOYMENT.md"
    ).read_text(encoding="utf-8")
    # No timer COPY into systemd anywhere in the deployment runbook: the
    # bare template is never installed (Authority B generates the unit with
    # a validated trigger instead).
    for line in runbook.splitlines():
        if "acash-hyp011-v2.timer" in line and "/etc/systemd/system" in line:
            assert "cp " not in line, line
    # No wrapper self-copy back into the tracked checkout (either spelling).
    assert "cp docs/operations/acash-hyp011-v2.sh /home/mew/Acash/docs/operations/" not in runbook
    assert (
        "cp /home/mew/Acash/docs/operations/acash-hyp011-v2.sh "
        "/home/mew/Acash/docs/operations/" not in runbook
    )
    # ... and no chmod mutation of tracked files (state-root 700 and
    # secrets 600 chmods elsewhere in the runbook are legitimate).
    assert "chmod +x" not in runbook
    # Installed copy contract instead.
    assert "/usr/local/sbin/acash-hyp011-v2" in runbook
    assert "install -o root -g root -m 0755" in runbook
    # Deployment preflight is the Authority-A check.
    assert "--deployment-preflight" in runbook
    assert "DEPLOYMENT_PREFLIGHT = PASS" in runbook
    # Mode bits of the tracked wrapper stay 0644 (no +x in git).
    mode = stat.S_IMODE(
        os.stat(
            Path(__file__).resolve().parents[3]
            / "docs"
            / "operations"
            / "acash-hyp011-v2.sh"
        ).st_mode
    )
    assert mode & 0o111 == 0
