"""Governance tests for HYP_009 pre-R2 execution-accounting clarification.

Sealed pre-result: asserts bookkeeping bindings and upstream pins. No market-data
access, no computation beyond hash verification over committed artifacts.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

from acash.core.serialization import CanonicalConfigSerializer

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAR_DOC = REPO_ROOT / "docs" / "phase14" / "HYP_009_PRE_R2_EXECUTION_ACCOUNTING_CLARIFICATION.md"
CLAR_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_009_PRE_R2_EXECUTION_ACCOUNTING_CLARIFICATION.json"
)
R1_MANIFEST = REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_009.json"
HYP_PATH = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_009.json"
PREREG = REPO_ROOT / "docs" / "research" / "CORE-001-HYP-009-strategy-preregistration.md"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_simulated_aum_distinguished_from_capital() -> None:
    m = _load(CLAR_MANIFEST)
    assert m["simulated_starting_aum_usd"] == "100000.00"
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True


def test_whole_share_and_cash_policies() -> None:
    m = _load(CLAR_MANIFEST)
    assert m["position_quantity_policy"] == "WHOLE_SHARES_ONLY"
    assert m["zero_or_negative_shares"] == "FAIL_CLOSED"
    assert m["residual_cash_return"] == 0.0
    assert m["negative_cash_permitted"] is False


def test_dividend_and_split_policies() -> None:
    m = _load(CLAR_MANIFEST)
    assert m["dividend_accounting"]["receivable_may_size_purchase_before_payable"] is False
    assert m["dividend_accounting"]["double_counting"] == "PROHIBITED"
    assert m["split_accounting"]["unbound_split"] == "BLOCKED_UNBOUND_SPLIT_AUTHORITY"


def test_terminal_and_benchmark_policies() -> None:
    m = _load(CLAR_MANIFEST)
    assert m["m1_terminal"]["m1_end"] == "2020-12-31"
    assert m["m1_terminal"]["fetch_2021_to_close_or_value"] == "PROHIBITED"
    assert m["m1_terminal"]["forced_liquidation"] == "PROHIBITED"
    assert m["benchmark"]["g4_operator"] == "CORE_MDD_LT_BENCHMARK_MDD_STRICT"


def test_upstream_pins_match_disk() -> None:
    m = _load(CLAR_MANIFEST)
    pins = m["upstream_pins"]
    r1 = _load(R1_MANIFEST)
    r1_payload = {k: v for k, v in r1.items() if k != "manifest_sha256"}
    # Repo convention: manifest SHA = hash over canonical payload, not file bytes.
    assert pins["r1_manifest_sha256"] == r1["manifest_sha256"]
    assert pins["r1_manifest_sha256"] == hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(r1_payload).encode("utf-8")
    ).hexdigest()
    assert pins["preregistration_sha256"] == _sha(PREREG)
    assert pins["hyp_009_record_sha256"] == _sha(HYP_PATH)
    assert m["r1_seal_modified"] is False
    assert m["market_data_access"] == "ZERO"


def test_clarification_doc_states() -> None:
    assert CLAR_DOC.is_file()
    text = CLAR_DOC.read_text(encoding="utf-8")
    assert "SIMULATED_STARTING_AUM_USD" in text
    assert "SIMULATED_AUM != CAPITAL_AUTHORITY" in text
    assert "PENDING_NEXT_PARTITION_EXECUTION_NOT_EXECUTED" in text
    assert "AUTHORIZE_CORE_001_HYP_009_PRE_R2_ACCOUNTING_CLARIFICATION_AND_R2_M1_EXECUTION" in text
