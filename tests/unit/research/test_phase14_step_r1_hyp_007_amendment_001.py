"""Unit and governance invariant tests for HYP_007 R1 Additive Friction Correction Amendment 001."""

from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest

from acash.execution.regulatory_fees import compute_finra_taf, compute_sec31_fee, get_finra_taf_segment
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification


def test_1_original_hyp_007_r1_artifacts_immutability() -> None:
    """Invariant 1: Original sealed HYP_007 R1 artifacts remain byte-for-byte immutable."""
    p85_spec = Path("docs/phase8.5/hypotheses/HYP_007.json").read_bytes()
    p14_spec = Path("docs/phase14/hypotheses/HYP_007.json").read_bytes()
    assert p85_spec == p14_spec
    assert hashlib.sha256(p14_spec).hexdigest() == "912a47fa8de199b6d77905056b717878f74564a74ea958e5d53e3ada3fe75591"

    spec_dict = json.loads(p14_spec.decode("utf-8"))
    spec_obj = HypothesisSpecification(**spec_dict)
    assert calculate_hypothesis_spec_sha256(spec_obj) == "e6821bed806cadef6c129f02c45cd244c0e720fca1715fcc480315c95186df7d"

    prereg_bytes = Path("docs/research/MEC-0017-HYP-007-strategy-preregistration.md").read_bytes()
    assert hashlib.sha256(prereg_bytes).hexdigest() == "41a0a27f9237371538366546a1761884d636d6c6d2e01ad14a90aa1cc47e16c4"

    man_data = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_007.json").read_text(encoding="utf-8"))
    assert man_data["manifest_sha256"] == "f48a57333675ebeb5a47cfff40108b13abec000ba958a42ba54fc714c30adc02"

    # Invariant: Original incorrect metadata remains historically visible in sealed R1
    cfg = json.loads(spec_dict["parameter_config_json"])
    assert "round nearest cent" in cfg["friction_model"]["finra_taf"]


def test_2_amendment_document_and_manifest_integrity() -> None:
    """Invariant 2: Additive Amendment 001 document and manifest are formed, sealed, and mirror-identical."""
    doc_path = Path("docs/phase14/HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001.md")
    assert doc_path.exists()
    doc_sha = hashlib.sha256(doc_path.read_bytes()).hexdigest()
    assert doc_sha == "34fe347d0ee669c73feb1c09bb6f9f57dfc47a814e7176133dc201d13205e73c"

    p14_man = Path("docs/phase14/manifests/HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001.json")
    data_man = Path("data/manifests/research/HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001.json")
    assert p14_man.exists()
    assert data_man.exists()
    assert p14_man.read_bytes() == data_man.read_bytes()

    man = json.loads(p14_man.read_text(encoding="utf-8"))
    assert man["amendment_id"] == "HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001"
    assert man["hypothesis_id"] == "HYP_007"
    assert man["mechanism_id"] == "MEC-0017"
    assert man["status"] == "HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001_SEALED_PASS"
    assert man["hypothesis_status"] == "R1_SEALED_READY_FOR_R2"
    assert man["r2_readiness"] == "READY_FOR_SEPARATE_HUMAN_AUTHORIZATION"
    assert man["r2_dataset_status"] == "NOT_STARTED"
    assert man["amendment_document_sha256"] == doc_sha
    assert man["friction_model_correction"]["effective_rounding_rule"] == "ROUND_CEILING_TO_CENT"
    assert man["friction_model_correction"]["defect_classification"] == "IMPLEMENTATION_CORRECT_R1_METADATA_INCORRECT"


def test_3_finra_taf_implementation_and_tiers_verification() -> None:
    """Invariant 3: Runtime implementation compute_finra_taf strictly implements ceiling rounding across all tiers."""
    # Sub-cent fee rounds up to $0.01 (CEILING)
    # Tier 4 (2021): rate 0.000119
    d_2021 = date(2021, 7, 1)
    seg_2021 = get_finra_taf_segment(d_2021)
    assert seg_2021.rate_per_share == Decimal("0.000119")
    assert seg_2021.max_fee_per_trade == Decimal("5.95")
    assert compute_finra_taf(d_2021, 1) == Decimal("0.01")   # 1 * 0.000119 = 0.000119 -> ceil $0.01
    assert compute_finra_taf(d_2021, 100) == Decimal("0.02") # 100 * 0.000119 = 0.0119 -> ceil $0.02

    # Tier 5 (2022): rate 0.000130, cap 6.49
    d_2022 = date(2022, 6, 1)
    seg_2022 = get_finra_taf_segment(d_2022)
    assert seg_2022.rate_per_share == Decimal("0.000130")
    assert seg_2022.max_fee_per_trade == Decimal("6.49")
    assert compute_finra_taf(d_2022, 100) == Decimal("0.02") # 100 * 0.000130 = 0.0130 -> ceil $0.02
    assert compute_finra_taf(d_2022, 60000) == Decimal("6.49") # Capped

    # Tier 6 (2023): rate 0.000145, cap 7.27
    d_2023 = date(2023, 6, 1)
    seg_2023 = get_finra_taf_segment(d_2023)
    assert seg_2023.rate_per_share == Decimal("0.000145")
    assert seg_2023.max_fee_per_trade == Decimal("7.27")
    assert compute_finra_taf(d_2023, 100) == Decimal("0.02") # 100 * 0.000145 = 0.0145 -> ceil $0.02
    assert compute_finra_taf(d_2023, 60000) == Decimal("7.27") # Capped

    # Tier 7 (2024): rate 0.000166, cap 8.30
    d_2024 = date(2024, 4, 30)
    seg_2024 = get_finra_taf_segment(d_2024)
    assert seg_2024.rate_per_share == Decimal("0.000166")
    assert seg_2024.max_fee_per_trade == Decimal("8.30")
    assert compute_finra_taf(d_2024, 1) == Decimal("0.01")   # 1 * 0.000166 = 0.000166 -> ceil $0.01
    assert compute_finra_taf(d_2024, 100) == Decimal("0.02") # 100 * 0.000166 = 0.0166 -> ceil $0.02
    assert compute_finra_taf(d_2024, 50000) == Decimal("8.30") # Exact cap

    # Buy transactions incur exactly $0.00
    assert compute_finra_taf(d_2024, 100, is_sell=False) == Decimal("0.00")

    # SEC Section 31 remains strictly separate
    sec_fee = compute_sec31_fee(d_2024, Decimal("40000.00"), is_sell=True)
    assert sec_fee > Decimal("0.00")
    assert compute_sec31_fee(d_2024, Decimal("40000.00"), is_sell=False) == Decimal("0.00")


def test_4_warmup_specification_and_prohibitions() -> None:
    """Invariant 4: Warmup requires earliest session 2021-06-09 and strictly prohibits signals/trades/P&L."""
    p14_man = Path("docs/phase14/manifests/HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001.json")
    man = json.loads(p14_man.read_text(encoding="utf-8"))
    warm = man["warmup_specification"]

    assert warm["m1_start_date"] == "2021-07-01"
    assert warm["earliest_required_warmup_session"] == "2021-06-09"
    assert warm["earliest_noise_area_session"] == "2021-06-11"
    assert warm["noise_area_warmup_sessions_required"] == 14
    assert warm["volatility_sizing_unadjusted_closes_required"] == 16
    assert warm["volatility_sizing_returns_required"] == 15
    assert warm["warmup_strategy_signals_permitted"] is False
    assert warm["warmup_trades_permitted"] is False
    assert warm["warmup_pnl_permitted"] is False
    assert warm["warmup_execution_quotes_required"] is False

    # Boundaries
    assert man["capital_authority_usd"] == "0.00"
    assert man["no_real_orders"] is True
    assert man["m2_data_access"] == "ZERO"
    assert man["is_paper_authorized"] is False
    assert man["is_live_authorized"] is False
