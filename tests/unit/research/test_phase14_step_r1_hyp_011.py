"""Unit and Invariant Tests for Phase 14 Step R1: HYP_011 / CORE-001 Preregistration.

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
HYP_PATH = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_011.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_011.json"
PREREG_PATH = REPO_ROOT / "docs" / "research" / "CORE-001-HYP-011-strategy-preregistration.md"
INCEPTION_MANIFEST = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "CORE_001_HYP_011_RESEARCH_INCEPTION.json"
)
REG_RECORD = (
    REPO_ROOT / "docs" / "phase14" / "phase14_r1_hypothesis_registration_record_HYP_011.md"
)
SCRIPT_PATH = REPO_ROOT / "scripts" / "register_phase14_step_r1_hyp_011.py"
PARK_MANIFEST = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_010_PARKED_NON_FALSIFIED_BLOCKER.json"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_hyp_011_identity_core_mechanism() -> None:
    h = _load(HYP_PATH)
    assert h["hypothesis_id"] == "HYP_011"
    assert h["core_id"] == "CORE-001"
    assert h["mechanism_id"] is None
    assert h["parent_hypothesis_id"] is None
    assert h["candidate_ordinal_within_core"] == 3
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert "HYP_011" not in TERMINAL_HYPOTHESIS_REGISTRY


def test_predecessor_semantics_and_hyp_010_parked() -> None:
    h = _load(HYP_PATH)
    assert h["predecessor_contexts"]["HYP_009"] == "TERMINAL_NOT_SUPPORTED_CANDIDATE_NOT_PARENT"
    assert h["predecessor_contexts"]["HYP_010"] == "BLOCKED_NON_FALSIFIED_CANDIDATE_NOT_PARENT"
    park = _load(PARK_MANIFEST)
    assert park["new_lifecycle_state"] == "HYP_010_BLOCKED_NON_FALSIFIED_BY_DIVIDEND_AUTHORITY"
    assert park["hypothesis_falsified"] is False
    assert park["historical_acquisition_executed"] is False
    assert park["performance_observed"] is False


def test_target_holdings_weights_no_signal() -> None:
    h = _load(HYP_PATH)
    assert h["target_holdings"] == {"ACWI": 0.8, "AGG": 0.2}
    params = json.loads(h["parameter_config_json"])
    assert params["target_weights"] == {"ACWI": 0.8, "AGG": 0.2}
    assert params["momentum_signal"] is False
    assert params["short_state"] is False
    assert params["volatility_targeting"] is False
    assert params["max_gross_leverage"] == 1.0
    assert params["rebalance_frequency"] == "ANNUAL"
    assert "lookback_months" not in params
    m = _load(MANIFEST_PATH)
    assert m["target_holdings"] == {"ACWI": 0.8, "AGG": 0.2}
    for banned in ("VEU", "IVV", "BIL", "QQQ", "VXUS", "BND", "TLT", "GLD"):
        assert banned not in json.dumps(params["target_weights"])


def test_whole_share_solver_constraints() -> None:
    params = json.loads(_load(HYP_PATH)["parameter_config_json"])
    assert params["rebalance_rule"] == (
        "FIRST_ELIGIBLE_OPEN_OF_EACH_NEW_CALENDAR_YEAR_TO_80_20_WHOLE_SHARES"
    )
    assert params["cash_return"] == 0.0


def test_authorities_provider_benchmark() -> None:
    m = _load(MANIFEST_PATH)
    pc = m["provider_contract"]
    assert pc["symbols"] == ["ACWI", "AGG", "SPY"]
    assert pc["bars_timeframe"] == "1Day"
    assert pc["bars_feed"] == "sip"
    assert pc["signal_price_adjustment"] == "split"
    assert pc["execution_price_adjustment"] == "raw"
    assert pc["dividend_authorities"] == {
        "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
        "AGG": "BLACKROCK_ISHARES_OFFICIAL",
        "SPY": "STATE_STREET_SPDR_OFFICIAL",
    }
    assert m["benchmark_primary"] == "SPY_BUY_AND_HOLD"


def test_partitions_prospective_minimums() -> None:
    m = _load(INCEPTION_MANIFEST)
    assert m["historical_partition"] == {
        "start": "2016-01-01",
        "end": "2024-12-31",
        "classification": "HISTORICAL_EXPOSED_REPLICATION_NOT_RESEARCHER_BLIND",
    }
    assert m["recent_stress_partition"]["classification"] == (
        "PUBLICLY_EXPOSED_RECENT_STRESS_NOT_PRISTINE_NON_DECISIVE"
    )
    assert m["quarantine"]["classification"] == "STRICT_ZERO_ACCESS_PRE_PROSPECTIVE_GAP"
    assert m["prospective"]["rule"] == (
        "FIRST_ELIGIBLE_REGULAR_SESSION_OPEN_STRICTLY_AFTER_R1_COMMIT_TIMESTAMP"
    )
    assert m["prospective"]["minimum_eligible_sessions"] == 504
    assert m["prospective"]["minimum_annual_rebalances"] == 2


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


def test_gate_reinvocation_reproduces_token() -> None:
    h = _load(HYP_PATH)
    m = _load(MANIFEST_PATH)
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_011",
        candidate_hypothesis_version="v1.0",
        economic_rationale=str(h["economic_rationale"]),
        target_symbol="ACWI",
        target_timeframe="1Day",
        feature_dependencies=list(h["feature_dependencies"]),
        parameter_search_grid={
            "core_specification": ["CORE_001_GLOBAL_80_20_STATIC_ALLOCATION_V1"],
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
        proposed_dataset_id="DS_CORE001_HYP011_ACWI_AGG_SPY_ALPACA_1DAY_SIP_2016_2024",
        proposed_data_window=("2016-01-01T00:00:00+00:00", "2024-12-31T23:59:59+00:00"),
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
    assert m["hypothesis_sha256"] == hashlib.sha256(
        HYP_PATH.read_bytes()
    ).hexdigest()
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
    assert "HYP_011 = PREREGISTERED_SEALED_R1" in text
    assert "AUTH_INCEPTION_HYP_011_d975fd46ad1a1b2f" in text
