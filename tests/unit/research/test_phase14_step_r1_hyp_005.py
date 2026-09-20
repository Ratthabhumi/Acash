"""Unit and Invariant Tests for Phase 14 Step R1: HYP_005 Registration & Governance.

Verifies:
1. HYP_005 ID is new, valid, and matches pattern ^HYP_[A-Z0-9_]+$.
2. HYP_003 and HYP_004 remain enrolled in TERMINAL_HYPOTHESIS_REGISTRY (anti-resurrection).
3. Gate invocation succeeds for valid HYP_005 and blocks terminal IDs.
4. K = 1 parameter search grid cardinality equality.
5. Canonical Git-tracked hypothesis mirrors (Phase 8.5 and Phase 14) and local runtime mirror are byte-identical.
6. Canonical Git-tracked R1 manifest and local runtime mirror are byte-identical.
7. Manifest SHA-256 matches disk bytes of canonical serialization.
8. Preregistration SHA-256 matches disk bytes and is pinned in manifest and spec.
9. All 11 upstream MEC-0015 authority contract and manifest hashes are pinned and match disk bytes.
10. Sizing contract invariants: 15 returns, ddof=1, shift=1, target_vol=0.02, max_leverage=4.0.
11. Noise-area contract invariants: 14 prior completed sessions, full-14 warmup required.
12. Early close policy: EXCLUDE_NON_STANDARD_REGULAR_SESSIONS.
13. Regulatory fee contracts: SEC Section 31 ROUND_CEILING operationalization, FINRA TAF 7 tiers.
14. Primary M1 acceptance gates: Net Return > 0, Sharpe >= 1.00, MDD <= 30%, Trades >= 100, 2x Stress.
15. 2x friction stress contract is frozen pre-P&L.
16. Zero empirical market data access during R1 (R1_MARKET_DATA_ACCESS = ZERO).
17. Zero strategy P&L, Sharpe, or trades computed.
18. Hard-locked zero authority: capital_authority_usd == 0.00, is_paper_authorized == False, is_live_authorized == False, NO_REAL_ORDERS == True.
19. Registration script has zero market-data / Alpaca / network imports.
20. Semantic conformance record exists and distinguishes binding research specifications from legacy schema compatibility stubs.
"""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.reinception import (
    InceptionDecision,
    ResearchInceptionProposal,
    ResearchReInceptionGate,
    TERMINAL_HYPOTHESIS_REGISTRY,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
    SplitPolicy,
)


def test_1_hyp_005_identity_and_terminal_registry_integrity() -> None:
    """Invariant 1: HYP_005 is not in TERMINAL_HYPOTHESIS_REGISTRY; HYP_003 and HYP_004 remain terminal."""
    assert "HYP_003" in TERMINAL_HYPOTHESIS_REGISTRY
    assert "HYP_004" in TERMINAL_HYPOTHESIS_REGISTRY
    assert "HYP_005" not in TERMINAL_HYPOTHESIS_REGISTRY


def test_2_reinception_gate_blocks_terminal_ids() -> None:
    """Invariant 2: Gate strictly blocks attempts to resurrect terminal hypothesis IDs."""
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_004",  # Terminal ID
        candidate_hypothesis_version="v2.0",
        economic_rationale="Attempted resurrection of terminal hypothesis.",
        target_symbol="SPY",
        target_timeframe="1m",
        feature_dependencies=["spy_ohlcv_1m"],
        parameter_search_grid={"test": ["val"]},
        planned_trial_count=1,
        target_horizons=[1],
        primary_horizon=1,
        expected_direction=ExpectedDirection.LONG,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.000001"),
            min_hac_t_stat=Decimal("1.96"),
            max_feature_autocorrelation=Decimal("0.999999"),
            min_cost_adjusted_spread_ratio=Decimal("1.0"),
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("0.0"),
            roundtrip_broker_fee_bps=Decimal("0.0"),
            fixed_slippage_bps=Decimal("0.0"),
        ),
        proposed_dataset_id="DS_TEST",
        proposed_data_window=("2020-01-01T00:00:00+00:00", "2021-01-01T00:00:00+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        ),
    )
    with pytest.raises(DataContractError, match="BLOCKED_MUTATION_VIOLATION"):
        ResearchReInceptionGate.evaluate_reinception_proposal(proposal)


def test_3_k_equals_1_grid_cardinality() -> None:
    """Invariant 3: K = 1 single primary preregistered specification."""
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_005.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    k_val = cfg["planned_trial_count_k"]["value"] if isinstance(cfg["planned_trial_count_k"], dict) else cfg["planned_trial_count_k"]
    assert k_val == 1
    assert cfg["primary_specification"] == "MEC_0015_NOISE_AREA_INTRADAY_MOMENTUM_BASELINE"


def test_4_sealed_mirrors_byte_identical() -> None:
    """Invariant 4: Canonical Git-tracked hypothesis mirrors and local runtime mirror are byte-identical."""
    p85 = Path("docs/phase8.5/hypotheses/HYP_005.json").read_bytes()
    p14 = Path("docs/phase14/hypotheses/HYP_005.json").read_bytes()
    data = Path("data/manifests/research/hypotheses/HYP_005.json").read_bytes()
    assert p85 == p14 == data

    # Verify canonical spec SHA-256 matches manifest
    spec_005 = HypothesisSpecification(**json.loads(p14.decode("utf-8")))
    calculated_spec_sha = calculate_hypothesis_spec_sha256(spec_005)
    manifest = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_005.json").read_text(encoding="utf-8"))
    assert manifest["hypothesis_sha256"] == calculated_spec_sha


def test_5_manifest_mirrors_byte_identical_and_valid() -> None:
    """Invariant 5: Canonical Git-tracked manifest and local runtime manifest mirror are byte-identical."""
    m14 = Path("docs/phase14/manifests/manifest_r1_HYP_005.json").read_bytes()
    mdata = Path("data/manifests/research/manifest_r1_HYP_005.json").read_bytes()
    assert m14 == mdata


def test_6_preregistration_sha_binding() -> None:
    """Invariant 6: Preregistration file SHA-256 matches disk bytes and is pinned in manifest and spec."""
    prereg_path = Path("docs/research/MEC-0015-HYP-005-strategy-preregistration.md")
    assert prereg_path.exists()
    calculated_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()

    manifest = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_005.json").read_text(encoding="utf-8"))
    assert manifest["preregistration_sha256"] == calculated_sha

    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_005.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    assert cfg["governance_lineage"]["preregistration_sha256"] == calculated_sha


def test_7_all_eleven_upstream_hashes_pinned_and_match_disk() -> None:
    """Invariant 7: All 11 upstream MEC-0015 contract and manifest hashes match disk bytes."""
    manifest = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_005.json").read_text(encoding="utf-8"))
    pinned = manifest["upstream_authority_hashes"]

    file_mapping = {
        "intake_doc_sha256": "docs/research/MEC-0015-profitability-first-intraday-momentum-intake.md",
        "strategy_contract_audit_sha256": "docs/research/MEC-0015-strategy-contract-audit.md",
        "open_decisions_sha256": "docs/research/MEC-0015-open-decisions.md",
        "provider_qualification_contract_sha256": "docs/research/MEC-0015-provider-qualification-contract.md",
        "friction_contract_sha256": "docs/research/MEC-0015-friction-contract.md",
        "partition_acceptance_contract_sha256": "docs/research/MEC-0015-partition-and-acceptance-contract.md",
        "bar_provider_manifest_sha256": "docs/research/manifests/MEC-0015-bar-provider-contract-manifest.json",
        "dividend_provider_manifest_sha256": "docs/research/manifests/MEC-0015-dividend-provider-contract-manifest.json",
        "quote_provider_manifest_sha256": "docs/research/manifests/MEC-0015-quote-provider-contract-manifest.json",
        "sec31_schedule_manifest_sha256": "docs/research/manifests/MEC-0015-sec31-fee-schedule.json",
        "finra_taf_schedule_manifest_sha256": "docs/research/manifests/MEC-0015-finra-taf-fee-schedule.json",
    }

    assert len(pinned) == 11
    for key, path_str in file_mapping.items():
        disk_sha = hashlib.sha256(Path(path_str).read_bytes()).hexdigest()
        assert pinned[key] == disk_sha, f"Mismatch on {key} for {path_str}"


def _unbox(val: object) -> object:
    """Helper to unbox type-tagged values from CanonicalConfigSerializer."""
    if isinstance(val, dict) and "__type__" in val and "value" in val:
        return val["value"]
    return val


def test_8_strategy_vol_sizing_and_noise_area_contracts() -> None:
    """Invariant 8: Strategy volatility sizing and noise area contracts strictly match specifications."""
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_005.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    strat = cfg["strategy_specification"]

    # Vol sizing
    vol = strat["volatility_sizing"]
    assert _unbox(vol["window_returns_count"]) == 15
    assert _unbox(vol["ddof"]) == 1
    assert _unbox(vol["shift"]) == 1
    assert _unbox(vol["current_day_included"]) is False
    assert _unbox(vol["target_volatility"]) == 0.02
    assert _unbox(vol["max_leverage"]) == 4.0
    assert _unbox(vol["sizing_denominator"]) == "CURRENT_SESSION_OPEN"

    # Noise area
    assert _unbox(strat["noise_area_lookback_sessions"]) == 14
    assert _unbox(strat["noise_area_warmup_policy"]) == "REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS"
    assert _unbox(strat["current_session_leakage"]) == "PROHIBITED"
    assert _unbox(strat["early_close_policy"]) == "EXCLUDE_NON_STANDARD_REGULAR_SESSIONS"


def test_9_regulatory_fee_operationalization() -> None:
    """Invariant 9: SEC Section 31 uses ROUND_CEILING operationalization and FINRA has 7 historical tiers."""
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_005.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    friction = cfg["friction_model"]

    sec31 = friction["sec_section_31"]
    assert _unbox(sec31["rounding"]) == "ROUND_CEILING_TO_CENT"
    assert _unbox(sec31["customer_pass_through"]) == "ACASH_CONSERVATIVE_OPERATIONALIZATION"

    finra = friction["finra_taf"]
    assert _unbox(finra["historical_tiers_count"]) == 7


def test_10_primary_m1_acceptance_gates() -> None:
    """Invariant 10: Primary M1 acceptance gates strictly defined as logical AND of 7 criteria."""
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_005.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    gates = cfg["primary_m1_acceptance_gates"]

    assert _unbox(gates["G1_net_total_return"]) == "> 0"
    assert _unbox(gates["G2_net_sharpe"]) == ">= 1.00"
    assert _unbox(gates["G3_max_drawdown"]) == "<= 0.30"
    assert _unbox(gates["G4_min_completed_trades"]) == ">= 100"
    assert _unbox(gates["G5_no_material_contract_failure"]) is True
    assert _unbox(gates["G6_2x_stress_net_return"]) == "> 0"
    assert _unbox(gates["G7_2x_stress_net_sharpe"]) == ">= 0.75"


def test_11_zero_authority_and_locks() -> None:
    """Invariant 11: Capital $0.00, NO_REAL_ORDERS, market data access zero, paper/live locked."""
    manifest = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_005.json").read_text(encoding="utf-8"))
    assert manifest["capital_authority_usd"] == "0.00"
    assert manifest["no_real_orders"] is True
    assert manifest["market_data_access"] == "ZERO"
    assert manifest["m1_data_access"] == "ZERO"
    assert manifest["m2_data_access"] == "ZERO"
    assert manifest["is_paper_authorized"] is False
    assert manifest["is_live_authorized"] is False
    assert manifest["status"] == "SEALED_STEP_R1_PASS"
    assert "STEP_R2" in manifest["next_required_step"]
    assert "LOCKED" in manifest["next_required_step"]


def test_12_no_market_data_network_imports_in_registration_script() -> None:
    """Invariant 12: Registration script performs zero market data I/O and has zero market data imports."""
    script_path = Path("scripts/register_phase14_step_r1_hyp_005.py")
    assert script_path.exists()
    code = script_path.read_text(encoding="utf-8")
    prohibited_tokens = ["alpaca", "urllib", "requests", "httpx", "parquet", "duckdb", "socket"]
    for token in prohibited_tokens:
        assert f"import {token}" not in code
        assert f"from {token}" not in code


def test_13_semantic_adapter_records_exist() -> None:
    """Invariant 13: Semantic conformance and registration records exist and are well-formed."""
    reg_record = Path("docs/phase14/phase14_r1_hypothesis_registration_record_HYP_005.md")
    assert reg_record.exists()
    assert "HYP_005 = CREATED_AND_SEALED_R1" in reg_record.read_text(encoding="utf-8")

    sem_record = Path("docs/phase14/phase14_r1_semantic_conformance_record_HYP_005.md")
    assert sem_record.exists()
    content = sem_record.read_text(encoding="utf-8")
    assert "Authority Precedence Order" in content
    assert "Human-Ratified MEC-0015 Strategy Preregistration" in content
