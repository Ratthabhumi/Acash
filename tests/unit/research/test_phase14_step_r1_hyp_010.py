"""Unit and Invariant Tests for Phase 14 Step R1: HYP_010 / CORE-001 Preregistration.

Implementation-only governance tests. No network calls, no market-data reads,
no signal/PnL computation. Asserts exclusively on committed artifacts plus a
deterministic re-invocation of the real gate.
"""

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, cast

from acash.core.serialization import CanonicalConfigSerializer
from acash.research.reinception import (
    InceptionDecision,
    ResearchInceptionProposal,
    ResearchReInceptionGate,
    TERMINAL_HYPOTHESIS_REGISTRY,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    InvalidationCriteria,
    SplitPolicy,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
HYP_PATH = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_010.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_010.json"
PREREG_PATH = REPO_ROOT / "docs" / "research" / "CORE-001-HYP-010-strategy-preregistration.md"
INCEPTION_MANIFEST = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "CORE_001_HYP_010_RESEARCH_INCEPTION.json"
)
REG_RECORD = (
    REPO_ROOT / "docs" / "phase14" / "phase14_r1_hypothesis_registration_record_HYP_010.md"
)
SCRIPT_PATH = REPO_ROOT / "scripts" / "register_phase14_step_r1_hyp_010.py"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_hyp_010_identity_core_linkage_no_mechanism() -> None:
    h = _load(HYP_PATH)
    assert h["hypothesis_id"] == "HYP_010"
    assert h["core_id"] == "CORE-001"
    assert h["mechanism_id"] is None
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert "HYP_010" not in TERMINAL_HYPOTHESIS_REGISTRY


def test_hyp_009_terminal_untouched_not_parent() -> None:
    h = _load(HYP_PATH)
    assert h["parent_hypothesis_id"] is None
    assert h["predecessor_candidate_context"] == "HYP_009"
    assert h["predecessor_relationship"] == (
        "TERMINAL_PREDECESSOR_CANDIDATE_NOT_PARENT_NOT_AMENDED_NOT_RESCUED"
    )
    term = _load(REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_TERMINAL_M2_DECISION.json")
    assert term["hyp_009_state"] == "HYP_009_TERMINAL_NOT_SUPPORTED_AT_LOCKED_M2"
    assert term["successor_hypothesis_created"] is False


def test_etf_universe_and_bil_signal_only() -> None:
    h = _load(HYP_PATH)
    assert h["target_universe"] == ["SPY", "VEU", "AGG"]
    assert h["signal_only_assets"] == ["BIL"]
    params = json.loads(h["parameter_config_json"])
    assert params["target_holdings"] == ["SPY", "VEU", "AGG"]
    m = _load(MANIFEST_PATH)
    assert m["target_universe"] == ["SPY", "VEU", "AGG"]
    assert m["signal_only_assets"] == ["BIL"]
    for banned in ("QQQ", "VXUS", "BND", "SHY", "TLT", "GLD"):
        assert banned not in json.dumps(params)


def test_frequency_momentum_formula_warmup() -> None:
    h = _load(HYP_PATH)
    params = json.loads(h["parameter_config_json"])
    assert params["frequency"] == "MONTHLY"
    m = _load(INCEPTION_MANIFEST)
    assert m["momentum_formula"] == "M12_ASSET_T_EQ_TR_T_DIV_TR_T-12_MINUS_1"
    assert m["warmup_month_end_observations"] == 13
    assert m["warmup_window"] == ["2016-01-01", "2017-01-31"]


def test_absolute_relative_rules_and_ties() -> None:
    m = _load(INCEPTION_MANIFEST)
    assert m["absolute_rule"] == "RISK_ON_IFF_SPY_M12_GT_BIL_M12_ELSE_AGG"
    assert m["absolute_tie"] == "AGG"
    assert m["relative_rule"] == "SPY_IFF_SPY_M12_GTE_VEU_M12_ELSE_VEU"
    assert m["relative_tie"] == "SPY"


def test_agg_not_ranked_trade_only_on_change() -> None:
    m = _load(MANIFEST_PATH)
    assert m["strategy_contract"]["target_holdings"] == ["SPY", "VEU", "AGG"]
    params = json.loads(_load(HYP_PATH)["parameter_config_json"])
    assert params["rebalance_rule"] == "TRADE_ONLY_ON_TARGET_CHANGE"
    assert params["max_gross_leverage"] == 1.0
    assert params["volatility_targeting"] is False
    assert params["short_state"] is False


def test_next_session_open_execution() -> None:
    m = _load(INCEPTION_MANIFEST)
    assert m["execution_timing"] == "NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL"


def test_partitions_no_fake_oos() -> None:
    m = _load(INCEPTION_MANIFEST)
    assert m["historical_partition"]["classification"] == (
        "HISTORICAL_EXPOSED_REPLICATION_NOT_RESEARCHER_BLIND"
    )
    assert m["recent_stress_partition"]["classification"] == (
        "PUBLICLY_EXPOSED_RECENT_STRESS_NOT_PRISTINE_NON_DECISIVE"
    )
    assert m["quarantine"]["classification"] == "STRICT_ZERO_ACCESS_PRE_PROSPECTIVE_GAP"
    assert "NOT_RESEARCHER_BLIND" in m["historical_partition"]["classification"]
    assert "NON_DECISIVE" in m["recent_stress_partition"]["classification"]
    assert m["prospective"]["rule"] == (
        "FIRST_NYSE_REGULAR_SESSION_OPEN_STRICTLY_AFTER_R1_COMMIT_TIMESTAMP"
    )
    assert m["prospective"]["minimum_completed_decisions"] == 24
    assert m["prospective"]["minimum_eligible_sessions"] == 504


def test_gates_exact_and_k_equals_1() -> None:
    m = _load(MANIFEST_PATH)
    g = m["acceptance_gates"]
    assert g["logical_conjunction"] == "G1 AND G2 AND G3 AND G4 AND G5 AND G6"
    assert g["G1_net_total_return"] == "> 0"
    assert g["G2_net_annualized_sharpe"] == ">= 0.50"
    assert g["G3_max_drawdown"] == "<= 0.35"
    assert g["G4_core_mdd_lt_benchmark_mdd"] is True
    assert g["G5_10bps_stress_net_total_return"] == "> 0"
    assert g["G6_no_material_contract_failure"] is True
    assert m["search_trial_count_k"] == 1
    assert m["contract_hashes"]["gate_contract_hash"] == (
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
    )


def test_sponsor_and_provider_contracts() -> None:
    m = _load(MANIFEST_PATH)
    pc = m["provider_contract"]
    assert pc["symbols"] == ["SPY", "VEU", "AGG", "BIL"]
    assert pc["bars_timeframe"] == "1Day"
    assert pc["bars_feed"] == "sip"
    assert pc["signal_price_adjustment"] == "split"
    assert pc["execution_price_adjustment"] == "raw"
    assert pc["dividend_authorities"] == {
        "SPY": "STATE_STREET_SPDR_OFFICIAL",
        "BIL": "STATE_STREET_SPDR_OFFICIAL",
        "VEU": "VANGUARD_OFFICIAL",
        "AGG": "BLACKROCK_ISHARES_OFFICIAL",
    }


def test_gate_reinvocation_reproduces_token() -> None:
    h = _load(HYP_PATH)
    m = _load(MANIFEST_PATH)
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_010",
        candidate_hypothesis_version="v1.0",
        economic_rationale=str(h["economic_rationale"]),
        target_symbol="SPY",
        target_timeframe="1Day",
        feature_dependencies=list(h["feature_dependencies"]),
        parameter_search_grid={
            "core_specification": ["CORE_001_ETF_NATIVE_DUAL_MOMENTUM_V1"],
        },
        planned_trial_count=1,
        target_horizons=[21],
        primary_horizon=21,
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
        proposed_dataset_id="DS_ETF_CORE001_HYP010_ALPACA_1DAY_SIP_2016_2026",
        proposed_data_window=("2016-01-01T00:00:00+00:00", "2026-08-15T00:00:00+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        ),
        author="external_research_authority_specification__implementation_only_encoding",
        proposed_at_utc=str(h["registered_at_utc"]),
    )
    token = ResearchReInceptionGate.evaluate_reinception_proposal(proposal=proposal)
    assert token.decision == InceptionDecision.INCEPTION_AUTHORIZED
    assert token.token_id == m["inception_token_id"]
    assert token.proposal_sha256 == m["proposal_sha256"]


def test_manifest_self_hash_and_pins() -> None:
    m = _load(MANIFEST_PATH)
    payload = {k: v for k, v in m.items() if k != "manifest_sha256"}
    assert m["manifest_sha256"] == hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
    ).hexdigest()
    assert m["preregistration_sha256"] == hashlib.sha256(
        PREREG_PATH.read_bytes()
    ).hexdigest()
    # Post-R1 reconciliation: the historical R1 manifest pins the pre-reconciliation
    # live bytes; the live record carries the authorized metadata transition.
    assert m["hypothesis_sha256"] == (
        "a32698926a8968820b81239d910a4e5db42f6b101cd09fb73c859b0675464d0b"
    )
    assert hashlib.sha256(HYP_PATH.read_bytes()).hexdigest() == (
        "b4061f1ccef2149e290c2d66693e0ccc09de137a04d9d55b08fd2a3f8046764d"
    )
    assert m["status"] == "SEALED_STEP_R1_PASS"


def test_zero_access_locks() -> None:
    m = _load(MANIFEST_PATH)
    assert m["market_data_access"] == "ZERO"
    assert m["historical_data_access"] == "ZERO"
    assert m["recent_stress_access"] == "ZERO"
    assert m["quarantine_access"] == "ZERO"
    assert m["prospective_access"] == "ZERO"
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True
    assert m["is_paper_authorized"] is False
    assert m["is_live_authorized"] is False


def test_script_has_no_market_data_imports_and_record_exists() -> None:
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("alpaca", "urllib", "requests", "httpx", "parquet", "duckdb", "socket"):
        assert f"import {token}" not in code
        assert f"from {token}" not in code
    assert REG_RECORD.is_file()
    text = REG_RECORD.read_text(encoding="utf-8")
    assert "HYP_010 = PREREGISTERED_SEALED_R1" in text
    assert "AUTH_INCEPTION_HYP_010_baf1924f0934d395" in text
