"""Unit and Invariant Tests for HYP_005 Entitlement Block and HYP_006 Pre-Inception.

Verifies:
1. HYP_005 original R1 artifacts remain strictly unmodified (byte-for-byte and canonical digest match).
2. HYP_005 is blocked non-falsified on primary data entitlement; P&L unobserved; resumable = True.
3. HYP_006 is in pre-inception state only; formal R1 JSON / manifest does not exist.
4. Canonical mechanism ID allocated is MEC-0016; candidate hypothesis ID is HYP_006.
5. Search space cardinality K = 1; strategy mechanics inherited before any empirical observation.
6. Proposed M1 is 2016-01-01 to 2024-04-30; M2 is strictly forbidden / zero access.
7. Zero-cost constraint ($0.00 budget) recorded; feasibility verdict is FREE_DATA_FEASIBILITY_CONDITIONAL.
8. HF Data Library role is strictly secondary bar cross-check only; zero quote/NBBO authority.
9. SSGA sovereign dividend authority covers all 33 post-2016 distributions.
10. Capital authority remains $0.00, NO_REAL_ORDERS == True, paper and live locked.
"""

import hashlib
import json
from pathlib import Path
import pytest

from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification


def test_1_hyp_005_original_r1_immutability() -> None:
    """Invariant 1: Original HYP_005 R1 artifacts remain byte-for-byte identical to R1 commit."""
    prereg = Path("docs/research/MEC-0015-HYP-005-strategy-preregistration.md")
    assert hashlib.sha256(prereg.read_bytes()).hexdigest() == "5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e"

    p85 = Path("docs/phase8.5/hypotheses/HYP_005.json").read_bytes()
    p14 = Path("docs/phase14/hypotheses/HYP_005.json").read_bytes()
    assert p85 == p14

    orig_man = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_005.json").read_text(encoding="utf-8"))
    assert orig_man["manifest_sha256"] == "f0322a049b6990ed2131f28cb33f0f2fd768a982be2e75815d9f999091422e61"
    assert orig_man["hypothesis_sha256"] == "ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f"

    spec = HypothesisSpecification(**json.loads(p14.decode("utf-8")))
    assert calculate_hypothesis_spec_sha256(spec) == "ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f"


def test_2_hyp_005_entitlement_block_invariants() -> None:
    """Invariant 2: HYP_005 is formally blocked non-falsified on entitlement; resumable=True; P&L unobserved."""
    doc_path = Path("docs/phase14/HYP_005_DATA_ENTITLEMENT_BLOCK_001.md")
    assert doc_path.exists()
    doc_sha = hashlib.sha256(doc_path.read_bytes()).hexdigest()

    man_path = Path("docs/phase14/manifests/HYP_005_DATA_ENTITLEMENT_BLOCK_001.json")
    assert man_path.exists()
    man_data = json.loads(man_path.read_text(encoding="utf-8"))

    assert man_data["block_document_sha256"] == doc_sha
    assert man_data["hypothesis_id"] == "HYP_005"
    assert man_data["mechanism_id"] == "MEC-0015"
    assert man_data["classification"] == "BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT"
    assert man_data["hypothesis_falsified"] is False
    assert man_data["hypothesis_rejected"] is False
    assert man_data["strategy_pnl_observed"] is False
    assert man_data["backtest_started"] is False
    assert man_data["r2_dataset_status"] == "NOT_STARTED"
    assert man_data["resumable"] is True
    assert man_data["capital_authority_usd"] == "0.00"
    assert man_data["no_real_orders"] is True
    assert man_data["is_paper_authorized"] is False
    assert man_data["is_live_authorized"] is False

    # Verify self-canonical digest
    man_copy = dict(man_data)
    del man_copy["manifest_sha256"]
    canonical_json = CanonicalConfigSerializer.to_canonical_json(man_copy)
    assert hashlib.sha256(canonical_json.encode("utf-8")).hexdigest() == man_data["manifest_sha256"]


def test_3_hyp_006_preinception_governance() -> None:
    """Invariant 3: HYP_006 is strictly pre-inception; formal R1 does not exist; K = 1."""
    # Sealed hypothesis and R1 manifests must NOT exist yet
    assert not Path("docs/phase8.5/hypotheses/HYP_006.json").exists()
    assert not Path("docs/phase14/hypotheses/HYP_006.json").exists()
    assert not Path("docs/phase14/manifests/manifest_r1_HYP_006.json").exists()

    # Pre-inception artifacts must exist
    audit_p = Path("docs/research/MEC-0016-HYP-006-free-data-feasibility-audit.md")
    prop_p = Path("docs/research/MEC-0016-HYP-006-proposal.md")
    req_p = Path("docs/research/MEC-0016-HYP-006-data-requirements.md")
    dec_p = Path("docs/research/MEC-0016-HYP-006-open-decisions.md")

    assert audit_p.exists()
    assert prop_p.exists()
    assert req_p.exists()
    assert dec_p.exists()

    prop_txt = prop_p.read_text(encoding="utf-8")
    assert "MEC-0016" in prop_txt
    assert "HYP_006" in prop_txt
    assert "SEARCH_SPACE_CARDINALITY: K = 1" in prop_txt
    assert "PROPOSED_M1: 2016-01-01 THROUGH 2024-04-30" in prop_txt
    assert "PROPOSED_M2: 2024-05-01 ONWARD (LOCKED / STRICTLY FORBIDDEN)" in prop_txt
    assert "STATUS: PREINCEPTION_READY_FOR_HUMAN_REVIEW" in prop_txt


def test_4_zero_cost_feasibility_and_hfdata_library_role() -> None:
    """Invariant 4: Zero-cost feasibility is CONDITIONAL; HF Data Library is bar cross-check only."""
    audit_txt = Path("docs/research/MEC-0016-HYP-006-free-data-feasibility-audit.md").read_text(encoding="utf-8")
    assert "FEASIBILITY_VERDICT: FREE_DATA_FEASIBILITY_CONDITIONAL" in audit_txt
    assert "HF_DATA_LIBRARY_ROLE = SECONDARY_INDEPENDENT_BAR_CROSS_CHECK_ONLY" in audit_txt
    assert "OPERATIONAL_BUDGET: $0.00" in audit_txt

    dec_txt = Path("docs/research/MEC-0016-HYP-006-open-decisions.md").read_text(encoding="utf-8")
    assert "MEC-0016-D06" in dec_txt
    assert "MEC-0016-D07" in dec_txt
    assert "EXACT_OPEN_BLOCKERS: 2" in dec_txt

    # Verify dividend manifest reuse covers all 33 post-2016 distributions
    div_data = json.loads(Path("docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json").read_text(encoding="utf-8"))
    post_2016 = [d for d in div_data["distributions"] if d["ex_date"] >= "2016-01-01"]
    assert len(post_2016) == 33
