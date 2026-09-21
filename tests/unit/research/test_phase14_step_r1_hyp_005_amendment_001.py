"""Unit and Invariant Tests for HYP_005 Additive R1 Provider Amendment 001.

Verifies:
1. Original R1 artifacts remain strictly unmodified (byte-for-byte and canonical digest match).
2. Amendment document and manifest exist and bind original R1 lineage.
3. Scientific hypothesis remains unchanged (scientific_hypothesis_changed == False).
4. M1 sample window remains unchanged (m1_sample_window_changed == False).
5. K = 1 trial count remains unchanged.
6. Primary dividend authority is State Street / SSGA official distributions.
7. SSGA dividend authority manifest covers all 68 M1-relevant distributions.
8. Reclassified Alpaca role is CROSS_PROVIDER_VALIDATION_ONLY.
9. Primary market data provider is Massive / Polygon US Stocks SIP (minute aggs + quotes back to 2003).
10. R2 dataset status remains NOT_STARTED; R2 readiness is BLOCKED_PENDING_MASSIVE_ENTITLEMENT.
11. Inception token invariants hold: capital $0.00, NO_REAL_ORDERS == True, paper/live locked.
"""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest

from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification


def test_1_original_r1_artifacts_immutability() -> None:
    """Invariant 1: Original R1 artifacts remain strictly untouched and byte-identical to R1 commit."""
    # Preregistration file SHA-256
    prereg = Path("docs/research/MEC-0015-HYP-005-strategy-preregistration.md")
    assert hashlib.sha256(prereg.read_bytes()).hexdigest() == "5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e"

    # Original R1 manifest internal SHA-256
    orig_man = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_005.json").read_text(encoding="utf-8"))
    assert orig_man["manifest_sha256"] == "f0322a049b6990ed2131f28cb33f0f2fd768a982be2e75815d9f999091422e61"
    assert orig_man["hypothesis_sha256"] == "ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f"

    # Hypothesis specification canonical digest
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_005.json").read_text(encoding="utf-8"))
    spec = HypothesisSpecification(**p14_hyp)
    assert calculate_hypothesis_spec_sha256(spec) == "ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f"


def test_2_amendment_bindings_and_immutability() -> None:
    """Invariant 2: Amendment manifest and document exist and bind original R1 hashes."""
    doc_path = Path("docs/phase14/HYP_005_R1_PROVIDER_AMENDMENT_001.md")
    assert doc_path.exists()
    doc_sha = hashlib.sha256(doc_path.read_bytes()).hexdigest()

    man_path = Path("docs/phase14/manifests/HYP_005_R1_PROVIDER_AMENDMENT_001.json")
    assert man_path.exists()
    man_data = json.loads(man_path.read_text(encoding="utf-8"))

    assert man_data["amendment_document_sha256"] == doc_sha
    assert man_data["upstream_r1_binding"]["original_r1_commit"] == "333af02424349bfb43ec05c7afc96ca960f6d5d7"
    assert man_data["upstream_r1_binding"]["original_hypothesis_sha256"] == "ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f"
    assert man_data["upstream_r1_binding"]["original_preregistration_sha256"] == "5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e"
    assert man_data["upstream_r1_binding"]["original_manifest_sha256"] == "f0322a049b6990ed2131f28cb33f0f2fd768a982be2e75815d9f999091422e61"


def test_3_scientific_hypothesis_invariants_preserved() -> None:
    """Invariant 3: Scientific hypothesis, sample window, K, and parameters remain unchanged."""
    man_data = json.loads(Path("docs/phase14/manifests/HYP_005_R1_PROVIDER_AMENDMENT_001.json").read_text(encoding="utf-8"))
    assert man_data["scientific_hypothesis_changed"] is False
    assert man_data["m1_sample_window_changed"] is False
    assert man_data["strategy_parameters_changed"] is False
    assert man_data["friction_stack_changed"] is False
    assert man_data["acceptance_gates_changed"] is False
    assert man_data["search_trial_count_k"] == 1


def test_4_ssga_dividend_authority_manifest_completeness() -> None:
    """Invariant 4: SSGA dividend manifest covers all 68 M1 distributions and matches digest."""
    div_path = Path("docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json")
    assert div_path.exists()
    div_file_sha = hashlib.sha256(div_path.read_bytes()).hexdigest()

    man_data = json.loads(Path("docs/phase14/manifests/HYP_005_R1_PROVIDER_AMENDMENT_001.json").read_text(encoding="utf-8"))
    assert man_data["amended_provider_lineage"]["dividend_authority_manifest_sha256"] == div_file_sha

    div_data = json.loads(div_path.read_text(encoding="utf-8"))
    assert div_data["primary_dividend_authority"] == "STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS"
    assert len(div_data["distributions"]) == 68
    assert div_data["scope"]["m1_relevant_distributions_count"] == 68

    # Verify first M1 dividend is June 2007 and last is March 2024
    assert div_data["distributions"][0]["ex_date"] == "2007-06-15"
    assert div_data["distributions"][-1]["ex_date"] == "2024-03-15"


def test_5_amended_provider_lineage_and_r2_locks() -> None:
    """Invariant 5: Lineage designates Massive + SSGA, with R2 locked pending entitlement."""
    man_data = json.loads(Path("docs/phase14/manifests/HYP_005_R1_PROVIDER_AMENDMENT_001.json").read_text(encoding="utf-8"))
    lineage = man_data["amended_provider_lineage"]
    assert lineage["primary_market_data_provider"] == "MASSIVE_POLYGON_US_STOCKS_SIP"
    assert lineage["reclassified_alpaca_role"] == "CROSS_PROVIDER_VALIDATION_ONLY"

    assert man_data["status"] == "AMENDMENT_SEALED_PROVIDER_AMENDED"
    assert man_data["capital_authority_usd"] == "0.00"
    assert man_data["no_real_orders"] is True
    assert man_data["market_data_access"] == "ZERO"
    assert man_data["m1_data_access"] == "ZERO"
    assert man_data["m2_data_access"] == "ZERO"
    assert man_data["is_paper_authorized"] is False
    assert man_data["is_live_authorized"] is False
    assert man_data["r2_dataset_status"] == "NOT_STARTED"
    assert man_data["r2_readiness"] == "BLOCKED_PENDING_MASSIVE_ENTITLEMENT"
