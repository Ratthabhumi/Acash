"""Unit and Invariant Tests for Phase 14 Step R1: HYP_009 / CORE-001 Preregistration.

Implementation-only governance tests. No network calls, no market-data reads,
no signal/PnL/Sharpe/MDD computation. Asserts exclusively on committed
governance artifacts plus a deterministic re-invocation of the real gate.
"""

import hashlib
import json
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
from decimal import Decimal

REPO_ROOT = Path(__file__).resolve().parents[3]
HYP_PATH = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_009.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_009.json"
PREREG_PATH = REPO_ROOT / "docs" / "research" / "CORE-001-HYP-009-strategy-preregistration.md"
REG_RECORD_PATH = (
    REPO_ROOT / "docs" / "phase14" / "phase14_r1_hypothesis_registration_record_HYP_009.md"
)
SCRIPT_PATH = REPO_ROOT / "scripts" / "register_phase14_step_r1_hyp_009.py"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_r1_state_and_gate_token() -> None:
    h = _load(HYP_PATH)
    m = _load(MANIFEST_PATH)
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert m["status"] == "SEALED_STEP_R1_PASS"
    assert m["inception_token_id"].startswith("AUTH_INCEPTION_HYP_009_")
    assert h["inception_token_id"] == m["inception_token_id"]
    assert h["proposal_sha256"] == m["proposal_sha256"]
    assert h["registered_at_utc"] == m["registered_at_utc"]
    assert "HYP_009" not in TERMINAL_HYPOTHESIS_REGISTRY


def test_gate_reinvocation_reproduces_token() -> None:
    """Deterministic re-invocation of the real gate reproduces token ID + proposal SHA."""
    h = _load(HYP_PATH)
    m = _load(MANIFEST_PATH)
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_009",
        candidate_hypothesis_version="v1.0",
        economic_rationale=str(json.loads(HYP_PATH.read_text(encoding="utf-8"))["economic_rationale"]),
        target_symbol="SPY",
        target_timeframe="1Day",
        feature_dependencies=[
            "spy_month_end_signal_levels_total_return_or_equivalent_causally_reconstructed",
            "spy_authoritative_split_history",
            "spy_authoritative_dividend_history_STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS",
            "canonical_nyse_calendar_with_sealed_unscheduled_closure_corrections",
        ],
        parameter_search_grid={
            "core_specification": ["CORE_001_SPY_MONTHLY_10M_SMA_LONG_CASH_V1"],
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
        proposed_dataset_id="DS_SPY_CORE001_ALPACA_1DAY_SIP_2016_2026",
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
    assert token.capital_authority_usd == Decimal("0.00")
    assert token.is_strategy_qualified is False
    assert token.is_paper_authorized is False
    assert token.is_live_authorized is False


def test_strategy_specification_hash() -> None:
    m = _load(MANIFEST_PATH)
    sc = m["strategy_contract"]
    assert sc["instrument"] == "SPY"
    assert sc["frequency"] == "MONTHLY"
    assert sc["signal"] == "LONG_IF_SIGNAL_LEVEL_GT_SMA_10M_ELSE_CASH"
    assert sc["lookback_month_ends"] == 10
    assert sc["equality_behavior"] == "CASH"
    assert sc["direction_states"] == ["LONG", "CASH"]
    assert sc["max_gross_leverage"] == 1.0
    assert sc["volatility_targeting"] is False
    assert sc["cash_return"] == 0.0
    assert sc["execution_timing"] == "NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL"
    assert sc["rebalance_rule"] == "TRADE_ONLY_ON_STATE_CHANGE"
    assert m["contract_hashes"]["strategy_specification_hash"] == hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(sc).encode("utf-8")
    ).hexdigest()


def test_provider_contract_hash() -> None:
    m = _load(MANIFEST_PATH)
    pc = m["provider_contract"]
    assert pc["bars_provider"] == "ALPACA_HISTORICAL_STOCK_BARS"
    assert pc["bars_endpoint"] == "/v2/stocks/SPY/bars"
    assert pc["bars_timeframe"] == "1Day"
    assert pc["bars_feed"] == "sip"
    assert pc["signal_price_adjustment"] == "split"
    assert pc["execution_price_adjustment"] == "raw"
    assert pc["dividend_authority"] == "STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS"
    assert pc["vendor_adjusted_close_as_authority"] is False
    assert pc["no_provider_substitution"] is True
    assert m["contract_hashes"]["provider_contract_hash"] == hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(pc).encode("utf-8")
    ).hexdigest()


def test_sample_partition_hash_and_exact_dates() -> None:
    m = _load(MANIFEST_PATH)
    sp = m["sample_partitions"]
    assert sp["research_start"] == "2016-01-01"
    assert (sp["warmup"]["start"], sp["warmup"]["end"]) == ("2016-01-01", "2016-10-31")
    assert (sp["m1"]["start"], sp["m1"]["end"]) == ("2016-11-01", "2020-12-31")
    assert (sp["m2"]["start"], sp["m2"]["end"]) == ("2021-01-01", "2024-12-31")
    assert sp["m2"]["classification"] == "LOCKED_HISTORICAL_OOS_NOT_PRISTINE_RESEARCHER_BLIND"
    assert (sp["m3"]["start"], sp["m3"]["end"]) == ("2025-01-01", "2026-08-14")
    assert sp["m3"]["classification"] == "NOT_PRISTINE_OOS"
    assert sp["m3"]["rescue_rule"] == "M3_MUST_NOT_RESCUE_FAILED_M2"
    assert sp["quarantine"]["start"] == "2026-08-15"
    assert sp["quarantine"]["classification"] == "STRICT_ZERO_ACCESS_PRE_PROSPECTIVE_GAP"
    assert sp["prospective"]["rule"] == (
        "FIRST_NYSE_REGULAR_SESSION_OPEN_STRICTLY_AFTER_R1_COMMIT_TIMESTAMP"
    )
    assert sp["prospective"]["state_at_r1"] == "LOCKED_ZERO_ACCESS"
    assert m["contract_hashes"]["sample_partition_hash"] == hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(sp).encode("utf-8")
    ).hexdigest()


def test_gate_contract_hash_and_operators() -> None:
    m = _load(MANIFEST_PATH)
    g = m["acceptance_gates"]
    assert g["logical_conjunction"] == "G1 AND G2 AND G3 AND G4 AND G5 AND G6"
    assert g["G1_net_total_return"] == "> 0"
    assert g["G2_net_annualized_sharpe"] == ">= 0.50"
    assert g["sharpe_convention"]["periods_per_year"] == 252
    assert g["sharpe_convention"]["ddof"] == 1
    assert g["sharpe_convention"]["risk_free_rate"] == 0
    assert g["G3_max_drawdown"] == "<= 0.35"
    assert g["G4_core_mdd_lt_benchmark_mdd"] is True
    assert g["G5_10bps_stress_net_total_return"] == "> 0"
    assert g["G6_no_material_contract_failure"] is True
    assert m["contract_hashes"]["gate_contract_hash"] == hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(g).encode("utf-8")
    ).hexdigest()
    assert m["search_trial_count_k"] == 1


def test_manifest_self_hash_and_pins() -> None:
    raw = MANIFEST_PATH.read_bytes()
    m = json.loads(raw.decode("utf-8"))
    payload = {k: v for k, v in m.items() if k != "manifest_sha256"}
    assert m["manifest_sha256"] == hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
    ).hexdigest()
    assert m["preregistration_sha256"] == hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest()
    assert m["hypothesis_sha256"] == hashlib.sha256(HYP_PATH.read_bytes()).hexdigest()
    up = m["upstream_authority_hashes"]
    assert up["inception_doc_sha256"] == hashlib.sha256(
        (REPO_ROOT / "docs" / "phase14" / "CORE_001_HYP_009_RESEARCH_INCEPTION.md").read_bytes()
    ).hexdigest()
    assert up["hyp_009_pre_r1_proposal_record_sha256"] != m["hypothesis_sha256"]


def test_hyp_009_scientific_fields_untouched() -> None:
    h = _load(HYP_PATH)
    assert h["target_horizons"] == [21]
    assert h["primary_horizon"] == 21
    assert h["expected_direction"] == "LONG"
    params = json.loads(h["parameter_config_json"])
    assert params["signal_name"] == "10_MONTH_SIMPLE_MOVING_AVERAGE"
    assert params["lookback_month_ends"] == 10
    assert params["equality_behavior"] == "CASH"
    assert params["max_gross_leverage"] == 1.0
    assert params["volatility_targeting"] is False
    assert params["cash_return"] == 0.0
    assert h["open_before_r1"] == [
        "OPEN_BEFORE_R1_TOTAL_RETURN_SIGNAL_CONSTRUCTION",
        "OPEN_BEFORE_R1_EXECUTION_COST_MODEL",
        "OPEN_BEFORE_R1_SAMPLE_PARTITION_DATES",
        "OPEN_BEFORE_R1_LOCKED_OOS_BOUNDARY",
        "OPEN_BEFORE_R1_PROSPECTIVE_BOUNDARY",
    ]


def test_zero_authority_locks() -> None:
    m = _load(MANIFEST_PATH)
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True
    assert m["market_data_access"] == "ZERO"
    assert m["m1_data_access"] == "ZERO"
    assert m["m2_data_access"] == "ZERO"
    assert m["m3_data_access"] == "ZERO"
    assert m["is_paper_authorized"] is False
    assert m["is_live_authorized"] is False
    assert m["status"] == "SEALED_STEP_R1_PASS"
    assert m["legacy_schema_semantics"] == "NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY"
    assert m["next_required_step"] == "AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION"


def test_registration_script_has_no_market_data_imports() -> None:
    assert SCRIPT_PATH.is_file()
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("alpaca", "urllib", "requests", "httpx", "parquet", "duckdb", "socket"):
        assert f"import {token}" not in code
        assert f"from {token}" not in code


def test_registration_record_exists_and_states_verdict() -> None:
    assert REG_RECORD_PATH.is_file()
    text = REG_RECORD_PATH.read_text(encoding="utf-8")
    assert "HYP_009 = PREREGISTERED_SEALED_R1" in text
    assert "AUTH_INCEPTION_HYP_009_e2ee71d26cf5891c" in text
    assert "AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION" in text
