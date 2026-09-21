"""Unit and Invariant Tests for HYP_005 Additive R1 Provider Amendment 001.

Verifies:
1. Original R1 artifacts remain strictly unmodified (byte-for-byte and canonical digest match).
2. Amendment document and manifest exist and bind original R1 lineage.
3. Scientific hypothesis remains unchanged (scientific_hypothesis_changed == False).
4. M1 sample window remains unchanged (m1_sample_window_changed == False).
5. K = 1 trial count remains unchanged.
6. Primary dividend authority is State Street / SSGA official distributions (total 68 distributions).
7. Complete dividend census: 35 pre-2016, 33 post-2016, 31 verified in Alpaca, 37 unverified in Alpaca.
8. Unverified post-2016 events are exactly 2016-03-18 and 2018-06-15 (ALPACA_CROSS_CHECK_ABSENT_OR_UNVERIFIED).
9. All 31 verified Alpaca events have exact Decimal rate match against SSGA (ALPACA_PRESENT_RATE_RECONCILIATION = 31/31 PASS).
10. Reclassified Alpaca role is CROSS_PROVIDER_VALIDATION_ONLY.
11. Primary market data provider is Massive / Polygon US Stocks SIP (minute aggs + quotes back to 2003).
12. Massive market-data live qualification state is NOT_EXECUTED_ENTITLEMENT_MISSING.
13. R2 dataset status remains NOT_STARTED; R2 readiness is BLOCKED_PENDING_MASSIVE_ENTITLEMENT_AND_LIVE_QUALIFICATION.
14. Next action is CONFIGURE_MASSIVE_ENTITLEMENT_THEN_AUTHORIZE_NARROW_PROVIDER_QUALIFICATION.
15. Inception token invariants hold: capital $0.00, NO_REAL_ORDERS == True, paper/live locked.
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

    # Verify self-canonical digest
    man_copy = dict(man_data)
    del man_copy["manifest_sha256"]
    canonical_json = CanonicalConfigSerializer.to_canonical_json(man_copy)
    assert hashlib.sha256(canonical_json.encode("utf-8")).hexdigest() == man_data["manifest_sha256"]


def test_3_scientific_hypothesis_invariants_preserved() -> None:
    """Invariant 3: Scientific hypothesis, sample window, K, and parameters remain unchanged."""
    man_data = json.loads(Path("docs/phase14/manifests/HYP_005_R1_PROVIDER_AMENDMENT_001.json").read_text(encoding="utf-8"))
    assert man_data["scientific_hypothesis_changed"] is False
    assert man_data["m1_sample_window_changed"] is False
    assert man_data["strategy_parameters_changed"] is False
    assert man_data["friction_stack_changed"] is False
    assert man_data["acceptance_gates_changed"] is False
    assert man_data["search_trial_count_k"] == 1


def test_4_ssga_dividend_authority_manifest_census_and_reconciliation() -> None:
    """Invariant 4: SSGA dividend manifest covers all 68 M1 distributions with exact census breakdown."""
    div_path = Path("docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json")
    assert div_path.exists()
    div_file_sha = hashlib.sha256(div_path.read_bytes()).hexdigest()

    man_data = json.loads(Path("docs/phase14/manifests/HYP_005_R1_PROVIDER_AMENDMENT_001.json").read_text(encoding="utf-8"))
    assert man_data["amended_provider_lineage"]["dividend_authority_manifest_sha256"] == div_file_sha

    div_data = json.loads(div_path.read_text(encoding="utf-8"))
    assert div_data["primary_dividend_authority"] == "STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS"
    dists = div_data["distributions"]
    assert len(dists) == 68
    assert div_data["scope"]["m1_relevant_distributions_count"] == 68

    # Verify boundary ex-dates
    assert dists[0]["ex_date"] == "2007-06-15"
    assert dists[-1]["ex_date"] == "2024-03-15"

    # Exact census breakdown
    pre_2016 = [d for d in dists if d["ex_date"] < "2016-01-01"]
    post_2016 = [d for d in dists if d["ex_date"] >= "2016-01-01"]
    assert len(pre_2016) == 35, f"Expected 35 pre-2016 events, got {len(pre_2016)}"
    assert len(post_2016) == 33, f"Expected 33 post-2016 events, got {len(post_2016)}"

    # All pre-2016 events must have alpaca_overlap_verified == False
    for d in pre_2016:
        assert d["alpaca_overlap_verified"] is False
        assert d["alpaca_rate"] is None

    # Alpaca verified counts
    verified = [d for d in dists if d["alpaca_overlap_verified"]]
    unverified = [d for d in dists if not d["alpaca_overlap_verified"]]
    assert len(verified) == 31, f"Expected 31 verified events, got {len(verified)}"
    assert len(unverified) == 37, f"Expected 37 unverified events, got {len(unverified)}"

    # Exact post-2016 unverified rows
    post_unverified = [d for d in post_2016 if not d["alpaca_overlap_verified"]]
    assert len(post_unverified) == 2
    assert [d["ex_date"] for d in post_unverified] == ["2016-03-18", "2018-06-15"]
    assert post_unverified[0]["cash_distribution"] == "1.049604"
    assert post_unverified[1]["cash_distribution"] == "1.245568"

    # Preceding first verified Alpaca distribution (before 2016-06-17)
    before_first_alpaca = [d for d in dists if d["ex_date"] < "2016-06-17"]
    assert len(before_first_alpaca) == 36

    # 31 verified rates match SSGA rates exactly
    for d in verified:
        assert d["alpaca_rate"] is not None
        assert Decimal(d["cash_distribution"]) == Decimal(d["alpaca_rate"])

    # Manifest summary verification
    recon = man_data["amended_provider_lineage"]["dividend_reconciliation_summary"]
    assert recon["total_m1_distributions"] == 68
    assert recon["pre_2016_distributions"] == 35
    assert recon["post_2016_distributions"] == 33
    assert recon["alpaca_verified_true"] == 31
    assert recon["alpaca_verified_false"] == 37
    assert recon["post_2016_unverified_rows"] == ["2016-03-18", "2018-06-15"]
    assert recon["preceding_first_verified_alpaca_distribution"] == 36
    assert recon["alpaca_present_rate_reconciliation"] == "31/31 PASS"
    assert recon["full_post_2016_alpaca_coverage"] == "NOT_ESTABLISHED"
    assert recon["ssga_full_m1_dividend_authority"] == "ESTABLISHED"


def test_5_amended_provider_lineage_and_r2_locks() -> None:
    """Invariant 5: Lineage designates Massive + SSGA, with R2 locked pending entitlement & live qualification."""
    man_data = json.loads(Path("docs/phase14/manifests/HYP_005_R1_PROVIDER_AMENDMENT_001.json").read_text(encoding="utf-8"))
    lineage = man_data["amended_provider_lineage"]
    assert lineage["primary_market_data_provider"] == "MASSIVE_POLYGON_US_STOCKS_SIP"
    assert lineage["reclassified_alpaca_role"] == "CROSS_PROVIDER_VALIDATION_ONLY"

    assert man_data["status"] == "AMENDMENT_SEALED_LINEAGE_ONLY_PROVIDER_QUALIFICATION_PENDING"
    assert man_data["massive_market_data_provider_qualification"] == "NOT_EXECUTED_ENTITLEMENT_MISSING"
    assert man_data["capital_authority_usd"] == "0.00"
    assert man_data["no_real_orders"] is True
    assert man_data["market_data_access"] == "ZERO"
    assert man_data["m1_data_access"] == "ZERO"
    assert man_data["m2_data_access"] == "ZERO"
    assert man_data["is_paper_authorized"] is False
    assert man_data["is_live_authorized"] is False
    assert man_data["r2_dataset_status"] == "NOT_STARTED"
    assert man_data["r2_readiness"] == "BLOCKED_PENDING_MASSIVE_ENTITLEMENT_AND_LIVE_QUALIFICATION"
    assert man_data["next_action"] == "CONFIGURE_MASSIVE_ENTITLEMENT_THEN_AUTHORIZE_NARROW_PROVIDER_QUALIFICATION"
