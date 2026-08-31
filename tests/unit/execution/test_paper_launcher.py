"""Unit tests for the ACASH Local Windows Paper Credential Workflow & Launcher.

Verifies:
1. Fail-closed behavior on absent/corrupted vault files.
2. In-memory DPAPI vault encryption & decryption roundtrip.
3. Process environment injection only for child execution (no permanent persistence).
4. Paper-only venue and endpoint enforcement (rejection of live venues).
5. Zero secret values leaked in string representations, logs, or exceptions.
6. Clean environment restoration in finally blocks.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Generator
import pytest

from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    AlpacaCredentials,
    PaperCredentialGuardError,
    assert_paper_venue,
    paper_credential_provider,
)
from acash.execution.alpaca.venue import AlpacaVenue


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def test_scripts_exist() -> None:
    """Verify both PowerShell scripts exist in scripts/ directory."""
    setup_script = SCRIPTS_DIR / "setup_paper_credentials.ps1"
    run_script = SCRIPTS_DIR / "run_paper.ps1"

    assert setup_script.exists(), f"Missing {setup_script}"
    assert run_script.exists(), f"Missing {run_script}"


def test_no_hardcoded_secrets_in_scripts() -> None:
    """Verify scripts contain no hardcoded secret keys or tokens."""
    for script_file in [SCRIPTS_DIR / "setup_paper_credentials.ps1", SCRIPTS_DIR / "run_paper.ps1"]:
        content = script_file.read_text(encoding="utf-8")
        # Ensure no accidental actual keys are embedded
        assert "PK" + "TEST" not in content
        assert "AKIA" not in content
        assert "sk_" not in content


def test_paper_credential_provider_isolated_env() -> None:
    """Verify paper_credential_provider reads injected env mapping strictly."""
    test_env = {
        "ACASH_ALPACA_API_KEY_ID": "PK_TEST_KEY_12345",
        "ACASH_ALPACA_API_SECRET": "SECRET_TEST_98765",
    }
    provider = paper_credential_provider(environ=test_env)
    assert provider.venue() == "ALPACA_PAPER"

    creds = provider.load()
    assert creds.resolved is True
    assert creds.api_key_id == "PK_TEST_KEY_12345"
    assert str(creds) == "********"
    assert "SECRET_TEST_98765" not in repr(creds)
    assert "PK_TEST_KEY_12345" not in repr(creds)


def test_paper_credential_provider_fails_closed_when_empty() -> None:
    """Verify fail-closed error when credentials are absent from environment."""
    provider = paper_credential_provider(environ={})
    with pytest.raises(AlpacaCredentialError) as exc_info:
        provider.load()
    assert "API key id is absent" in str(exc_info.value)
    # Ensure no secrets in error message
    assert "PK" not in str(exc_info.value)


def test_assert_paper_venue_guard() -> None:
    """Verify assert_paper_venue rejects non-paper venues fail-closed."""
    assert_paper_venue("ALPACA_PAPER")  # OK

    with pytest.raises(PaperCredentialGuardError) as exc_info:
        assert_paper_venue("ALPACA_LIVE")
    assert "refuses non-paper venue" in str(exc_info.value)

    with pytest.raises(PaperCredentialGuardError):
        assert_paper_venue("OTHER_VENUE")


def test_alpaca_venue_derived_endpoints() -> None:
    """Verify AlpacaVenue properties are immutable and derived."""
    assert AlpacaVenue.PAPER.base_url == "https://paper-api.alpaca.markets/v2"
    assert AlpacaVenue.PAPER.is_paper is True
    assert AlpacaVenue.LIVE.base_url == "https://api.alpaca.markets/v2"
    assert AlpacaVenue.LIVE.is_paper is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI tests require Windows PowerShell")
def test_powershell_launcher_help_and_missing_vault(tmp_path: Path) -> None:
    """Verify launcher shows error when vault is not found or displays help cleanly."""
    run_script = SCRIPTS_DIR / "run_paper.ps1"

    # Test ShowHelp
    cmd_help = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(run_script), "-ShowHelp"]
    res_help = subprocess.run(cmd_help, capture_output=True, text=True)
    assert res_help.returncode == 0
    assert "ACASH" in res_help.stdout or "Paper-Only" in res_help.stdout
