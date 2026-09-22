"""Unit and governance tests for HYP_006 R1 Quote-Provenance Amendment 001."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0016_early_quote_contract import (
    ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS,
    UNRESOLVED_PROVENANCE_QUOTE_CONDITIONS,
    REJECTED_QUOTE_CONDITIONS,
    parse_alpaca_quote,
)


from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification


def test_1_r1_artifacts_immutability() -> None:
    """Invariant 1: Original sealed R1 artifacts remain byte-for-byte immutable."""
    p85_spec = Path("docs/phase8.5/hypotheses/HYP_006.json").read_bytes()
    p14_spec = Path("docs/phase14/hypotheses/HYP_006.json").read_bytes()
    assert p85_spec == p14_spec
    assert hashlib.sha256(p14_spec).hexdigest() == "30d66b71af0480f5cae7fd74cf24b7331a741ad765244acdd41dad468ed8cf7d"

    # Verified canonical hypothesis spec SHA-256
    spec_obj = HypothesisSpecification(**json.loads(p14_spec.decode("utf-8")))
    assert calculate_hypothesis_spec_sha256(spec_obj) == "aba1dfa9bd54e42722c7cd160214632aea7eb0c5545808e8fe03208996478a30"

    prereg_bytes = Path("docs/research/MEC-0016-HYP-006-strategy-preregistration.md").read_bytes()
    assert hashlib.sha256(prereg_bytes).hexdigest() == "18fb66bf0ac2d41e207ec677b6773f447168e7e7a9c23747de2307f7fd5c8c0f"

    man_data = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_006.json").read_text(encoding="utf-8"))
    assert man_data["manifest_sha256"] == "bf2c1dd43de3aa8d8fdfcb23717e9aec454dbbc1e0d4be5ef9a70b40088fbba8"

    # Preserved historical record in original R1
    spec_dict = json.loads(p14_spec.decode("utf-8"))
    cfg = json.loads(spec_dict["parameter_config_json"])
    assert cfg["strategy_rules"]["execution_rules"]["quote_conditions_policy"]["acceptable_conditions"] == ["R", "?"]


def test_2_amendment_document_and_manifest_integrity() -> None:
    """Invariant 2: Additive Amendment 001 document and manifest are properly formed and sealed."""
    doc_path = Path("docs/phase14/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.md")
    assert doc_path.exists()
    doc_sha = hashlib.sha256(doc_path.read_bytes()).hexdigest()

    man_path = Path("docs/phase14/manifests/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.json")
    assert man_path.exists()
    data_man_path = Path("data/manifests/research/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.json")
    assert data_man_path.exists()

    # Mirror equality
    assert man_path.read_bytes() == data_man_path.read_bytes()

    man_data = json.loads(man_path.read_text(encoding="utf-8"))
    assert man_data["amendment_id"] == "HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001"
    assert man_data["hypothesis_id"] == "HYP_006"
    assert man_data["mechanism_id"] == "MEC-0016"
    assert man_data["amendment_document_sha256"] == doc_sha
    assert man_data["quote_provenance_audit"]["question_mark_classification"] == "STRUCTURALLY_USABLE_BUT_CONDITION_PROVENANCE_UNRESOLVED"
    assert man_data["quote_provenance_audit"]["q1_feed_semantics"] == "ESTABLISHED_CONSOLIDATED_NBBO"
    assert man_data["quote_provenance_audit"]["q2_condition_semantics"] == "NOT_ESTABLISHED_UNDIFFERENTIATED_LEGACY_PLACEHOLDER"
    assert man_data["quote_provenance_audit"]["question_mark_present_in_official_map"] is False

    # Status invariants
    assert man_data["status"] == "AMENDMENT_SEALED_QUOTE_PROVENANCE_UNRESOLVED"
    assert man_data["hypothesis_status"] == "BLOCKED_NON_FALSIFIED_BY_EXECUTION_DATA_PROVENANCE"
    assert man_data["r2_readiness"] == "BLOCKED"
    assert man_data["r2_dataset_status"] == "NOT_STARTED"
    assert man_data["hypothesis_falsified"] is False
    assert man_data["hypothesis_rejected"] is False
    assert man_data["strategy_pnl_observed"] is False
    assert man_data["backtest_started"] is False
    assert man_data["resumable"] is True
    assert man_data["capital_authority_usd"] == "0.00"
    assert man_data["no_real_orders"] is True
    assert man_data["market_data_access"] == "ZERO"
    assert man_data["m1_data_access"] == "ZERO"
    assert man_data["m2_data_access"] == "ZERO"
    assert man_data["is_paper_authorized"] is False
    assert man_data["is_live_authorized"] is False


def test_3_question_mark_treatment_under_amendment() -> None:
    """Invariant 3: Under Amendment 001, '?' fails closed for dataset execution and is only admitted for diagnostic audit."""
    raw_legacy = {
        "t": "2016-06-17T14:00:00.002Z",
        "bp": "206.91",
        "ap": "206.92",
        "bs": 2,
        "as": 24,
        "bx": "K",
        "ax": "P",
        "c": ["?"],
        "z": "B",
    }

    # For dataset execution (allow_unresolved_provenance=False), '?' raises fail-closed
    with pytest.raises(DataContractError, match="UNRESOLVED_QUOTE_CONDITION_PROVENANCE"):
        parse_alpaca_quote(raw_legacy, allow_unresolved_provenance=False)

    # For diagnostic probe audit (allow_unresolved_provenance=True), '?' parses successfully
    q_diag = parse_alpaca_quote(raw_legacy, allow_unresolved_provenance=True)
    assert q_diag.bid_price == Decimal("206.91")
    assert q_diag.ask_price == Decimal("206.92")
    assert q_diag.conditions == ["?"]

    # Condition 'R' (regular open) always succeeds
    raw_regular = dict(raw_legacy, c=["R"])
    q_reg = parse_alpaca_quote(raw_regular, allow_unresolved_provenance=False)
    assert q_reg.conditions == ["R"]

    # Unacceptable conditions fail closed in both modes
    for bad_c in ["N", "C", "L", "4"]:
        raw_bad = dict(raw_legacy, c=[bad_c])
        with pytest.raises(DataContractError, match="UNACCEPTABLE_QUOTE_CONDITION"):
            parse_alpaca_quote(raw_bad, allow_unresolved_provenance=False)
        with pytest.raises(DataContractError, match="UNACCEPTABLE_QUOTE_CONDITION"):
            parse_alpaca_quote(raw_bad, allow_unresolved_provenance=True)

    # Unknown conditions fail closed in both modes
    raw_unknown = dict(raw_legacy, c=["UNKNOWN_CODE"])
    with pytest.raises(DataContractError, match="UNKNOWN_QUOTE_CONDITION"):
        parse_alpaca_quote(raw_unknown, allow_unresolved_provenance=False)
    with pytest.raises(DataContractError, match="UNKNOWN_QUOTE_CONDITION"):
        parse_alpaca_quote(raw_unknown, allow_unresolved_provenance=True)


def test_4_prohibitions_and_invariants() -> None:
    """Invariant 4: Strategy execution cannot fall back to IEX, bar-based fills, or unverified approximations."""
    doc_text = Path("docs/phase14/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.md").read_text(encoding="utf-8")
    assert "No Bar-Based Execution Fallback" in doc_text
    assert "No Splicing with IEX" in doc_text
    assert "Zero P&L Contamination" in doc_text
    assert "BLOCKED_NON_FALSIFIED_BY_EXECUTION_DATA_PROVENANCE" in doc_text

    # Verify no strategy signals, trades, backtest, or P&L exist
    man_data = json.loads(Path("docs/phase14/manifests/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.json").read_text(encoding="utf-8"))
    assert man_data["strategy_pnl_observed"] is False
    assert man_data["backtest_started"] is False
    assert man_data["r2_dataset_status"] == "NOT_STARTED"
    assert man_data["r2_readiness"] == "BLOCKED"
    assert man_data["capital_authority_usd"] == "0.00"
