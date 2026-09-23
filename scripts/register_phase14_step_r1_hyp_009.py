"""Phase 14 Step R1 Registration & Sealing Script: HYP_009 (CORE-001 SPY Monthly 10M SMA Long/Cash).

Strictly enforces:
1. Submits frozen CORE-001/HYP_009 preregistration to ResearchReInceptionGate (real invocation).
2. Formally evaluates all 6 institutional invariants (K = 1, no search).
3. Generates InceptionAuthorizationToken bound to HYP_009.
4. Transitions docs/phase14/hypotheses/HYP_009.json PROPOSED_NOT_PREREGISTERED
   -> R1_PREREGISTERED_SEALED under gate authority (scientific fields untouched).
5. Emits canonical R1 Registration Manifest for HYP_009 with pinned contract hashes.
6. Strictly maintains fail-closed boundaries: zero market data loading, $0.00 capital, backtest locked.

Deviations from the HYP_005 script (documented in the R1 registration record):
- No phase8.5 mirror: HYP_009 uses the custom CORE format (core_id/state/open_before_r1),
  which is not a bare HypothesisSpecification; phase14 is the sole canonical home.
- No data/ gitignored mirrors: surgical tracked-files-only change.
- hypothesis_sha256 = SHA-256 over sealed file bytes (custom format is not directly
  consumable by calculate_hypothesis_spec_sha256).
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.reinception import (
    InceptionAuthorizationToken,
    InceptionDecision,
    ResearchInceptionProposal,
    ResearchReInceptionGate,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    InvalidationCriteria,
    SplitPolicy,
)

REGISTERED_AT_UTC = "2026-09-23T22:41:00Z"
HUMAN_AUTHORIZATION = "AUTHORIZE_CORE_001_HYP_009_R1_PREREGISTRATION"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_canonical(obj: object) -> str:
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(obj).encode("utf-8")
    ).hexdigest()


def build_strategy_contract() -> dict:
    return {
        "core_id": "CORE-001",
        "hypothesis_id": "HYP_009",
        "working_title": "SPY Monthly 10-Month SMA Long/Cash Core",
        "strategy_family": "LONG_HORIZON_MOVING_AVERAGE_TREND_FILTER",
        "instrument": "SPY",
        "frequency": "MONTHLY",
        "decision_date_rule": "LAST_REGULAR_TRADING_SESSION_OF_EACH_CALENDAR_MONTH",
        "direction_states": ["LONG", "CASH"],
        "signal": "LONG_IF_SIGNAL_LEVEL_GT_SMA_10M_ELSE_CASH",
        "lookback_month_ends": 10,
        "equality_behavior": "CASH",
        "tolerance_band": False,
        "hysteresis": False,
        "confirmation_indicator": False,
        "stop_loss": False,
        "trailing_stop": False,
        "secondary_filter": False,
        "volatility_filter": False,
        "liquidity_filter": False,
        "macro_filter": False,
        "machine_learning": False,
        "discretionary_override": False,
        "long_state_exposure": "1.00_SPY_NOTIONAL",
        "cash_state_exposure": "0.00",
        "max_gross_leverage": 1.0,
        "volatility_targeting": False,
        "cash_return": 0.0,
        "benchmark": "SPY_BUY_AND_HOLD",
        "execution_timing": "NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL",
        "same_close_execution": False,
        "rebalance_rule": "TRADE_ONLY_ON_STATE_CHANGE",
        "warmup_completed_month_end_observations": 10,
        "pre_warmup_behavior": "NO_SIGNAL_FAIL_CLOSED",
        "calendar_authority": "CANONICAL_NYSE_CALENDAR_IN_REPOSITORY",
        "missing_data_policy": "FAIL_CLOSED_NO_INTERPOLATION_NO_FORWARD_FILL",
    }


def build_provider_contract() -> dict:
    return {
        "bars_provider": "ALPACA_HISTORICAL_STOCK_BARS",
        "bars_endpoint": "/v2/stocks/SPY/bars",
        "bars_timeframe": "1Day",
        "bars_feed": "sip",
        "signal_price_adjustment": "split",
        "execution_price_adjustment": "raw",
        "dividend_authority": "STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS",
        "signal_construction": "CAUSAL_TOTAL_RETURN_INDEX_G_T_EQ_(P_T_PLUS_D_T)_DIV_P_T-1_EX_DATE_ONLY",
        "vendor_adjusted_close_as_authority": False,
        "no_provider_substitution": True,
        "no_provider_splicing": True,
        "missing_coverage_policy": "BLOCKED_DATA_ENTITLEMENT",
    }


def build_sample_partitions() -> dict:
    return {
        "research_start": "2016-01-01",
        "warmup": {"start": "2016-01-01", "end": "2016-10-31", "pnl": "ZERO"},
        "m1": {
            "start": "2016-11-01",
            "end": "2020-12-31",
            "role": "DESIGN_AND_IMPLEMENTATION_REPLICATION_SAMPLE",
            "classification": "HISTORICAL_EXPOSED_REPLICATION",
        },
        "m2": {
            "start": "2021-01-01",
            "end": "2024-12-31",
            "role": "LOCKED_HISTORICAL_OOS",
            "classification": "LOCKED_HISTORICAL_OOS_NOT_PRISTINE_RESEARCHER_BLIND",
            "firewall": "NO_M2_READS_UNTIL_R1_SEALED_AND_M1_DATASET_COMPLETE_AND_M1_RESULT_SEALED_AND_EXPLICIT_HUMAN_AUTH",
        },
        "m3": {
            "start": "2025-01-01",
            "end": "2026-08-14",
            "role": "PUBLICLY_EXPOSED_RECENT_STRESS_SAMPLE",
            "classification": "NOT_PRISTINE_OOS",
            "rescue_rule": "M3_MUST_NOT_RESCUE_FAILED_M2",
        },
        "quarantine": {
            "start": "2026-08-15",
            "end": "PROSPECTIVE_START_EXCLUSIVE",
            "classification": "STRICT_ZERO_ACCESS_PRE_PROSPECTIVE_GAP",
        },
        "prospective": {
            "rule": "FIRST_NYSE_REGULAR_SESSION_OPEN_STRICTLY_AFTER_R1_COMMIT_TIMESTAMP",
            "state_at_r1": "LOCKED_ZERO_ACCESS",
        },
    }


def build_acceptance_gates() -> dict:
    return {
        "logical_conjunction": "G1 AND G2 AND G3 AND G4 AND G5 AND G6",
        "G1_net_total_return": "> 0",
        "G2_net_annualized_sharpe": ">= 0.50",
        "sharpe_convention": {
            "periods_per_year": 252,
            "ddof": 1,
            "risk_free_rate": 0,
            "zero_variance": "FAIL_CLOSED",
        },
        "G3_max_drawdown": "<= 0.35",
        "G4_core_mdd_lt_benchmark_mdd": True,
        "G5_10bps_stress_net_total_return": "> 0",
        "G6_no_material_contract_failure": True,
        "net_of": "BASELINE_FRICTION",
        "no_discretionary_override": True,
    }


def register_step_r1_hyp_009() -> InceptionAuthorizationToken:
    print("================================================================================")
    print("ACASH PHASE 14 STEP R1: HYPOTHESIS REGISTRATION & SEALING (HYP_009 / CORE-001)")
    print("SPY Monthly 10-Month SMA Long/Cash Core | K = 1 | No search | No backtest")
    print("================================================================================")

    prereg_doc_path = Path("docs/research/CORE-001-HYP-009-strategy-preregistration.md")
    if not prereg_doc_path.exists():
        raise DataContractError(f"CRITICAL: Frozen pre-registration document not found at '{prereg_doc_path}'.")
    prereg_bytes = prereg_doc_path.read_bytes()
    prereg_sha256 = hashlib.sha256(prereg_bytes).hexdigest()
    prereg_text = prereg_bytes.decode("utf-8")
    for marker in (
        "PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_R1_SEAL",
        "OPEN_BEFORE_R1_UNRESOLVED_COUNT = 0",
        "HYP_009 = PROPOSED_NOT_PREREGISTERED",
        "EMPIRICAL_EXECUTION = NOT_AUTHORIZED",
    ):
        if marker not in prereg_text:
            raise DataContractError(f"CRITICAL: Preregistration document missing marker '{marker}'.")
    print(f"[Pre-Flight] Frozen Pre-Registration SHA-256: {prereg_sha256}")

    hyp_path = Path("docs/phase14/hypotheses/HYP_009.json")
    if not hyp_path.exists():
        raise DataContractError("CRITICAL: HYP_009 proposal record not found.")
    hyp_pre = json.loads(hyp_path.read_text(encoding="utf-8"))
    if hyp_pre["state"] != "PROPOSED_NOT_PREREGISTERED":
        raise DataContractError(f"CRITICAL: HYP_009 state must be PROPOSED_NOT_PREREGISTERED, got {hyp_pre['state']}.")
    hyp_pre_sha256 = _sha256_file(hyp_path)
    print(f"[Pre-Flight] HYP_009 pre-R1 proposal record SHA-256: {hyp_pre_sha256}")

    upstream_authority_hashes = {
        "inception_doc_sha256": _sha256_file(Path("docs/phase14/CORE_001_HYP_009_RESEARCH_INCEPTION.md")),
        "inception_manifest_sha256": _sha256_file(Path("docs/phase14/manifests/CORE_001_HYP_009_RESEARCH_INCEPTION.json")),
        "semantic_conformance_record_sha256": _sha256_file(
            Path("docs/phase14/phase14_pre_r1_semantic_conformance_record_HYP_009.md")
        ),
        "semantic_conformance_manifest_sha256": _sha256_file(
            Path("docs/phase14/manifests/HYP_009_PRE_R1_SEMANTIC_CONFORMANCE.json")
        ),
        "hyp_008_retirement_manifest_sha256": _sha256_file(
            Path("docs/phase14/manifests/HYP_008_PRE_R1_RETIREMENT.json")
        ),
        "hyp_009_pre_r1_proposal_record_sha256": hyp_pre_sha256,
    }

    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_009",
        candidate_hypothesis_version="v1.0",
        economic_rationale=str(hyp_pre["economic_rationale"]),
        target_symbol="SPY",
        target_timeframe="1Day",
        feature_dependencies=list(hyp_pre["feature_dependencies"]),
        parameter_search_grid={
            "core_specification": ["CORE_001_SPY_MONTHLY_10M_SMA_LONG_CASH_V1"],
        },
        planned_trial_count=1,
        target_horizons=[21],  # Non-binding schema compatibility stub (see conformance record)
        primary_horizon=21,  # Non-binding schema compatibility stub
        expected_direction=ExpectedDirection.LONG,  # Non-binding schema stub (strategy is LONG/CASH)
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.000001"),  # Non-binding schema compatibility stub
            min_hac_t_stat=Decimal("1.96"),  # Non-binding schema compatibility stub
            max_feature_autocorrelation=Decimal("0.999999"),  # Non-binding schema compatibility stub
            min_cost_adjusted_spread_ratio=Decimal("1.0"),  # Non-binding schema compatibility stub
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("0.0"),  # Non-binding DTO stub; binding friction is 2bps/10bps in R1 contracts
            roundtrip_broker_fee_bps=Decimal("0.0"),
            fixed_slippage_bps=Decimal("0.0"),
        ),
        proposed_dataset_id="DS_SPY_CORE001_ALPACA_1DAY_SIP_2016_2026",
        proposed_data_window=("2016-01-01T00:00:00+00:00", "2026-08-15T00:00:00+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),  # Transient non-binding schema compatibility metadata
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        ),
        author="external_research_authority_specification__implementation_only_encoding",
        proposed_at_utc=REGISTERED_AT_UTC,
    )

    print("\n[Step 1] Submitting candidate proposal HYP_009 to ResearchReInceptionGate...")
    token = ResearchReInceptionGate.evaluate_reinception_proposal(proposal=proposal)
    print(f" -> Gate Decision: {token.decision.value}")
    print(f" -> Token ID: {token.token_id}")
    print(f" -> Proposal SHA-256: {token.proposal_sha256}")
    if token.decision != InceptionDecision.INCEPTION_AUTHORIZED:
        raise DataContractError(f"Re-Inception Gate rejected proposal: {token.decision}")
    if token.authorized_hypothesis_id != "HYP_009":
        raise DataContractError(f"Token hypothesis mismatch: {token.authorized_hypothesis_id}")
    if token.capital_authority_usd != Decimal("0.00"):
        raise DataContractError("Token capital authority must be $0.00")
    if token.is_strategy_qualified is not False:
        raise DataContractError("Token must have is_strategy_qualified = False")
    if token.is_paper_authorized is not False:
        raise DataContractError("Token must have is_paper_authorized = False")
    if token.is_live_authorized is not False:
        raise DataContractError("Token must have is_live_authorized = False")

    strategy_contract = build_strategy_contract()
    provider_contract = build_provider_contract()
    sample_partitions = build_sample_partitions()
    acceptance_gates = build_acceptance_gates()
    contract_hashes = {
        "strategy_specification_hash": _sha256_canonical(strategy_contract),
        "provider_contract_hash": _sha256_canonical(provider_contract),
        "sample_partition_hash": _sha256_canonical(sample_partitions),
        "gate_contract_hash": _sha256_canonical(acceptance_gates),
    }
    print("\n[Step 2] Contract hashes:")
    for key, digest in contract_hashes.items():
        print(f" -> {key}: {digest}")

    hyp_sealed = dict(hyp_pre)
    hyp_sealed["state"] = "R1_PREREGISTERED_SEALED"
    hyp_sealed["registered_at_utc"] = REGISTERED_AT_UTC
    hyp_sealed["inception_token_id"] = token.token_id
    hyp_sealed["proposal_sha256"] = token.proposal_sha256
    hyp_sealed["preregistration_sha256"] = prereg_sha256
    hyp_sealed["r1_manifest"] = "docs/phase14/manifests/manifest_r1_HYP_009.json"
    hyp_path.write_text(json.dumps(hyp_sealed, indent=2), encoding="utf-8")
    hyp_sha256 = _sha256_file(hyp_path)
    print(f"\n[Step 3] HYP_009 sealed (state=R1_PREREGISTERED_SEALED) SHA-256: {hyp_sha256}")

    manifest_payload = {
        "manifest_type": "HYPOTHESIS_REGISTRATION_MANIFEST",
        "hypothesis_id": "HYP_009",
        "hypothesis_ordinal": 9,
        "hypothesis_ordinal_alias": "HYP_009",
        "core_id": "CORE-001",
        "mechanism_id": None,
        "canonical_title": "HYP_009 — SPY Monthly 10-Month SMA Long/Cash Core",
        "hypothesis_version": "v1.0",
        "hypothesis_sha256": hyp_sha256,
        "registered_at_utc": REGISTERED_AT_UTC,
        "author": "external_research_authority_specification__implementation_only_encoding",
        "target_symbol": "SPY",
        "primary_timeframe": "1Day",
        "search_trial_count_k": 1,
        "human_authorization": HUMAN_AUTHORIZATION,
        "inception_token_id": token.token_id,
        "proposal_sha256": token.proposal_sha256,
        "preregistration_sha256": prereg_sha256,
        "upstream_authority_hashes": upstream_authority_hashes,
        "contract_hashes": contract_hashes,
        "strategy_contract": strategy_contract,
        "provider_contract": provider_contract,
        "sample_partitions": sample_partitions,
        "acceptance_gates": acceptance_gates,
        "legacy_schema_semantics": "NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY",
        "status": "SEALED_STEP_R1_PASS",
        "capital_authority_usd": "0.00",
        "no_real_orders": True,
        "market_data_access": "ZERO",
        "m1_data_access": "ZERO",
        "m2_data_access": "ZERO",
        "m3_data_access": "ZERO",
        "is_paper_authorized": False,
        "is_live_authorized": False,
        "next_required_step": "AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION",
    }
    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest_payload)
    manifest_digest = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    manifest_payload["manifest_sha256"] = manifest_digest
    man_path = Path("docs/phase14/manifests/manifest_r1_HYP_009.json")
    man_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    print(f"\n[Step 4] R1 Manifest written to {man_path} SHA-256: {manifest_digest}")

    print("\n================================================================================")
    print("HYP_009 CANONICAL R1 REGISTRATION COMPLETED & SEALED!")
    print("Status: R1 PASS / SEALED (R2 LOCKED / CAPITAL $0.00 / M2 LOCKED / NO_REAL_ORDERS)")
    print("================================================================================")
    return token


if __name__ == "__main__":
    register_step_r1_hyp_009()
