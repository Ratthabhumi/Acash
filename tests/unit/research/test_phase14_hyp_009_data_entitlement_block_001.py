"""Governance tests for HYP_009 operational entitlement block 001.

Proves the non-falsifying block: credentials absent, provider fail-closed,
protected R1 lineage untouched, zero empirical activity. No network calls.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

import pytest

from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BLOCK_DOC = REPO_ROOT / "docs" / "phase14" / "HYP_009_DATA_ENTITLEMENT_BLOCK_001.md"
BLOCK_MANIFEST = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_DATA_ENTITLEMENT_BLOCK_001.json"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_block_status_non_falsifying_and_resumable() -> None:
    m = _load(BLOCK_MANIFEST)
    assert m["current_status"] == "BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT"
    assert m["hypothesis_falsified"] is False
    assert m["hypothesis_rejected"] is False
    assert m["strategy_pnl_observed"] is False
    assert m["backtest_started"] is False
    assert m["r2_dataset_build"] == "NOT_STARTED"
    assert m["resumable"] is True


def test_credential_provider_fail_closed_no_secrets_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Future-safe: isolate via monkeypatch so this historical fail-closed proof holds
    # even after real credentials are installed for authorized R2 resumption.
    # Never reads, prints, hashes, or logs secret values — only removes the names.
    m = _load(BLOCK_MANIFEST)
    assert m["missing_credentials"] == [
        "ACASH_ALPACA_API_KEY_ID",
        "ACASH_ALPACA_API_SECRET",
    ]
    monkeypatch.delenv("ACASH_ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ACASH_ALPACA_API_SECRET", raising=False)
    try:
        EnvAlpacaCredentialProvider().load()
        raise AssertionError("credential provider must fail closed without credentials")
    except AlpacaCredentialError:
        pass
    assert m["credential_check_result"] == "AlpacaCredentialError_RAISED_FAIL_CLOSED"
    assert m["network_requests_issued"] == 0


def test_zero_empirical_activity() -> None:
    m = _load(BLOCK_MANIFEST)
    assert m["hyp_007_empirical_reads"] == 0
    assert m["m2_access"] == "ZERO"
    assert m["m3_access"] == "ZERO"
    assert m["quarantine_access"] == "ZERO"
    assert m["prospective_access"] == "ZERO"
    assert m["paper_authorized"] is False
    assert m["live_authorized"] is False
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True


def test_block_doc_states() -> None:
    assert BLOCK_DOC.is_file()
    text = BLOCK_DOC.read_text(encoding="utf-8")
    assert "BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT" in text
    assert "HYP_009_STATUS = BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT" in text
    assert "ACASH_ALPACA_API_KEY_ID" in text
    assert "AUTHORIZE_CORE_001_HYP_009_PRE_R2_ACCOUNTING_CLARIFICATION_AND_R2_M1_EXECUTION" in (
        _load(BLOCK_MANIFEST)["authorization"]
    )


def test_protected_artifacts_exist() -> None:
    m = _load(BLOCK_MANIFEST)
    for rel in m["protected_artifacts_untouched"]:
        assert (REPO_ROOT / rel).is_file(), f"protected artifact missing: {rel}"
    hyp_sha = hashlib.sha256(
        (REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_009.json").read_bytes()
    ).hexdigest()
    assert hyp_sha == "fb855542e86aa91139a0c7cdbedaad60de113ccbf679fe3e12a7465bcae13f2d"
