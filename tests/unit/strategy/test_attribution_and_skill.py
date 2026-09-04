"""Test Phase 17 Performance Attribution, Skill vs Luck, and Alternative Explanations."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.strategy.schema import (
    AlternativeExplanation,
    AlternativeExplanationRegister,
    EffectiveEvidenceSample,
    EvidenceSupportLevel,
    ExplanationStatus,
    FactorModelType,
    LuckSensitivity,
    ObservedOutcomeUncertainty,
    ParameterProvenance,
    PerformanceAttributionAssessment,
    PersistenceAssessment,
    SkillEvidence,
    SkillEvidenceStatus,
    WinnerSelectionRisk,
)


class TestAttributionAndSkill:
    """Verify performance attribution, skill evidence vectors, and alternative explanation invariants."""

    def test_invariant_12_profit_not_skill(self) -> None:
        """A strategy can have positive net return while skill evidence remains unproven."""
        attribution = PerformanceAttributionAssessment(
            gross_return=Decimal("0.45"),
            net_return=Decimal("0.35"),
            benchmark_return=Decimal("0.25"),
            market_beta_exposure=Decimal("1.20"),
            luck_sensitivity=LuckSensitivity.HIGH,
            outcome_uncertainty=ObservedOutcomeUncertainty.HIGH,
            persistence_assessment=PersistenceAssessment.FAILED,
            attribution_confidence=Decimal("0.20"),
            provenance=ParameterProvenance.RESEARCH_DERIVED,
        )
        # Even with +35% net return, luck sensitivity is HIGH and persistence is FAILED
        assert attribution.net_return > Decimal("0.0")
        assert attribution.luck_sensitivity == LuckSensitivity.HIGH
        assert attribution.persistence_assessment == PersistenceAssessment.FAILED

    def test_invariant_13_no_universal_factor_model(self) -> None:
        """FactorModelType distinguishes market-specific vs none without forcing a single model."""
        attr_fx = PerformanceAttributionAssessment(
            gross_return=Decimal("0.10"),
            net_return=Decimal("0.08"),
            factor_model_type=FactorModelType.MARKET_SPECIFIC,
            factor_model_id="FX_CARRY_MOMENTUM_3F",
            applicability_scope="G10_CURRENCY_PAIRS",
        )
        assert attr_fx.factor_model_type == FactorModelType.MARKET_SPECIFIC
        assert attr_fx.applicability_scope == "G10_CURRENCY_PAIRS"

        attr_crypto = PerformanceAttributionAssessment(
            gross_return=Decimal("0.50"),
            net_return=Decimal("0.40"),
            factor_model_type=FactorModelType.NONE,
            factor_model_id="NONE",
            applicability_scope="CRYPTO_SPOT",
        )
        assert attr_crypto.factor_model_type == FactorModelType.NONE

    def test_invariant_14_residual_not_alpha(self) -> None:
        """Unexplained residual component cannot be silently assumed to be proven alpha."""
        attribution = PerformanceAttributionAssessment(
            gross_return=Decimal("0.15"),
            net_return=Decimal("0.12"),
            market_beta_exposure=Decimal("0.0"),
            estimated_excess_return_component=Decimal("0.03"),
            residual_component=Decimal("0.09"),  # 9% residual is unexplained, NOT proven alpha
            luck_sensitivity=LuckSensitivity.MODERATE,
        )
        # Residual component is distinct from confirmed excess return component
        assert attribution.residual_component == Decimal("0.09")
        assert attribution.estimated_excess_return_component == Decimal("0.03")

    def test_invariant_15_effective_sample_estimator(self) -> None:
        """EffectiveEvidenceSample stores declared estimator methodology and assumptions."""
        eff_sample = EffectiveEvidenceSample(
            raw_observation_count=200,
            effective_sample_size=Decimal("45.5"),
            estimator_method="BLOCK_BOOTSTRAP_EPISODIC",
            dependency_model="SERIAL_CORRELATION_BLOCK_5",
            assumptions=("Intra-basket trades are dependent", "Regime switches reset correlation"),
            effective_sample_confidence=Decimal("0.85"),
            observed_regimes_count=3,
            provenance=ParameterProvenance.RESEARCH_DERIVED,
        )
        assert eff_sample.raw_observation_count == 200
        assert eff_sample.effective_sample_size == Decimal("45.5")
        assert eff_sample.estimator_method == "BLOCK_BOOTSTRAP_EPISODIC"

    def test_invariant_16_skill_evidence_vector_no_scalar_score(self) -> None:
        """SkillEvidence strictly forbids scalar composite scores (e.g. skill_score)."""
        # Injecting skill_score raises fail-closed DataContractError
        with pytest.raises(DataContractError, match="Scalar composite skill scores"):
            SkillEvidence.model_validate({"skill_score": 85})

        # Valid multi-dimensional vector with EvidenceSupportLevel
        vector = SkillEvidence(
            out_of_sample_support=EvidenceSupportLevel.SUPPORTED,
            walk_forward_support=EvidenceSupportLevel.SUPPORTED,
            regime_coverage_support=EvidenceSupportLevel.WEAK,
            execution_realism_support=EvidenceSupportLevel.SUPPORTED,
            robustness_support=EvidenceSupportLevel.INCONCLUSIVE,
            attribution_support=EvidenceSupportLevel.SUPPORTED,
            persistence_support=EvidenceSupportLevel.WEAK,
            sample_quality_support=EvidenceSupportLevel.SUPPORTED,
            unresolved_alternatives_count=1,
            statistical_confidence=Decimal("0.78"),
        )
        assert vector.out_of_sample_support == EvidenceSupportLevel.SUPPORTED
        assert vector.regime_coverage_support == EvidenceSupportLevel.WEAK
        assert vector.robustness_support == EvidenceSupportLevel.INCONCLUSIVE

    def test_invariant_17_alternative_explanation_register(self) -> None:
        """AlternativeExplanationRegister tracks counter-hypotheses with explicit status."""
        alt_beta = AlternativeExplanation(
            explanation_id="ALT-01",
            hypothesis="Broad equity market beta exposure",
            status=ExplanationStatus.SUPPORTED,
            supporting_evidence_summary="Beta to S&P500 is 1.15, explaining 85% of return variance",
            unresolved_risk="Strategy is essentially a leveraged beta proxy",
        )
        alt_regime = AlternativeExplanation(
            explanation_id="ALT-03",
            hypothesis="Abnormal low-volatility regime tailwind",
            status=ExplanationStatus.PLAUSIBLE,
            supporting_evidence_summary="Backtest executed exclusively during 2017 low vol regime",
            unresolved_risk="Strategy may fail under volatility expansion",
        )
        register = AlternativeExplanationRegister(
            strategy_id="STRAT_CANDIDATE_01",
            eval_timestamp_utc=datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc),
            explanations=(alt_beta, alt_regime),
            has_unresolved_critical_explanations=True,
        )
        assert register.has_unresolved_critical_explanations is True
        assert len(register.explanations) == 2
        assert register.explanations[0].status == ExplanationStatus.SUPPORTED

    def test_invariant_18_winner_selection_risk(self) -> None:
        """WinnerSelectionRisk enforces discount haircut on tournament champions."""
        winner_risk = WinnerSelectionRisk(
            tournament_size=50,
            parameter_search_count=1000,
            variant_count=20,
            data_snooping_risk_level="HIGH",
            haircut_discount_pct=Decimal("0.35"),
        )
        assert winner_risk.haircut_discount_pct == Decimal("0.35")
        assert winner_risk.data_snooping_risk_level == "HIGH"
