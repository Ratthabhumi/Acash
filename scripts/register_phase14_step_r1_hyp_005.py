"""Phase 14 Step R1 Registration & Sealing Script: HYP_005 (MEC-0015 Noise-Area Intraday Momentum).

Strictly enforces:
1. Submits human-ratified MEC-0015 strategy replication proposal to ResearchReInceptionGate.
2. Formally evaluates all 6 institutional invariants.
3. Generates InceptionAuthorizationToken bound to HYP_005.
4. Seals canonical HypothesisSpecification to disk with deterministic SHA-256 digest.
5. Emits canonical R1 Registration Manifest for HYP_005.
6. Strictly maintains fail-closed boundaries: zero market data loading, $0.00 capital, backtest locked.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.reinception import (
    InceptionAuthorizationToken,
    InceptionDecision,
    ResearchInceptionProposal,
    ResearchReInceptionGate,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
    SplitPolicy,
)


def register_step_r1_hyp_005() -> InceptionAuthorizationToken:
    print("================================================================================")
    print("ACASH PHASE 14 STEP R1: HYPOTHESIS REGISTRATION & SEALING (HYP_005)")
    print("Mechanism Lineage: MEC-0015 SPY Noise-Area Intraday Momentum Net-Profitability Replication")
    print("Target Instrument: SPY (Consolidated SIP 1-Minute Bars, Quotes & Dividends)")
    print("Session Authority: NYSE Regular Trading Sessions (390 standard minutes only)")
    print("================================================================================")

    registered_at_utc = "2026-09-21T05:00:00Z"
    prereg_doc_path = Path("docs/research/MEC-0015-HYP-005-strategy-preregistration.md")
    if not prereg_doc_path.exists():
        raise DataContractError(f"CRITICAL: Frozen pre-registration document not found at '{prereg_doc_path}'.")

    prereg_bytes = prereg_doc_path.read_bytes()
    prereg_sha256 = hashlib.sha256(prereg_bytes).hexdigest()
    prereg_text = prereg_bytes.decode("utf-8")

    # Assert preregistration document integrity assertions
    if "PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_REGISTRATION" not in prereg_text:
        raise DataContractError("CRITICAL: Preregistration document status is not FINAL_PENDING_HYPOTHESIS_REGISTRATION.")
    if "OPEN_METHODOLOGICAL_BLOCKERS = 0" not in prereg_text:
        raise DataContractError("CRITICAL: Preregistration document does not report OPEN_METHODOLOGICAL_BLOCKERS = 0.")
    if "HYP_005 = NOT_CREATED" not in prereg_text:
        raise DataContractError("CRITICAL: Preregistration document does not assert HYP_005 = NOT_CREATED.")
    if "EMPIRICAL_EXECUTION = NOT_AUTHORIZED" not in prereg_text:
        raise DataContractError("CRITICAL: Preregistration document does not assert EMPIRICAL_EXECUTION = NOT_AUTHORIZED.")

    print(f"[Pre-Flight] Frozen Pre-Registration SHA-256: {prereg_sha256}")

    # Upstream MEC-0015 Authority Contract Hashes
    upstream_contract_hashes = {
        "intake_doc_sha256": hashlib.sha256(
            Path("docs/research/MEC-0015-profitability-first-intraday-momentum-intake.md").read_bytes()
        ).hexdigest(),
        "strategy_contract_audit_sha256": hashlib.sha256(
            Path("docs/research/MEC-0015-strategy-contract-audit.md").read_bytes()
        ).hexdigest(),
        "open_decisions_sha256": hashlib.sha256(
            Path("docs/research/MEC-0015-open-decisions.md").read_bytes()
        ).hexdigest(),
        "provider_qualification_contract_sha256": hashlib.sha256(
            Path("docs/research/MEC-0015-provider-qualification-contract.md").read_bytes()
        ).hexdigest(),
        "friction_contract_sha256": hashlib.sha256(
            Path("docs/research/MEC-0015-friction-contract.md").read_bytes()
        ).hexdigest(),
        "partition_acceptance_contract_sha256": hashlib.sha256(
            Path("docs/research/MEC-0015-partition-and-acceptance-contract.md").read_bytes()
        ).hexdigest(),
        "bar_provider_manifest_sha256": hashlib.sha256(
            Path("docs/research/manifests/MEC-0015-bar-provider-contract-manifest.json").read_bytes()
        ).hexdigest(),
        "dividend_provider_manifest_sha256": hashlib.sha256(
            Path("docs/research/manifests/MEC-0015-dividend-provider-contract-manifest.json").read_bytes()
        ).hexdigest(),
        "quote_provider_manifest_sha256": hashlib.sha256(
            Path("docs/research/manifests/MEC-0015-quote-provider-contract-manifest.json").read_bytes()
        ).hexdigest(),
        "sec31_schedule_manifest_sha256": hashlib.sha256(
            Path("docs/research/manifests/MEC-0015-sec31-fee-schedule.json").read_bytes()
        ).hexdigest(),
        "finra_taf_schedule_manifest_sha256": hashlib.sha256(
            Path("docs/research/manifests/MEC-0015-finra-taf-fee-schedule.json").read_bytes()
        ).hexdigest(),
    }

    # 1. Construct Proposal for HYP_005
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_005",
        candidate_hypothesis_version="v1.0",
        economic_rationale=(
            "Intraday noise-area breakouts in SPY confirm institutional momentum when price extends beyond "
            "the 14-session same-minute historical dispersion anchored by dividend-adjusted previous close "
            "and confirmed by cumulative regular-session VWAP, yielding positive net economic returns after friction."
        ),
        target_symbol="SPY",
        target_timeframe="1m",
        feature_dependencies=[
            "spy_sip_ohlcv_1m",
            "spy_historical_cash_dividends",
            "cumulative_rth_vwap_hlc3",
            "noise_area_14d_same_minute",
            "realized_volatility_15d_unadjusted",
        ],
        parameter_search_grid={
            "primary_specification": ["MEC_0015_NOISE_AREA_INTRADAY_MOMENTUM_BASELINE"],
        },
        planned_trial_count=1,  # Exactly K = 1 single primary preregistered specification
        target_horizons=[1],   # Non-binding schema compatibility stub
        primary_horizon=1,     # Non-binding schema compatibility stub
        expected_direction=ExpectedDirection.LONG,  # Non-binding schema stub (strategy trades long & short)
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.000001"),  # Non-binding schema compatibility stub
            min_hac_t_stat=Decimal("1.96"),             # Non-binding schema compatibility stub
            max_feature_autocorrelation=Decimal("0.999999"),  # Non-binding schema compatibility stub
            min_cost_adjusted_spread_ratio=Decimal("1.0"),    # Non-binding schema compatibility stub
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("0.0"),         # Non-binding schema stub; true friction bound in config
            roundtrip_broker_fee_bps=Decimal("0.0"),  # True friction bound in parameter_config
            fixed_slippage_bps=Decimal("0.0"),
        ),
        proposed_dataset_id="DS_SPY_MEC0015_SIP_REPLICATION_2007_2024",
        proposed_data_window=("2007-05-01T00:00:00+00:00", "2024-04-30T23:59:59+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),  # Transient non-binding schema compatibility metadata
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        ),
        author="human_operator_ratified",
        proposed_at_utc=registered_at_utc,
    )

    print("\n[Step 1] Submitting candidate proposal HYP_005 to ResearchReInceptionGate...")
    token = ResearchReInceptionGate.evaluate_reinception_proposal(proposal=proposal)
    print(f" -> Gate Decision: {token.decision.value}")
    print(f" -> Token ID: {token.token_id}")
    print(f" -> Authorized Hypothesis ID: {token.authorized_hypothesis_id}")
    print(f" -> Proposal SHA-256: {token.proposal_sha256}")
    print(f" -> Capital Authority: ${token.capital_authority_usd}")
    print(f" -> Strategy Qualified: {token.is_strategy_qualified}")
    print(f" -> Paper Authorized: {token.is_paper_authorized}")
    print(f" -> Live Authorized: {token.is_live_authorized}")

    if token.decision != InceptionDecision.INCEPTION_AUTHORIZED:
        raise DataContractError(f"Re-Inception Gate rejected proposal: {token.decision}")

    # Token zero-authority invariants
    if token.authorized_hypothesis_id != "HYP_005":
        raise DataContractError(f"Token hypothesis mismatch: {token.authorized_hypothesis_id}")
    if token.capital_authority_usd != Decimal("0.00"):
        raise DataContractError(f"Token capital authority must be $0.00, got: {token.capital_authority_usd}")
    if token.is_strategy_qualified is not False:
        raise DataContractError("Token must have is_strategy_qualified = False")
    if token.is_paper_authorized is not False:
        raise DataContractError("Token must have is_paper_authorized = False")
    if token.is_live_authorized is not False:
        raise DataContractError("Token must have is_live_authorized = False")

    # 2. Build Canonical HypothesisSpecification parameter config
    parameter_config = {
        "mechanism_id": "MEC-0015",
        "hypothesis_ordinal": 5,
        "hypothesis_title": "HYP_005 — SPY Noise-Area Intraday Momentum Net-Profitability Replication",
        "research_class": "STRATEGY_NATIVE_EXECUTABLE_ECONOMIC_HYPOTHESIS",
        "primary_research_objective": "NET_ECONOMIC_PERFORMANCE_AFTER_REALISTIC_FRICTION",
        "primary_specification": "MEC_0015_NOISE_AREA_INTRADAY_MOMENTUM_BASELINE",
        "planned_trial_count_k": 1,
        "strategy_specification": {
            "target_instrument": "SPY",
            "session_authority": "NYSE_REGULAR_TRADING_SESSIONS_390_MINUTES",
            "early_close_policy": "EXCLUDE_NON_STANDARD_REGULAR_SESSIONS",
            "noise_area_lookback_sessions": 14,
            "noise_area_warmup_policy": "REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS",
            "current_session_leakage": "PROHIBITED",
            "noise_multiplier": 1.0,
            "dividend_contract": {
                "provider": "ALPACA_CORPORATE_ACTIONS_SNAPSHOT",
                "point_in_time_vintage": "NOT_GUARANTEED_BY_PROVIDER",
                "gap_adjustment": "prev_close - current_day_cash_dividend",
                "missing_record_policy": "FAIL_CLOSED",
            },
            "vwap_contract": {
                "numerator": "HLC3",
                "session": "CUMULATIVE_RTH",
                "daily_reset": True,
                "provider_vw_field": "REJECTED",
            },
            "decision_epochs_et": [
                "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
                "13:00", "13:30", "14:00", "14:30", "15:00", "15:30"
            ],
            "decision_epoch_alpaca_bar_mapping": "LEFT_EDGE_ONE_MINUTE_PRIOR (e.g. 10:00 -> 09:59:00)",
            "signal_rules": {
                "long_entry": "Close > UpperBand AND Close > VWAP",
                "short_entry": "Close < LowerBand AND Close < VWAP",
                "exit_or_flip": "FLAT on neutral; flip on opposite signal",
                "entry_requires_vwap_confirmation": True,
            },
            "position_transition_rules": {
                "stop_evaluation_frequency": "30_MINUTE_DECISION_EPOCHS",
                "continuous_intraminute_stops": "PROHIBITED",
            },
            "execution_rules": {
                "boundary": "FIRST_VALID_SIP_NBBO_AT_OR_AFTER_DECISION_TIMESTAMP",
                "buy_fill": "NBBO_Ask + $0.001/share adverse slippage",
                "sell_fill": "NBBO_Bid - $0.001/share adverse slippage",
                "spread_model": "EMBEDDED_IN_NBBO",
                "explicit_half_spread_deduction_with_nbbo": "PROHIBITED",
                "same_bar_close_fills": "PROHIBITED",
            },
            "eod_contract": {
                "overnight_exposure": "STRICTLY_ZERO",
                "close_deadline": "16:00:00 America/New_York",
                "implementation": "FROZEN_MEC_0015_EOD_SEMANTICS",
            },
            "volatility_sizing": {
                "canonical_authority": "AUTHOR_MATLAB_IMPLEMENTATION",
                "return_series": "SIMPLE_CLOSE_TO_CLOSE_UNADJUSTED",
                "window_returns_count": 15,
                "ddof": 1,
                "shift": 1,
                "current_day_included": False,
                "target_volatility": 0.02,
                "max_leverage": 4.0,
                "sizing_denominator": "CURRENT_SESSION_OPEN",
                "aum_reference": "PRIOR_DAY_ENDING_AUM",
                "shares_rounding": "NEAREST_INTEGER",
            },
        },
        "friction_model": {
            "commission": "max($0.35, $0.0035 * shares)",
            "slippage": "$0.001/share adverse per executed side",
            "sec_section_31": {
                "side": "SELL_ONLY",
                "schedule_manifest": "MEC-0015-sec31-fee-schedule.json",
                "customer_pass_through": "ACASH_CONSERVATIVE_OPERATIONALIZATION",
                "rounding": "ROUND_CEILING_TO_CENT",
            },
            "finra_taf": {
                "side": "SELL_ONLY",
                "schedule_manifest": "MEC-0015-finra-taf-fee-schedule.json",
                "historical_tiers_count": 7,
            },
            "short_borrow": {
                "baseline_bps": 0,
                "historical_rate_classification": "UNOBSERVED",
            },
        },
        "two_x_friction_stress_contract": {
            "commission_multiplier": 2.0,
            "regulatory_fee_multiplier": 2.0,
            "additional_slippage_stress": "ONE_OBSERVED_HALF_SPREAD_PER_SIDE",
            "short_borrow_stress_annualized_bps": 50,
            "short_borrow_proration": "holding_minutes / (390 * 252)",
        },
        "partition_policy": {
            "m1_replication_sample": {
                "start_date": "2007-05-01",
                "end_date": "2024-04-30",
                "role": "PUBLICATION_EXPOSED_REPLICATION_SAMPLE",
                "purpose": "IMPLEMENTATION_AND_ECONOMIC_REPLICATION",
            },
            "m2_stress_sample": {
                "start_date": "2024-05-01",
                "end_date": "LAST_PUBLICLY_EXPOSED_REPLICATION_DATE",
                "role": "PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE",
                "access_state": "LOCKED_R4_ONLY",
            },
            "m3_holdout": {
                "role": "PROSPECTIVE_ONLY",
                "state": "SEALED_REVISE_ONLY_BY_SEPARATE_HUMAN_AUTHORIZATION",
            },
        },
        "primary_m1_acceptance_gates": {
            "logical_conjunction": "G1 AND G2 AND G3 AND G4 AND G5 AND G6 AND G7",
            "G1_net_total_return": "> 0",
            "G2_net_sharpe": ">= 1.00",
            "G3_max_drawdown": "<= 0.30",
            "G4_min_completed_trades": ">= 100",
            "G5_no_material_contract_failure": True,
            "G6_2x_stress_net_return": "> 0",
            "G7_2x_stress_net_sharpe": ">= 0.75",
        },
        "m2_continuation_gates": {
            "G1_net_total_return": "> 0",
            "G2_net_sharpe": ">= 0.50",
            "G3_max_drawdown": "<= 0.35",
            "G4_2x_stress_total_return": ">= 0",
            "G5_no_catastrophic_risk_failure": True,
        },
        "benchmark_contract": {
            "primary_benchmark": "SPY_BUY_AND_HOLD_TOTAL_RETURN",
            "relative_outperformance_substitutes_for_absolute_gates": False,
        },
        "upstream_authority_hashes": upstream_contract_hashes,
        "schema_compatibility_classification": {
            "binding": [
                "mechanism_id_MEC_0015",
                "single_specification_K_1",
                "primary_m1_economic_acceptance_gates",
                "two_x_friction_stress_contract",
                "alpaca_sip_1m_data_contract",
                "full_14_prior_sessions_noise_area",
                "author_matlab_vol_sizing_15d",
                "sec31_round_ceiling_operationalization",
                "finra_taf_7_tiers",
                "m1_partition_2007_2024",
                "m2_stress_locked",
                "m3_prospective_only",
            ],
            "non_binding_metadata": [
                "target_horizons=[1]",
                "primary_horizon=1",
                "min_in_sample_rank_ic=0.000001",
                "max_feature_autocorrelation=0.999999",
                "min_cost_adjusted_spread_ratio=1.0",
                "proposal_SplitPolicy",
                "zero_CostModelConfig",
                "expected_direction_LONG",
            ],
        },
        "governance_lineage": {
            "hypothesis_ordinal": 5,
            "hypothesis_id": "HYP_005",
            "preregistration_doc": "docs/research/MEC-0015-HYP-005-strategy-preregistration.md",
            "preregistration_sha256": prereg_sha256,
            "canonical_starting_commit": "4ec8e0fcaee73ea8cfbaf71f5d338ef813e1e33d",
            "human_authorization": "AUTHORIZE_HYP_005_INCEPTION_AND_R1_REGISTRATION",
            "inception_token_id": token.token_id,
            "proposal_sha256": token.proposal_sha256,
        },
    }
    parameter_config_json = CanonicalConfigSerializer.to_canonical_json(parameter_config)

    hyp_spec = HypothesisSpecification(
        hypothesis_id=proposal.candidate_hypothesis_id,
        hypothesis_version=proposal.candidate_hypothesis_version,
        parent_hypothesis_id=None,
        economic_rationale=proposal.economic_rationale,
        target_symbol=proposal.target_symbol,
        feature_dependencies=proposal.feature_dependencies,
        parameter_config_json=parameter_config_json,
        expected_direction=proposal.expected_direction,
        target_horizons=proposal.target_horizons,
        primary_horizon=proposal.primary_horizon,
        invalidation_criteria=proposal.invalidation_criteria,
        registered_at_utc=registered_at_utc,
        author=proposal.author,
    )

    # 3. Compute Canonical SHA-256
    hyp_sha256 = calculate_hypothesis_spec_sha256(hyp_spec)
    print(f"\n[Step 2] Computed Canonical Hypothesis SHA-256: {hyp_sha256}")

    # 4. Persist Sealed JSON in Canonical Tracked Locations and Local Runtime Mirror
    p85_hyp_dir = Path("docs/phase8.5/hypotheses")
    p85_hyp_dir.mkdir(parents=True, exist_ok=True)
    p85_hyp_file = p85_hyp_dir / f"{hyp_spec.hypothesis_id}.json"

    p14_hyp_dir = Path("docs/phase14/hypotheses")
    p14_hyp_dir.mkdir(parents=True, exist_ok=True)
    p14_hyp_file = p14_hyp_dir / f"{hyp_spec.hypothesis_id}.json"

    data_hyp_dir = Path("data/manifests/research/hypotheses")
    data_hyp_dir.mkdir(parents=True, exist_ok=True)
    data_hyp_file = data_hyp_dir / f"{hyp_spec.hypothesis_id}.json"

    spec_json_dict = hyp_spec.model_dump(mode="json")
    formatted_spec_json = json.dumps(spec_json_dict, indent=2)

    p85_hyp_file.write_text(formatted_spec_json, encoding="utf-8")
    p14_hyp_file.write_text(formatted_spec_json, encoding="utf-8")
    data_hyp_file.write_text(formatted_spec_json, encoding="utf-8")

    # Verify byte equality across canonical and local runtime mirrors
    b85 = p85_hyp_file.read_bytes()
    b14 = p14_hyp_file.read_bytes()
    bdata = data_hyp_file.read_bytes()
    if not (b85 == b14 == bdata):
        raise DataContractError("CRITICAL: Sealed hypothesis mirrors are not byte-identical.")

    print(f" -> Persisted Canonical Tracked Sealed Hypothesis to: {p85_hyp_file}")
    print(f" -> Persisted Canonical Tracked Sealed Hypothesis to: {p14_hyp_file}")
    print(f" -> Persisted Local Runtime Gitignored Mirror to: {data_hyp_file}")
    print(" -> Mirror byte equality verified across canonical and local mirrors.")

    # 5. Persist R1 Registration Manifest
    manifest_payload = {
        "manifest_type": "HYPOTHESIS_REGISTRATION_MANIFEST",
        "hypothesis_id": hyp_spec.hypothesis_id,
        "hypothesis_ordinal": 5,
        "hypothesis_ordinal_alias": "HYP_005",
        "mechanism_id": "MEC-0015",
        "canonical_title": "HYP_005 — SPY Noise-Area Intraday Momentum Net-Profitability Replication",
        "hypothesis_version": hyp_spec.hypothesis_version,
        "hypothesis_sha256": hyp_sha256,
        "registered_at_utc": registered_at_utc,
        "author": hyp_spec.author,
        "target_symbol": hyp_spec.target_symbol,
        "primary_timeframe": "1m",
        "search_trial_count_k": 1,
        "human_authorization": "AUTHORIZE_HYP_005_INCEPTION_AND_R1_REGISTRATION",
        "inception_token_id": token.token_id,
        "proposal_sha256": token.proposal_sha256,
        "preregistration_sha256": prereg_sha256,
        "upstream_authority_hashes": upstream_contract_hashes,
        "status": "SEALED_STEP_R1_PASS",
        "capital_authority_usd": "0.00",
        "no_real_orders": True,
        "market_data_access": "ZERO",
        "m1_data_access": "ZERO",
        "m2_data_access": "ZERO",
        "is_paper_authorized": False,
        "is_live_authorized": False,
        "next_required_step": "STEP_R2_MEC0015_DATASET_CONSTRUCTION_LOCKED_PENDING_SEPARATE_HUMAN_AUTHORIZATION",
    }
    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest_payload)
    manifest_digest = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    manifest_payload["manifest_sha256"] = manifest_digest
    formatted_manifest = json.dumps(manifest_payload, indent=2)

    p14_man_dir = Path("docs/phase14/manifests")
    p14_man_dir.mkdir(parents=True, exist_ok=True)
    p14_man_file = p14_man_dir / f"manifest_r1_{hyp_spec.hypothesis_id}.json"
    p14_man_file.write_text(formatted_manifest, encoding="utf-8")

    data_man_dir = Path("data/manifests/research")
    data_man_dir.mkdir(parents=True, exist_ok=True)
    data_man_file = data_man_dir / f"manifest_r1_{hyp_spec.hypothesis_id}.json"
    data_man_file.write_text(formatted_manifest, encoding="utf-8")

    # Verify byte equality across both manifest mirrors
    m14 = p14_man_file.read_bytes()
    mdata = data_man_file.read_bytes()
    if not (m14 == mdata):
        raise DataContractError("CRITICAL: R1 manifest mirrors are not byte-identical.")

    print(f" -> Persisted Canonical Tracked R1 Manifest to: {p14_man_file}")
    print(f" -> Persisted Local Runtime Gitignored Mirror to: {data_man_file}")
    print(f" -> Manifest SHA-256: {manifest_digest}")
    print(" -> Manifest mirror byte equality verified across canonical and local mirrors.")

    print("\n================================================================================")
    print("HYP_005 CANONICAL REGISTRATION COMPLETED & SEALED!")
    print(f"Canonical Hypothesis ID: {hyp_spec.hypothesis_id}")
    print(f"Canonical Hypothesis SHA-256: {hyp_sha256}")
    print(f"Canonical Manifest SHA-256: {manifest_digest}")
    print("Status: R1 PASS / SEALED (R2 LOCKED / CAPITAL $0.00 / M2 LOCKED / NO_REAL_ORDERS)")
    print("================================================================================")

    return token


if __name__ == "__main__":
    register_step_r1_hyp_005()
