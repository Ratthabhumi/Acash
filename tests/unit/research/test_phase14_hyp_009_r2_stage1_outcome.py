"""Governance tests for HYP_009 R2 Stage-1 credential-check outcome.

Proves the §4 fail-closed stop with zero network activity. Monkeypatch-isolated:
valid regardless of future outer-environment credentials. No secret inspection.
"""

import json
from pathlib import Path
from typing import Any, Dict, cast

import pytest

from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTCOME_DOC = REPO_ROOT / "docs" / "phase14" / "HYP_009_R2_STAGE1_CREDENTIAL_CHECK_OUTCOME.md"
OUTCOME_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_009_R2_STAGE1_CREDENTIAL_CHECK_OUTCOME.json"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_stage1_outcome_is_credential_block_no_stage2() -> None:
    m = _load(OUTCOME_MANIFEST)
    assert m["authorization"] == (
        "AUTHORIZE_CORE_001_HYP_009_R2_PROVIDER_QUALIFICATION_AND_M1_EXECUTION"
    )
    assert m["classification"] == "BLOCKED_PRE_ENTITLEMENT_CHECK_MISSING_CREDENTIALS"
    assert m["network_requests_issued"] == 0
    assert m["stage_2_executed"] is False
    assert m["pre_check_contracts_verified"] is True
    assert m["hypothesis_falsified"] is False
    assert m["r2_dataset_build"] == "NOT_STARTED"


def test_fail_closed_reproducible_under_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ACASH_ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ACASH_ALPACA_API_SECRET", raising=False)
    try:
        EnvAlpacaCredentialProvider().load()
        raise AssertionError("must fail closed without credentials")
    except AlpacaCredentialError:
        pass
    m = _load(OUTCOME_MANIFEST)
    assert m["credential_check_result"] == "AlpacaCredentialError_RAISED_FAIL_CLOSED"
    assert m["key_id_present"] is False
    assert m["secret_present"] is False


def test_outcome_doc_states() -> None:
    assert OUTCOME_DOC.is_file()
    text = OUTCOME_DOC.read_text(encoding="utf-8")
    assert "BLOCKED_PRE_ENTITLEMENT_CHECK_MISSING_CREDENTIALS" in text
    assert "STAGE_2: NOT_AUTHORIZED_BY_THIS_OUTCOME" in text
    assert "PROVIDE_HYP_009_R2_ALPACA_CREDENTIALS_AND_REAUTHORIZE_PROVIDER_QUALIFICATION" in text
