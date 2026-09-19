"""Phase 14 Step R1 Registration & Sealing Script: HYP_004 (MEC-0014A Gao Baseline Replication).

Strictly enforces:
1. Submits human-ratified MEC-0014A statistical replication proposal to ResearchReInceptionGate.
2. Formally evaluates all 6 institutional invariants.
3. Generates InceptionAuthorizationToken bound to HYP_004.
4. Seals canonical HypothesisSpecification to disk with deterministic SHA-256 digest.
5. Emits canonical R1 Registration Manifest for HYP_004.
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


def register_step_r1_hyp_004() -> InceptionAuthorizationToken:
    print("================================================================================")
    print("ACASH PHASE 14 STEP R1: HYPOTHESIS REGISTRATION & SEALING (HYP_004)")
    print("Mechanism Lineage: MEC-0014A Market Intraday Momentum (Gao Baseline Replication)")
    print("Target Instrument: SPY (Consolidated SIP Trades & Closing Auction)")
    print("Session Authority: Accepted NyseCa1Calendar (CA-1)")
    print("================================================================================")

    registered_at_utc = "2026-09-19T05:00:00Z"
    prereg_doc_path = Path("docs/research/MEC-0014A-statistical-preregistration-draft.md")
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
    if "HYP_004 = NOT_CREATED" not in prereg_text:
        raise DataContractError("CRITICAL: Preregistration document does not assert HYP_004 = NOT_CREATED.")
    if "EMPIRICAL_EXECUTION = NOT_AUTHORIZED" not in prereg_text:
        raise DataContractError("CRITICAL: Preregistration document does not assert EMPIRICAL_EXECUTION = NOT_AUTHORIZED.")

    print(f"[Pre-Flight] Frozen Pre-Registration SHA-256: {prereg_sha256}")

    # 1. Construct Proposal for HYP_004
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_004",
        candidate_hypothesis_version="v1.0",
        economic_rationale=(
            "The first half-hour SPY return, including overnight information from the previous market close "
            "through 10:00 ET, may predict the final half-hour return because institutional portfolio rebalancing "
            "and late-day order-flow continuation can induce intraday return persistence near the market close."
        ),
        target_symbol="SPY",
        target_timeframe="1m",  # Non-binding provider/data-resolution metadata
        feature_dependencies=[
            "spy_previous_primary_close",
            "spy_transaction_price_1000_et",
            "spy_transaction_price_1530_et",
            "spy_primary_close",
            "r1_simple_return",
            "r13_simple_return",
        ],
        parameter_search_grid={
            "primary_specification": ["GAO_R1_TO_R13_BASELINE"],
        },
        planned_trial_count=1,  # Exactly K = 1 single primary preregistered specification
        target_horizons=[1],   # Non-binding schema compatibility stub
        primary_horizon=1,     # Non-binding schema compatibility stub
        expected_direction=ExpectedDirection.LONG,  # Meaning positive beta_r1 > 0; NOT a trading long
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.000001"),  # Non-binding schema compatibility stub
            min_hac_t_stat=Decimal("1.96"),             # Corresponds to asymptotic two-sided 5% level
            max_feature_autocorrelation=Decimal("0.999999"),  # Non-binding schema compatibility stub
            min_cost_adjusted_spread_ratio=Decimal("1.0"),    # Non-binding schema compatibility stub
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("0.0"),         # Non-binding schema compatibility metadata
            roundtrip_broker_fee_bps=Decimal("0.0"),  # Statistical replication only; no execution
            fixed_slippage_bps=Decimal("0.0"),        # Trading economics belong to MEC-0014B
        ),
        proposed_dataset_id="DS_SPY_MEC0014A_SIP_REPLICATION_2017_2022",
        proposed_data_window=("2017-01-01T00:00:00+00:00", "2022-12-31T23:59:59+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),  # Transient non-binding schema compatibility metadata
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        ),
        author="human_operator_ratified",
        proposed_at_utc=registered_at_utc,
    )

    print("\n[Step 1] Submitting candidate proposal HYP_004 to ResearchReInceptionGate...")
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
    if token.authorized_hypothesis_id != "HYP_004":
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
        "mechanism_id": "MEC-0014A",
        "hypothesis_ordinal": 4,
        "primary_specification": "GAO_R1_TO_R13_BASELINE",
        "planned_trial_count_k": 1,
        "statistical_specification": {
            "return_convention": "SIMPLE_RETURN",
            "predictor_r1": "p1000 / previous_primary_close - 1",
            "target_r13": "current_primary_close / p1530 - 1",
            "regression_equation": "r13 = alpha + beta * r1 + epsilon",
            "expected_slope": "beta > 0",
            "primary_acceptance_criterion": "beta > 0 AND two-sided Newey-West-HAC p-value < 0.05",
            "newey_west_lag_rule": "floor(4 * (T / 100)^(2/9))",
            "daily_trade_filter": "raw regular-session SIP trade count >= 500",
            "session_interval_predicate": "09:30:00 <= timestamp <= 16:00:00 America/New_York",
            "intraday_endpoint_authority": "QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY with distinct-price fail-closed rule",
            "market_close_authority": "unique NYSE Arca x=P, c=6 qualifying closing auction",
            "missing_endpoint_policy": "EXCLUDE_SESSION_FAIL_CLOSED",
            "corporate_action_baseline": "RAW_OBSERVED_TRANSACTION_PRICE_SEMANTICS (no dividend adjustment)",
        },
        "partition_policy": {
            "primary_replication_sample": {
                "start_date": "2017-01-01",
                "end_date": "2022-12-31",
                "label": "MEC_0014A_MECHANISM_SPECIFIC_REPLICATION_SAMPLE",
            },
            "internal_secondary_oos_diagnostic": {
                "initial_estimation": ["2017-01-01", "2019-12-31"],
                "forecast_evaluation": ["2020-01-01", "2022-12-31"],
                "re_estimation_frequency": "monthly_expanding",
                "role": "SECONDARY_PREREGISTERED_DIAGNOSTIC",
            },
            "external_holdout": {
                "start_date": "2023-01-01",
                "end_date": "2026-12-31",
                "state": "SEALED_UNREAD",
                "label": "MEC_0014_STRATEGY_UNEXPOSED_HOLDOUT / TECHNICALLY_PROBED_IN_ISOLATED_INFRASTRUCTURE_SESSIONS",
            },
        },
        "provider_caveats": {
            "taq_record_equivalence": "NOT_ESTABLISHED",
            "endpoint_mapping": "ACASH_QUALIFIED_PROVIDER_OPERATIONALIZATION",
            "session_interval_classification": "ACASH_PROVIDER_OPERATIONALIZATION_CHOICE",
        },
        "schema_compatibility_classification": {
            "binding": [
                "expected_direction_LONG_as_positive_beta",
                "preregistered_regression_r13_on_r1",
                "simple_return_semantics",
                "deterministic_newey_west_lag_rule",
                "two_sided_p_005_acceptance_criterion",
                "date_partition_2017_2022",
            ],
            "non_binding_metadata": [
                "target_horizons=[1]",
                "primary_horizon=1",
                "min_in_sample_rank_ic=0.000001",
                "max_feature_autocorrelation=0.999999",
                "min_cost_adjusted_spread_ratio=1.0",
                "proposal_SplitPolicy",
                "zero_CostModelConfig",
            ],
        },
        "governance_lineage": {
            "hypothesis_ordinal": 4,
            "hypothesis_id": "HYP_004",
            "preregistration_doc": "docs/research/MEC-0014A-statistical-preregistration-draft.md",
            "preregistration_sha256": prereg_sha256,
            "canonical_preregistration_commit": "ccd42a50be935cacb22b7681d5b806c449495057",
            "inception_token_id": token.token_id,
            "proposal_sha256": token.proposal_sha256,
            "source_git_sha": "ccd42a50be935cacb22b7681d5b806c449495057",
        },
        "calendar_authority": {
            "calendar_name": "NyseCa1Calendar",
            "code": "CA-1",
            "timezone": "America/New_York",
            "regular_session_minutes": 390,
        },
        "data_contract": {
            "symbol": "SPY",
            "feed": "sip",
            "adjustment": "raw",
            "data_window": ["2017-01-01", "2022-12-31"],
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

    # 4. Persist Sealed JSON in Canonical Locations
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

    # Verify byte equality across all three mirrors
    b85 = p85_hyp_file.read_bytes()
    b14 = p14_hyp_file.read_bytes()
    bdata = data_hyp_file.read_bytes()
    if not (b85 == b14 == bdata):
        raise DataContractError("CRITICAL: Sealed hypothesis mirrors are not byte-identical.")

    print(f" -> Persisted Sealed Hypothesis to: {p85_hyp_file}")
    print(f" -> Persisted Sealed Hypothesis to: {p14_hyp_file}")
    print(f" -> Persisted Sealed Hypothesis to: {data_hyp_file}")
    print(" -> Mirror byte equality verified across all 3 locations.")

    # 5. Persist R1 Registration Manifest
    manifest_payload = {
        "manifest_type": "HYPOTHESIS_REGISTRATION_MANIFEST",
        "hypothesis_id": hyp_spec.hypothesis_id,
        "hypothesis_ordinal": 4,
        "hypothesis_ordinal_alias": "HYP_004",
        "mechanism_id": "MEC-0014A",
        "hypothesis_version": hyp_spec.hypothesis_version,
        "hypothesis_sha256": hyp_sha256,
        "registered_at_utc": registered_at_utc,
        "author": hyp_spec.author,
        "target_symbol": hyp_spec.target_symbol,
        "primary_timeframe": "1m",
        "search_trial_count_k": 1,
        "inception_token_id": token.token_id,
        "proposal_sha256": token.proposal_sha256,
        "preregistration_sha256": prereg_sha256,
        "status": "SEALED_STEP_R1_PASS",
        "capital_authority_usd": "0.00",
        "next_required_step": "STEP_R2_MEC0014A_DATASET_CONSTRUCTION_LOCKED_PENDING_SEPARATE_HUMAN_AUTHORIZATION",
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

    print(f" -> Persisted R1 Manifest to: {p14_man_file}")
    print(f" -> Persisted R1 Manifest to: {data_man_file}")
    print(f" -> Manifest SHA-256: {manifest_digest}")
    print(" -> Manifest mirror byte equality verified across both locations.")

    print("\n================================================================================")
    print("HYP_004 CANONICAL REGISTRATION COMPLETED & SEALED!")
    print(f"Canonical Hypothesis ID: {hyp_spec.hypothesis_id}")
    print(f"Canonical Hypothesis SHA-256: {hyp_sha256}")
    print(f"Canonical Manifest SHA-256: {manifest_digest}")
    print("Status: R1 PASS / SEALED (R2 LOCKED / CAPITAL $0.00 / OOS SEALED)")
    print("================================================================================")

    return token


if __name__ == "__main__":
    register_step_r1_hyp_004()
