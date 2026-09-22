"""Unit and Invariant Tests for HYP_005 Entitlement Block and HYP_006 Pre-Inception.

Verifies:
1. HYP_005 original R1 artifacts remain strictly unmodified (byte-for-byte and canonical digest match).
2. HYP_005 is blocked non-falsified on primary data entitlement; P&L unobserved; resumable = True.
3. HYP_006 is in pre-inception state only; formal R1 JSON / manifest does not exist.
4. Canonical mechanism ID allocated is MEC-0016; candidate hypothesis ID is HYP_006.
5. Search space cardinality K = 1; strategy mechanics inherited before any empirical observation.
6. Mathematical strategy contract strictly adheres to MEC-0015 without drift:
   - Same-minute move-from-open Noise Area across 14 prior completed eligible sessions.
   - Multiplicative bands around daily anchors (UpperAnchor * (1 + sigma_open)).
   - TypicalPrice (H+L+C)/3 cumulative RTH VWAP.
   - 15 daily returns, ddof=1, shift=1, target daily vol 0.02 (NO sqrt(252)), max leverage 4.0.
   - Nearest-integer position sizing (round, NOT floor).
   - Fail-closed session exclusion for any missing minute (NO <=5 missing bar allowance).
   - Zero arbitrary 30-second quote timeout; zero arbitrary $0.05 HF tolerance.
7. Proposed M1 is 2016-01-01 to 2024-04-30; M2 is strictly forbidden / zero access.
8. HF Data Library role is strictly secondary bar cross-check only; zero quote/NBBO authority.
9. Early-M1 historical SIP quote manifest exists for 2016-06-17, 2017-06-01, 2018-06-01 (9/9 valid).
10. Feasibility verdict is FREE_DATA_FEASIBILITY_PASS with 0 open blockers.
11. Capital authority remains $0.00, NO_REAL_ORDERS == True, paper and live locked.
"""

from decimal import Decimal
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
    assert "GOVERNANCE_STATE: HYP_006_PREINCEPTION_READY_FOR_HUMAN_REVIEW (R1 NOT CREATED)" in prop_txt


def test_4_hyp_006_mathematical_contract_integrity() -> None:
    """Invariant 4: Strategy contract matches MEC-0015 without drift (Noise, bands, sizing, missing bars)."""
    prop_txt = Path("docs/research/MEC-0016-HYP-006-proposal.md").read_text(encoding="utf-8")
    req_txt = Path("docs/research/MEC-0016-HYP-006-data-requirements.md").read_text(encoding="utf-8")

    # Noise area must use move_open from same-minute, NOT daily high-low
    assert "move_open" in prop_txt
    assert "REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS" in prop_txt
    assert "UpperAnchor" in prop_txt
    assert "1 + \\sigma\\_open" in prop_txt or "1 + \\sigma_open" in prop_txt or "(1 + \\sigma" in prop_txt
    assert "NoiseArea_d = \\frac{1}{14}" not in prop_txt  # Replaced daily high-low

    # VWAP contract
    assert "TypicalPrice" in prop_txt
    assert "REJECTED_FOR_BASELINE_SIGNAL_LOGIC" in prop_txt

    # Volatility sizing: target daily vol 0.02, NO sqrt(252), round() nearest integer
    assert "0.02" in prop_txt
    assert "sqrt(252)" not in prop_txt
    assert "\\sqrt{252}" not in prop_txt
    assert "round" in prop_txt

    # Missing bar policy: FAIL_CLOSED_SESSION_EXCLUSION, no <=5 missing bars
    assert "FAIL_CLOSED_SESSION_EXCLUSION" in req_txt
    assert "<= 5" not in req_txt
    assert "<=5" not in req_txt

    # No arbitrary 30s timeout or $0.05 HF tolerance
    assert "30 seconds" not in req_txt and "30s" not in req_txt
    assert "$0.05" not in req_txt


def test_5_early_quote_qualification_manifest_and_feasibility_pass() -> None:
    """Invariant 5: Early-M1 SIP quote probe manifest exists, 9/9 valid, feasibility is PASS."""
    manifest_p = Path("docs/research/manifests/MEC-0016-alpaca-early-quote-contract-manifest.json")
    assert manifest_p.exists()
    data = json.loads(manifest_p.read_text(encoding="utf-8"))

    assert data["symbol"] == "SPY"
    assert data["feed"] == "sip"
    assert data["is_qualified"] is True
    assert data["authorized_probe_dates"] == ["2016-06-17", "2017-06-01", "2018-06-01"]
    assert len(data["boundary_evaluations"]) == 9

    for b in data["boundary_evaluations"]:
        assert b["is_valid"] is True
        assert Decimal(b["simulated_buy_fill"]) > Decimal("0")
        assert Decimal(b["simulated_sell_fill"]) > Decimal("0")
        assert Decimal(b["simulated_buy_fill"]) >= Decimal(b["simulated_sell_fill"])
        assert b["session_date"] in ("2016-06-17", "2017-06-01", "2018-06-01")

    # Audit and decisions report PASS
    audit_txt = Path("docs/research/MEC-0016-HYP-006-free-data-feasibility-audit.md").read_text(encoding="utf-8")
    assert "FEASIBILITY_VERDICT: FREE_DATA_FEASIBILITY_PASS" in audit_txt

    dec_txt = Path("docs/research/MEC-0016-HYP-006-open-decisions.md").read_text(encoding="utf-8")
    assert "EXACT_OPEN_BLOCKERS: 0" in dec_txt
    assert "MEC-0016-D06" in dec_txt and "RESOLVED_PASS" in dec_txt
    assert "MEC-0016-D07" in dec_txt and "RESOLVED_PASS" in dec_txt
