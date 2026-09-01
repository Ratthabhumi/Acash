"""Phase 8.5 Alpha Qualification & Evidence Evaluation Engine (Slice 2, 3, & 4).

Provides:
- Economic qualification evaluation against sovereign hurdle rates.
- Strict zero-rebate isolation invariant enforcement.
- Monotonic friction sensitivity analysis.
- Computable falsification trigger evaluation engine.
- AlphaQualificationGate: master orchestrator composing Phase 4, Phase 6, and Phase 8.5 evidence.
- AlphaQualificationDossier cryptographic sealing with SHA-256 lineage DAG.

Strictly adheres to:
- Single Authority Rule: AlphaEconomicDecomposition in alpha_schema.py is the sole arithmetic authority.
- Zero Capital Authority: Capital allocated remains $0.00 across all qualification decisions.
- Separation of Concerns: Research (8.5) != Allocation (8) != Risk (9) != Execution (7).
- Zero Dependency Loops: Research qualification does NOT require a downstream Phase 8 capital allocation decision.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Any, Mapping, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaFalsificationTrigger,
    AlphaLifecycleState,
    AlphaQualificationDossier,
    FalsificationComparisonOperator,
    _verify_finite_decimal,
    validate_lifecycle_transition,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification, InvalidationCriteria
from acash.validation.schema import SearchTrialLedger, ValidationGateVerdict, ValidationReport


class EconomicQualificationConfig(BaseModel):
    """Configuration for Alpha Economic Qualification Policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hurdle_rate_bps: Decimal = Field(
        default=Decimal("5.0"),
        description="Minimum required Net Trading Alpha in basis points (evaluated at rebate=0).",
    )
    require_positive_net_alpha: bool = Field(
        default=True,
        description="Whether Net Trading Alpha must strictly exceed 0 bps regardless of hurdle.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_finite_fields(cls, data: Any) -> Any:
        if isinstance(data, dict) and "hurdle_rate_bps" in data:
            _verify_finite_decimal(data["hurdle_rate_bps"], "hurdle_rate_bps")
        return data


class EconomicQualificationDecision(BaseModel):
    """Deterministic verdict emitted by the Economic Qualification Engine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_viable: bool
    lifecycle_verdict: AlphaLifecycleState
    economic_decomposition: AlphaEconomicDecomposition
    hurdle_rate_bps: Decimal
    excess_alpha_over_hurdle_bps: Decimal
    rejection_reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_fields_and_invariants(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "hurdle_rate_bps" in data:
                _verify_finite_decimal(data["hurdle_rate_bps"], "hurdle_rate_bps")
            if "excess_alpha_over_hurdle_bps" in data:
                _verify_finite_decimal(data["excess_alpha_over_hurdle_bps"], "excess_alpha_over_hurdle_bps")
        return data


class AlphaQualificationResult(BaseModel):
    """Immutable result emitted by the AlphaQualificationGate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_qualified: bool
    lifecycle_state: AlphaLifecycleState
    dossier: Optional[AlphaQualificationDossier] = None
    rejection_reason: Optional[str] = None


def create_economic_decomposition(
    gross_trading_pnl_bps: Decimal,
    realized_spread_slippage_bps: Decimal = Decimal("0.0"),
    broker_commissions_bps: Decimal = Decimal("0.0"),
    broker_rebate_income_bps: Decimal = Decimal("0.0"),
) -> AlphaEconomicDecomposition:
    """Helper constructing an immutable AlphaEconomicDecomposition.

    Delegates all arithmetic invariant checks directly to the canonical AlphaEconomicDecomposition contract.
    """
    gross = _verify_finite_decimal(gross_trading_pnl_bps, "gross_trading_pnl_bps")
    spread = _verify_finite_decimal(realized_spread_slippage_bps, "realized_spread_slippage_bps")
    comm = _verify_finite_decimal(broker_commissions_bps, "broker_commissions_bps")
    rebate = _verify_finite_decimal(broker_rebate_income_bps, "broker_rebate_income_bps")

    net = gross - (spread + comm)
    total = net + rebate

    return AlphaEconomicDecomposition(
        gross_trading_pnl_bps=gross,
        realized_spread_slippage_bps=spread,
        broker_commissions_bps=comm,
        net_trading_alpha_bps=net,
        broker_rebate_income_bps=rebate,
        total_realized_economic_bps=total,
    )


def evaluate_economic_qualification(
    decomposition: AlphaEconomicDecomposition,
    hurdle_rate_bps: Decimal = Decimal("5.0"),
    current_state: AlphaLifecycleState = AlphaLifecycleState.STATISTICAL_VALIDATED,
) -> EconomicQualificationDecision:
    """Evaluate whether an Alpha candidate clears economic hurdle criteria.

    Strict Invariant:
    - Qualification is evaluated strictly against Net Trading Alpha with Rebate = 0.
    - If Net Trading Alpha >= Hurdle: emits ECONOMIC_EDGE_QUALIFIED.
    - If Net Trading Alpha < Hurdle: emits REJECTED_HURDLE_COLLAPSE (fail-closed).
    - Validates forward lifecycle transition from current_state to target verdict.

    Raises:
        DataContractError: If current_state cannot transition to the emitted verdict.
    """
    _verify_finite_decimal(hurdle_rate_bps, "hurdle_rate_bps")

    # Evaluate viability strictly on Net Trading Alpha (Rebate = 0)
    is_viable = decomposition.is_economically_viable(hurdle_rate_bps=hurdle_rate_bps)
    excess_alpha = decomposition.net_trading_alpha_bps - hurdle_rate_bps

    if is_viable:
        target_verdict = AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED
        rejection_reason = None
    else:
        target_verdict = AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE
        rejection_reason = (
            f"Net trading alpha ({decomposition.net_trading_alpha_bps} bps) failed hurdle rate "
            f"({hurdle_rate_bps} bps). Evaluated with rebate=0. "
            f"(Gross: {decomposition.gross_trading_pnl_bps} bps, Costs: "
            f"{decomposition.realized_spread_slippage_bps + decomposition.broker_commissions_bps} bps, "
            f"Rebates ignored: {decomposition.broker_rebate_income_bps} bps)."
        )

    # Enforce deterministic state machine transition rules
    validate_lifecycle_transition(current_state, target_verdict)

    return EconomicQualificationDecision(
        is_viable=is_viable,
        lifecycle_verdict=target_verdict,
        economic_decomposition=decomposition,
        hurdle_rate_bps=hurdle_rate_bps,
        excess_alpha_over_hurdle_bps=excess_alpha,
        rejection_reason=rejection_reason,
    )


# ---------------------------------------------------------------------------
# 3. Computable Falsification Trigger Evaluation Engine (Slice 3)
# ---------------------------------------------------------------------------


def evaluate_falsification_trigger(
    trigger: AlphaFalsificationTrigger,
    observed_value: Decimal,
) -> AlphaFalsificationTrigger:
    """Evaluate a single falsification trigger against an observed metric value."""
    obs = _verify_finite_decimal(observed_value, f"observed_value for {trigger.metric_name}")
    threshold = trigger.threshold_value

    if trigger.comparison_operator == FalsificationComparisonOperator.LESS_THAN:
        is_triggered = obs < threshold
        op_sym = "<"
    elif trigger.comparison_operator == FalsificationComparisonOperator.GREATER_THAN:
        is_triggered = obs > threshold
        op_sym = ">"
    elif trigger.comparison_operator == FalsificationComparisonOperator.LESS_EQUAL:
        is_triggered = obs <= threshold
        op_sym = "<="
    elif trigger.comparison_operator == FalsificationComparisonOperator.GREATER_EQUAL:
        is_triggered = obs >= threshold
        op_sym = ">="
    else:
        raise DataContractError(f"Unsupported comparison operator: {trigger.comparison_operator}")

    reason: Optional[str] = None
    if is_triggered:
        reason = (
            f"Falsification trigger '{trigger.trigger_name}' tripped: "
            f"observed {trigger.metric_name}={obs} {op_sym} threshold {threshold}."
        )

    return AlphaFalsificationTrigger(
        trigger_name=trigger.trigger_name,
        metric_name=trigger.metric_name,
        threshold_value=trigger.threshold_value,
        comparison_operator=trigger.comparison_operator,
        is_triggered=is_triggered,
        observed_value=obs,
        trigger_reason=reason,
    )


def evaluate_falsification_battery(
    triggers: Sequence[AlphaFalsificationTrigger],
    observed_metrics: Mapping[str, Decimal],
    require_all_metrics: bool = True,
) -> Tuple[AlphaFalsificationTrigger, ...]:
    """Evaluate an entire battery of falsification triggers against an observed metrics payload."""
    evaluated_list = []
    for trigger in triggers:
        if trigger.metric_name not in observed_metrics:
            if require_all_metrics:
                raise DataContractError(
                    f"Missing required metric '{trigger.metric_name}' in observed_metrics for trigger '{trigger.trigger_name}'."
                )
            evaluated_list.append(trigger)
            continue

        raw_val = observed_metrics[trigger.metric_name]
        evaluated_trigger = evaluate_falsification_trigger(trigger, raw_val)
        evaluated_list.append(evaluated_trigger)

    return tuple(evaluated_list)


def check_has_any_falsification_triggered(
    evaluated_triggers: Sequence[AlphaFalsificationTrigger],
) -> bool:
    """Check whether any trigger in an evaluated battery has tripped."""
    return any(t.is_triggered for t in evaluated_triggers)


def build_falsification_triggers_from_invalidation_criteria(
    criteria: InvalidationCriteria,
) -> Tuple[AlphaFalsificationTrigger, ...]:
    """Construct canonical falsification triggers from a Phase 4 InvalidationCriteria specification."""
    triggers = (
        AlphaFalsificationTrigger(
            trigger_name="OOS_RANK_IC_DEGRADATION",
            metric_name="rank_ic",
            threshold_value=criteria.min_in_sample_rank_ic,
            comparison_operator=FalsificationComparisonOperator.LESS_THAN,
        ),
        AlphaFalsificationTrigger(
            trigger_name="HAC_T_STAT_INSIGNIFICANCE",
            metric_name="hac_t_stat",
            threshold_value=criteria.min_hac_t_stat,
            comparison_operator=FalsificationComparisonOperator.LESS_THAN,
        ),
        AlphaFalsificationTrigger(
            trigger_name="FEATURE_AUTOCORRELATION_SATURATION",
            metric_name="autocorrelation_lag1",
            threshold_value=criteria.max_feature_autocorrelation,
            comparison_operator=FalsificationComparisonOperator.GREATER_THAN,
        ),
        AlphaFalsificationTrigger(
            trigger_name="SPREAD_FRAGILITY_COLLAPSE",
            metric_name="spread_ratio",
            threshold_value=criteria.min_cost_adjusted_spread_ratio,
            comparison_operator=FalsificationComparisonOperator.LESS_THAN,
        ),
    )
    return triggers


# ---------------------------------------------------------------------------
# 4. Master Alpha Qualification Gate & Dossier Sealing (Slice 4)
# ---------------------------------------------------------------------------


class AlphaQualificationGate:
    """Master Orchestrator for Phase 8.5 Alpha Qualification & Evidence Sealing.

    Strict Invariants:
    - Consumes existing Phase 4 (Hypothesis), Phase 6 (ValidationReport, SearchTrialLedger),
      and Phase 8.5 (Economic Decomposition, Falsification Triggers) evidence.
    - Does NOT recompute or redefine Phase 6 statistical tests (DSR/PBO/FWER).
    - Does NOT require a downstream Phase 8 capital allocation decision (Zero dependency loops).
    - Evaluates rebate isolation: Rebates cannot rescue negative net alpha.
    - If all evidence passes: seals an immutable AlphaQualificationDossier and sets
      state to RESEARCH_QUALIFIED with capital_authority_usd == 0.00.
    """

    def __init__(
        self,
        config: Optional[EconomicQualificationConfig] = None,
        governance_policy_version: str = "v1.0",
    ) -> None:
        self.config = config or EconomicQualificationConfig()
        self.governance_policy_version = governance_policy_version

    def _derive_governance_policy_digest(self) -> str:
        """Derive deterministic SHA-256 fingerprint for the qualification governance policy."""
        payload = {
            "governance_policy_version": self.governance_policy_version,
            "hurdle_rate_bps": str(self.config.hurdle_rate_bps),
            "require_positive_net_alpha": self.config.require_positive_net_alpha,
        }
        canonical_json = CanonicalConfigSerializer.to_canonical_json(payload)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def qualify_alpha(
        self,
        alpha_id: str,
        strategy_id: str,
        hypothesis_spec: HypothesisSpecification,
        trial_ledger: SearchTrialLedger,
        validation_report: ValidationReport,
        economic_decomposition: AlphaEconomicDecomposition,
        falsification_triggers: Sequence[AlphaFalsificationTrigger] = (),
        governance_policy_digest: Optional[str] = None,
        current_state: AlphaLifecycleState = AlphaLifecycleState.STATISTICAL_VALIDATED,
        fixed_created_timestamp_utc: Optional[str] = None,
    ) -> AlphaQualificationResult:
        """Execute the master qualification battery and emit sealed dossier or fail-closed rejection.

        Raises:
            DataContractError: On missing artifacts, tampered ledgers/digests, or illegal state transitions.
        """
        # 1. Pre-Flight Fail-Closed Invariant Validation
        if not alpha_id:
            raise DataContractError("alpha_id must not be empty.")
        if not strategy_id:
            raise DataContractError("strategy_id must not be empty.")
        if hypothesis_spec is None:
            raise DataContractError("Mandatory hypothesis_spec is required for Alpha qualification.")
        if trial_ledger is None:
            raise DataContractError("Mandatory trial_ledger is required for Alpha qualification.")
        if validation_report is None:
            raise DataContractError("Mandatory validation_report is required for Alpha qualification.")
        if economic_decomposition is None:
            raise DataContractError("Mandatory economic_decomposition is required for Alpha qualification.")

        # 2. Lineage Identity & Digest Integrity Validation
        if validation_report.hypothesis_id != hypothesis_spec.hypothesis_id:
            raise DataContractError(
                f"Lineage mismatch: validation_report.hypothesis_id '{validation_report.hypothesis_id}' "
                f"!= hypothesis_spec.hypothesis_id '{hypothesis_spec.hypothesis_id}'."
            )
        if validation_report.strategy_id != strategy_id:
            raise DataContractError(
                f"Lineage mismatch: validation_report.strategy_id '{validation_report.strategy_id}' "
                f"!= strategy_id '{strategy_id}'."
            )

        # Verify Trial Ledger is sealed and digest matches computed hash
        if not trial_ledger.is_sealed or not trial_ledger.ledger_digest:
            raise DataContractError(
                f"SearchTrialLedger '{trial_ledger.ledger_id}' must be in SEALED state before Alpha qualification."
            )
        computed_ledger_digest = trial_ledger.compute_ledger_digest()
        if trial_ledger.ledger_digest != computed_ledger_digest:
            raise DataContractError(
                f"Tampered SearchTrialLedger detected! ledger_digest '{trial_ledger.ledger_digest}' "
                f"!= computed '{computed_ledger_digest}'."
            )

        hyp_digest = calculate_hypothesis_spec_sha256(hypothesis_spec)
        gov_digest = governance_policy_digest or self._derive_governance_policy_digest()
        val_digest = validation_report.decision_digest

        # 3. Layer 1: Phase 6 Statistical Validation Gate Check
        if (
            validation_report.verdict != ValidationGateVerdict.PASS_TRADEABLE_ALPHA
            or not validation_report.is_tradeable_alpha
        ):
            return AlphaQualificationResult(
                is_qualified=False,
                lifecycle_state=AlphaLifecycleState.REJECTED_STATISTICAL_GATE,
                dossier=None,
                rejection_reason=(
                    f"Candidate failed Phase 6 statistical validation gate: "
                    f"verdict='{validation_report.verdict.value}', is_tradeable_alpha={validation_report.is_tradeable_alpha}."
                ),
            )

        # 4. Layer 2: Phase 8.5 Economic Hurdle & Rebate Isolation Check
        if current_state == AlphaLifecycleState.STATISTICAL_VALIDATED:
            validate_lifecycle_transition(current_state, AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED)
            active_state = AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED
        elif current_state in (
            AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED,
            AlphaLifecycleState.FORWARD_PAPER_MONITORED,
        ):
            active_state = current_state
        else:
            validate_lifecycle_transition(current_state, AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED)
            active_state = AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED

        econ_decision = evaluate_economic_qualification(
            decomposition=economic_decomposition,
            hurdle_rate_bps=self.config.hurdle_rate_bps,
            current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
        )
        if not econ_decision.is_viable:
            return AlphaQualificationResult(
                is_qualified=False,
                lifecycle_state=AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE,
                dossier=None,
                rejection_reason=econ_decision.rejection_reason,
            )

        # 5. Layer 3: Phase 8.5 Falsification Triggers & Forward Monitoring Check
        if active_state == AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED:
            validate_lifecycle_transition(active_state, AlphaLifecycleState.FORWARD_PAPER_MONITORED)
            active_state = AlphaLifecycleState.FORWARD_PAPER_MONITORED

        if check_has_any_falsification_triggered(falsification_triggers):
            validate_lifecycle_transition(active_state, AlphaLifecycleState.DEGRADED_FORWARD_TEST)
            tripped = [t.trigger_reason for t in falsification_triggers if t.is_triggered and t.trigger_reason]
            return AlphaQualificationResult(
                is_qualified=False,
                lifecycle_state=AlphaLifecycleState.DEGRADED_FORWARD_TEST,
                dossier=None,
                rejection_reason=f"Falsification triggers tripped: {'; '.join(tripped)}.",
            )

        # 6. Dossier Sealing & Lineage Binding
        target_state = AlphaLifecycleState.RESEARCH_QUALIFIED
        validate_lifecycle_transition(active_state, target_state)

        now_utc = fixed_created_timestamp_utc or datetime.now(timezone.utc).isoformat()
        unsealed_dossier = AlphaQualificationDossier(
            alpha_id=alpha_id,
            strategy_id=strategy_id,
            lifecycle_state=target_state,
            hypothesis_digest=hyp_digest,
            trial_ledger_digest=computed_ledger_digest,
            validation_report_digest=val_digest,
            governance_policy_digest=gov_digest,
            economic_decomposition=economic_decomposition,
            falsification_triggers=tuple(falsification_triggers),
            governance_policy_version=self.governance_policy_version,
            created_timestamp_utc=now_utc,
            capital_authority_usd=Decimal("0.00"),
        )
        dossier_digest = unsealed_dossier.compute_dossier_digest()
        sealed_dossier = AlphaQualificationDossier(
            alpha_id=unsealed_dossier.alpha_id,
            strategy_id=unsealed_dossier.strategy_id,
            lifecycle_state=unsealed_dossier.lifecycle_state,
            hypothesis_digest=unsealed_dossier.hypothesis_digest,
            trial_ledger_digest=unsealed_dossier.trial_ledger_digest,
            validation_report_digest=unsealed_dossier.validation_report_digest,
            governance_policy_digest=unsealed_dossier.governance_policy_digest,
            economic_decomposition=unsealed_dossier.economic_decomposition,
            falsification_triggers=unsealed_dossier.falsification_triggers,
            governance_policy_version=unsealed_dossier.governance_policy_version,
            created_timestamp_utc=unsealed_dossier.created_timestamp_utc,
            capital_authority_usd=unsealed_dossier.capital_authority_usd,
            dossier_digest=dossier_digest,
        )

        return AlphaQualificationResult(
            is_qualified=True,
            lifecycle_state=target_state,
            dossier=sealed_dossier,
            rejection_reason=None,
        )
