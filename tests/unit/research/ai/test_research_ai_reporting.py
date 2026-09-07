"""Phase 14 Slice 4 tests: Section 33 research report generator + evidence grounding.

Covers, in order of adversarial escalation (AGENTS.md Rule 14):
happy-path, boundary, malformed, contradictory, adversarial, permutation,
numerical-stability, golden-reference — plus governance firewall and
omitted-not-fabricated guarantees mandated by adjudications D-1..D-5.
"""

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import ast
from pathlib import Path
from typing import Optional, Tuple

import pytest
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaLifecycleState,
    AlphaQualificationDossier,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)
from acash.research.ai.reporting import (
    EvidenceGroundingVerifier,
    GroundingVerificationResult,
    OMITTED_MARKER,
    Section33Report,
    Section33ReportGenerator,
    validate_evidence_chain,
)
from acash.validation.schema import (
    DSRResult,
    MultipleTestingResult,
    OverfittingReport,
    SearchTrialLedger,
    SearchTrialRecord,
    SharpeSpace,
    ValidationGateVerdict,
    ValidationReport,
)

STRATEGY_ID = "STRREG_001"
HYPOTHESIS_ID = "HYP_TEST_0001"
ALPHA_ID = "ALPHA_0001"

DECISION_DIGEST = hashlib.sha256(b"slice4-validation-report-fixture-v1").hexdigest()
EVIDENCE_DIGEST = hashlib.sha256(b"slice4-evidence-fixture-v1").hexdigest()
GOVERNANCE_DIGEST = hashlib.sha256(b"slice4-governance-policy-v1").hexdigest()


@dataclass
class Bundle:
    """A fully sealed, cross-digest-consistent evidence bundle."""

    hypothesis: HypothesisSpecification
    ledger: SearchTrialLedger
    validation: ValidationReport
    dossier: AlphaQualificationDossier


def _make_dsr() -> DSRResult:
    return DSRResult(
        estimated_sharpe=Decimal("1.2"),
        benchmark_sharpe=Decimal("0.0"),
        expected_max_sharpe_sr0=Decimal("0.70"),
        sample_skewness=Decimal("-0.30"),
        sample_kurtosis=Decimal("3.10"),
        sample_size_t=2500,
        dsr_trials_k=45,
        trial_variance_used=Decimal("0.09"),
        dsr_statistic=Decimal("1.645"),
        dsr_probability=Decimal("0.95"),
        is_statistically_significant=True,
        has_sufficient_track_record=True,
    )


def _make_multiple_testing() -> MultipleTestingResult:
    return MultipleTestingResult(
        dsr_trials_k=45,
        raw_p_values=[Decimal("0.01")],
        holm_bonferroni_p_values=[Decimal("0.45")],
        benjamini_hochberg_q_values=[Decimal("0.10")],
        bonferroni_haircut_sharpe_ratio=Decimal("1.40"),
        is_fwer_significant=True,
    )


def _make_overfitting() -> OverfittingReport:
    return OverfittingReport(
        pbo_estimate=Decimal("0.05"),
        logits_distribution_mean=Decimal("-1.20"),
        logits_distribution_std=Decimal("0.30"),
        is_pbo_acceptable=True,
        parameter_fragility_max_curvature=Decimal("0.10"),
        is_parameter_stable=True,
        analytical_friction_monotonicity_passed=True,
    )


def _make_econ(
    gross: str = "-12.50",
    spread: str = "2.00",
    commissions: str = "1.00",
    net: str = "-15.50",
    rebate: str = "0.00",
    total: str = "-15.50",
) -> AlphaEconomicDecomposition:
    return AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal(gross),
        realized_spread_slippage_bps=Decimal(spread),
        broker_commissions_bps=Decimal(commissions),
        net_trading_alpha_bps=Decimal(net),
        broker_rebate_income_bps=Decimal(rebate),
        total_realized_economic_bps=Decimal(total),
    )


def _make_hypothesis() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id=HYPOTHESIS_ID,
        hypothesis_version="v1",
        parent_hypothesis_id=None,
        economic_rationale=(
            "Fragmented order flow predicts short-horizon directional continuation across liquid "
            "index constituents; the candidate edge is falsified if the HAC t-stat falls below the "
            "pre-registered threshold."
        ),
        target_symbol="EQX:INDEX_0099",
        feature_dependencies=["order_flow_imbalance"],
        parameter_config_json='{"window": 5, "direction": "long"}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[5],
        primary_horizon=5,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-01-01T00:00:00+00:00",
        author="QA_Auditor",
    )


def _make_trial() -> SearchTrialRecord:
    p_value = Decimal("0.01")
    p_value_method = "ASYMPTOTIC_TWO_SIDED_ZERO_SHARPE_NORMAL_TEST_V1"
    config_sha256 = SearchTrialRecord.compute_config_sha256(
        feature_names=("order_flow_imbalance",), parameters={"window": 5}
    )
    p_value_input_hash = SearchTrialRecord.compute_p_value_input_hash(
        return_series_sha256="b" * 64,
        config_sha256=config_sha256,
        p_value=p_value,
        p_value_method=p_value_method,
    )
    return SearchTrialRecord(
        trial_id="TRIAL_0001",
        strategy_id=STRATEGY_ID,
        hypothesis_id=HYPOTHESIS_ID,
        feature_names=("order_flow_imbalance",),
        parameters={"window": 5},
        in_sample_sharpe=Decimal("1.8"),
        p_value=p_value,
        p_value_method=p_value_method,
        p_value_input_hash=p_value_input_hash,
        config_sha256=config_sha256,
        in_sample_return_series_sha256="b" * 64,
        execution_manifest_id="BM_0001",
    )


def make_bundle(
    *,
    verdict: ValidationGateVerdict = ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
    stat_blocks: bool = True,
    in_sample_sharpe: Optional[Decimal] = Decimal("1.8"),
    out_of_sample_sharpe: Optional[Decimal] = Decimal("0.95"),
    oos_retention_pct: Optional[Decimal] = Decimal("50.0"),
    econ: Optional[AlphaEconomicDecomposition] = None,
) -> Bundle:
    hypothesis = _make_hypothesis()
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_0001",
        strategy_id=STRATEGY_ID,
        hypothesis_id=HYPOTHESIS_ID,
        trials=(_make_trial(),),
        sharpe_space=SharpeSpace.ANNUAL,
    ).seal(sealed_at_utc="2026-01-02T00:00:00+00:00")
    assert ledger.ledger_digest is not None

    validation = ValidationReport(
        validation_id=DECISION_DIGEST,
        evidence_digest=EVIDENCE_DIGEST,
        decision_digest=DECISION_DIGEST,
        strategy_id=STRATEGY_ID,
        hypothesis_id=HYPOTHESIS_ID,
        verdict=verdict,
        is_tradeable_alpha=(verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA),
        dsr_result=_make_dsr() if stat_blocks else None,
        multiple_testing_result=_make_multiple_testing() if stat_blocks else None,
        overfitting_report=_make_overfitting() if stat_blocks else None,
        in_sample_sharpe=in_sample_sharpe,
        out_of_sample_sharpe=out_of_sample_sharpe,
        oos_retention_pct=oos_retention_pct,
        created_timestamp_utc="2026-01-03T00:00:00+00:00",
    )

    dossier = AlphaQualificationDossier(
        alpha_id=ALPHA_ID,
        strategy_id=STRATEGY_ID,
        lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
        hypothesis_digest=calculate_hypothesis_spec_sha256(hypothesis),
        trial_ledger_digest=ledger.ledger_digest,
        validation_report_digest=DECISION_DIGEST,
        governance_policy_digest=GOVERNANCE_DIGEST,
        economic_decomposition=econ if econ is not None else _make_econ(),
        falsification_triggers=(),
        governance_policy_version="v1.0",
        created_timestamp_utc="2026-01-04T00:00:00+00:00",
        capital_authority_usd=Decimal("0.00"),
        dossier_digest="",
    )
    dossier = dossier.model_copy(update={"dossier_digest": dossier.compute_dossier_digest()})
    return Bundle(hypothesis=hypothesis, ledger=ledger, validation=validation, dossier=dossier)


@pytest.fixture()
def bundle() -> Bundle:
    return make_bundle()


@pytest.fixture()
def generator() -> Section33ReportGenerator:
    return Section33ReportGenerator()


@pytest.fixture()
def verifier() -> EvidenceGroundingVerifier:
    return EvidenceGroundingVerifier()


# ---------------------------------------------------------------------------
# 1. Happy path & structural completeness
# ---------------------------------------------------------------------------


def test_happy_path_full_section33_report_grounds(  # noqa: ANN201
    bundle: Bundle, generator: Section33ReportGenerator, verifier: EvidenceGroundingVerifier
) -> None:
    report = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    assert isinstance(report.report_sha256, str)
    expected_digest = hashlib.sha256(report.report_markdown.encode("utf-8")).hexdigest()
    assert report.report_sha256 == expected_digest

    for header in (
        "## 1. Executive Summary & Lifecycle Status",
        "## 2. Economic Rationale & Hypothesis Lineage",
        "## 3. Data Provenance & Timeframe Coordinates",
        "## 4. Empirical Performance Evidence",
        "## 5. Statistical Validation Breakdown",
        "## 6. Economic Decomposition",
        "## 7. Observed Facts vs Model Interpretations",
        "## 8. Methodological Boundaries & Disclaimers",
    ):
        assert header in report.report_markdown, header

    assert "{{" not in report.report_markdown and "}}" not in report.report_markdown
    assert "| In-Sample Sharpe | 1.8 |" in report.report_markdown
    assert "| Out-of-Sample Sharpe | 0.95 |" in report.report_markdown
    assert "| DSR Probability | 0.95 |" in report.report_markdown
    assert "| Gross Trading Alpha | -12.50 bps |" in report.report_markdown
    assert "| Total Realized Economic | -15.50 bps |" in report.report_markdown

    result = verifier.verify_report(
        report.report_markdown, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis
    )
    assert result.is_grounded
    assert result.report_sha256 == report.report_sha256
    assert report.hypothesis_digest == bundle.dossier.hypothesis_digest
    assert report.trial_ledger_digest == bundle.ledger.ledger_digest
    assert report.validation_report_decision_digest == bundle.validation.decision_digest
    assert report.dossier_digest == bundle.dossier.dossier_digest
    claim_labels = {c.claim_label for c in result.verified_claims}
    for expected_label in (
        "in-sample sharpe",
        "out-of-sample sharpe",
        "dsr probability",
        "dsr p-value",
        "estimated sharpe",
        "benchmark sharpe",
        "expected maximum sharpe (sr0)",
        "declared trials k",
        "sample size t",
        "pbo estimate",
        "parameter fragility max curvature",
        "bonferroni haircut sharpe",
        "gross trading alpha",
        "net trading alpha",
        "broker rebate income",
        "total realized economic",
        "declared trial count k",
    ):
        assert expected_label in claim_labels, expected_label


def test_validate_evidence_chain_accepts_sealed_bundle(bundle: Bundle) -> None:
    chain = validate_evidence_chain(bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert chain.is_valid
    assert chain.hypothesis_digest == bundle.dossier.hypothesis_digest
    assert chain.trial_ledger_digest == bundle.ledger.ledger_digest
    assert chain.validation_report_decision_digest == bundle.validation.decision_digest


def test_generated_report_omitted_metrics_marked_not_fabricated(bundle: Bundle, generator: Section33ReportGenerator) -> None:
    report = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    for metric in ("Sortino", "Max Drawdown", "Calmar", "Profit Factor", "Friction Sensitivity Matrix", "Zero-Rebate Hurdle Excess"):
        assert f"| {metric} | {OMITTED_MARKER} |" in report.report_markdown, metric


# ---------------------------------------------------------------------------
# 2. Boundary: tolerance handling
# ---------------------------------------------------------------------------


def test_claim_within_exact_tolerance_plus_0_01_passes(  # noqa: ANN201
    bundle: Bundle, verifier: EvidenceGroundingVerifier
) -> None:
    report = "| In-Sample Sharpe | 1.81 |"
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded


def test_claim_exceeding_tolerance_0_011_rejects(  # noqa: ANN201
    bundle: Bundle, verifier: EvidenceGroundingVerifier
) -> None:
    report = "| In-Sample Sharpe | 1.811 |"
    with pytest.raises(DataContractError, match="deviates"):
        verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_claim_precision_expansion_1_8000_passes(  # noqa: ANN201
    bundle: Bundle, verifier: EvidenceGroundingVerifier
) -> None:
    result = verifier.verify_report(
        "| In-Sample Sharpe | 1.8000 |", bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis
    )
    assert result.is_grounded


def test_custom_verifier_tolerance_0_05(bundle: Bundle) -> None:
    wide = EvidenceGroundingVerifier(tolerance=Decimal("0.05"))
    strict = EvidenceGroundingVerifier()
    report = "| PBO Estimate | 0.10 |"
    assert wide.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis).is_grounded
    with pytest.raises(DataContractError, match="deviates"):
        strict.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_invalid_verifier_tolerance_rejected() -> None:
    with pytest.raises(DataContractError, match="tolerance"):
        EvidenceGroundingVerifier(tolerance=Decimal("-0.01"))
    with pytest.raises(DataContractError, match="tolerance"):
        EvidenceGroundingVerifier(tolerance=Decimal("NaN"))


# ---------------------------------------------------------------------------
# 3. Malformed numeric tokens and malformed markdown
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malformed_report",
    [
        "| In-Sample Sharpe | 1.8.2 |",
        "| In-Sample Sharpe | 1..8 |",
        "| In-Sample Sharpe | 1.8,500 |",
    ],
)
def test_malformed_numeric_tokens_reject(malformed_report: str, bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    with pytest.raises(DataContractError, match="Malformed"):
        verifier.verify_report(malformed_report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_comma_grouped_number_rejects(  # noqa: ANN201
    bundle: Bundle, verifier: EvidenceGroundingVerifier
) -> None:
    # "-1,2" is not a canonical grouped decimal and never resolves to -12.50.
    report = "| Gross Trading Alpha | -1,2 bps |"
    with pytest.raises(DataContractError):
        verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_numeric_claim_inside_fenced_code_block_is_extracted(  # noqa: ANN201
    bundle: Bundle, verifier: EvidenceGroundingVerifier
) -> None:
    report = "```\nIn-Sample Sharpe\n1.8\n```"
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded
    assert any(c.claim_label == "in-sample sharpe" for c in result.verified_claims)


# ---------------------------------------------------------------------------
# 4. Contradictory / fabricated claims
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "claim_line, label_in_message",
    [
        ("| In-Sample Sharpe | 3.5 |", "in-sample sharpe"),
        ("| Out-of-Sample Sharpe | 0.50 |", "out-of-sample sharpe"),
        ("| DSR Probability | 0.90 |", "dsr probability"),
        ("| PBO Estimate | 0.50 |", "pbo estimate"),
        ("| Net Trading Alpha | -99.00 bps |", "net trading alpha"),
        ("| OOS Retention | 75.0 |", "oos retention"),
        ("| Declared Trial Count K | 2 |", "declared trial count k"),
    ],
)
def test_fabricated_claim_values_reject(  # noqa: ANN201
    claim_line: str, label_in_message: str, bundle: Bundle, verifier: EvidenceGroundingVerifier
) -> None:
    report = "# Report\n" + claim_line
    with pytest.raises(DataContractError) as excinfo:
        verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert label_in_message in str(excinfo.value)


@pytest.mark.parametrize(
    "claim_line, label_in_message",
    [
        ("| Max Drawdown | -5.0 % |", "max drawdown"),
        ("| Sortino | 0.65 |", "sortino"),
        ("| Calmar | 0.42 |", "calmar"),
        ("| Profit Factor | 1.29 |", "profit factor"),
        ("| PnL | 1500 |", "pnl"),
        ("| Sharpe | 1.8 |", "sharpe"),
        ("| Sharpe Ratio | 1.8 |", "sharpe ratio"),
    ],
)
def test_unregistered_claim_types_always_reject(  # noqa: ANN201
    claim_line: str, label_in_message: str, bundle: Bundle, verifier: EvidenceGroundingVerifier
) -> None:
    report = "# Report\n" + claim_line
    with pytest.raises(DataContractError) as excinfo:
        verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert label_in_message in str(excinfo.value)


# ---------------------------------------------------------------------------
# 5. Evidence chain / digest integrity (D-5)
# ---------------------------------------------------------------------------


def test_unsealed_ledger_fails_closed(bundle: Bundle, generator: Section33ReportGenerator) -> None:
    unsealed = SearchTrialLedger(
        ledger_id="LEDGER_0001",
        strategy_id=STRATEGY_ID,
        hypothesis_id=HYPOTHESIS_ID,
        trials=bundle.ledger.trials,
        sharpe_space=SharpeSpace.ANNUAL,
        is_sealed=False,
        ledger_digest=None,
    )
    with pytest.raises(DataContractError, match="SEALED"):
        generator.generate(bundle.hypothesis, unsealed, bundle.validation, bundle.dossier)
    with pytest.raises(DataContractError, match="SEALED"):
        validate_evidence_chain(bundle.dossier, bundle.validation, unsealed, bundle.hypothesis)


def test_ledger_dossier_digest_mismatch_rejects(bundle: Bundle) -> None:
    tampered = bundle.dossier.model_copy(update={"trial_ledger_digest": "e" * 64})
    with pytest.raises(DataContractError, match="Evidence chain mismatch"):
        validate_evidence_chain(tampered, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_validation_dossier_digest_mismatch_rejects(bundle: Bundle) -> None:
    tampered = bundle.dossier.model_copy(update={"validation_report_digest": "f" * 64})
    with pytest.raises(DataContractError, match="Evidence chain mismatch"):
        validate_evidence_chain(tampered, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_dossier_digest_tamper_rejects(bundle: Bundle) -> None:
    tampered = bundle.dossier.model_copy(update={"dossier_digest": "0" * 64})
    with pytest.raises(DataContractError, match="Tampered AlphaQualificationDossier"):
        validate_evidence_chain(tampered, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_ledger_content_tamper_rejected_at_dto_level() -> None:
    altered_trial = _make_trial().model_copy(update={"in_sample_sharpe": Decimal("9.9")})
    with pytest.raises(DataContractError, match="mismatch"):
        SearchTrialLedger(
            ledger_id="LEDGER_0001",
            strategy_id=STRATEGY_ID,
            hypothesis_id=HYPOTHESIS_ID,
            trials=(altered_trial,),
            sharpe_space=SharpeSpace.ANNUAL,
            is_sealed=True,
            sealed_at_utc="2026-01-02T00:00:00+00:00",
            ledger_digest="a" * 64,
        )


def test_hypothesis_id_mismatch_rejects(bundle: Bundle) -> None:
    other = bundle.hypothesis.model_copy(update={"hypothesis_id": "HYP_TEST_9999"})
    with pytest.raises(DataContractError, match="inconsistency"):
        validate_evidence_chain(bundle.dossier, bundle.validation, bundle.ledger, other)


def test_hypothesis_content_digest_mismatch_rejects(bundle: Bundle) -> None:
    other = bundle.hypothesis.model_copy(update={"economic_rationale": "A different sealed rationale."})
    with pytest.raises(DataContractError, match="Evidence chain mismatch"):
        validate_evidence_chain(bundle.dossier, bundle.validation, bundle.ledger, other)


def test_strategy_id_mismatch_rejects(bundle: Bundle) -> None:
    other = bundle.validation.model_copy(update={"strategy_id": "STRREG_OTHER"})
    with pytest.raises(DataContractError, match="inconsistency"):
        validate_evidence_chain(bundle.dossier, other, bundle.ledger, bundle.hypothesis)


# ---------------------------------------------------------------------------
# 6. Adversarial: prose, tables, inline code, duplicates, percentage, negatives
# ---------------------------------------------------------------------------


def test_prose_claim_grounded(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    report = "The DSR Probability: 0.95 per the sealed certificate."
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded
    assert any(c.claim_label == "dsr probability" for c in result.verified_claims)


def test_interleaved_prose_is_not_a_claim(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    report = "The DSR Probability is approximately 0.95 per the sealed certificate."
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded
    assert result.verified_claims == ()


def test_inline_code_claim_grounded(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    report = "Row: `In-Sample Sharpe: 1.8` passed to the verifier unchanged."
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded


def test_duplicate_claims_all_grounded(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    report = (
        "| In-Sample Sharpe | 1.8 |\n"
        "| In-Sample Sharpe | 1.8 |\n"
        "The in-sample sharpe figure is exactly 1.8; only adjacent tokens claim."
    )
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded
    assert sum(1 for c in result.verified_claims if c.claim_label == "in-sample sharpe") == 2


def test_percentage_unit_inadmissible_for_dsr_rejects(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    report = "| DSR Probability | 95% |"
    with pytest.raises(DataContractError, match="inadmissible"):
        verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_percentage_unit_admissible_for_validation_passes(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    report = "| OOS Retention | 50.0 % |"
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded


def test_comma_formatted_thousands_grounded() -> None:
    econ = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("-1250.00"),
        realized_spread_slippage_bps=Decimal("50.00"),
        broker_commissions_bps=Decimal("25.00"),
        net_trading_alpha_bps=Decimal("-1325.00"),
        broker_rebate_income_bps=Decimal("0.00"),
        total_realized_economic_bps=Decimal("-1325.00"),
    )
    b = make_bundle(econ=econ)
    verifier = EvidenceGroundingVerifier()
    report = "Sealed gross trading alpha -1,250.00 bps and total realized economic -1,325.00 bps."
    result = verifier.verify_report(report, b.dossier, b.validation, b.ledger, b.hypothesis)
    assert result.is_grounded
    assert any(c.parsed_value == Decimal("-1250.00") for c in result.verified_claims)
    assert any(c.parsed_value == Decimal("-1325.00") for c in result.verified_claims)


def test_negative_value_grounded_and_flipped_sign_rejects(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    grounded = verifier.verify_report(
        "| Net Trading Alpha | -15.50 bps |", bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis
    )
    assert grounded.is_grounded
    with pytest.raises(DataContractError, match="deviates"):
        verifier.verify_report(
            "| Net Trading Alpha | +15.50 bps |", bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis
        )


def test_zero_claims_report_is_trivially_grounded(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    report = "# Report\nThis document contains prose only: no figures are reported."
    result = verifier.verify_report(report, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert result.is_grounded
    assert result.verified_claims == ()


# ---------------------------------------------------------------------------
# 7. Permutation / determinism / golden reference
# ---------------------------------------------------------------------------


def test_row_permutation_is_claim_invariant(bundle: Bundle, verifier: EvidenceGroundingVerifier) -> None:
    baseline = "| DSR Probability | 0.95 |\n| Estimated Sharpe | 1.2 |\n| DSR Statistic | 1.645 |\n"
    permuted = "| DSR Statistic | 1.645 |\n| DSR Probability | 0.95 |\n| Estimated Sharpe | 1.2 |\n"
    r1 = verifier.verify_report(baseline, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    r2 = verifier.verify_report(permuted, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis)
    assert {c.parsed_value for c in r1.verified_claims} == {c.parsed_value for c in r2.verified_claims}


def test_golden_byte_exact_determinism(bundle: Bundle, generator: Section33ReportGenerator) -> None:
    r1 = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    r2 = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    assert r1.report_markdown == r2.report_markdown
    assert r1.report_sha256 == r2.report_sha256
    assert isinstance(r1, Section33Report)


# ---------------------------------------------------------------------------
# 8. Missing evidence → OMITTED, never fabricated (D-2)
# ---------------------------------------------------------------------------


def test_missing_stat_blocks_omitted_not_fabricated(generator: Section33ReportGenerator) -> None:
    b = make_bundle(
        verdict=ValidationGateVerdict.REJECT_HIGH_PBO,
        stat_blocks=False,
        out_of_sample_sharpe=None,
        oos_retention_pct=None,
    )
    report = generator.generate(b.hypothesis, b.ledger, b.validation, b.dossier)
    for metric in (
        "DSR Probability",
        "DSR p-value",
        "DSR Statistic",
        "Estimated Sharpe",
        "Benchmark Sharpe",
        "Expected Maximum Sharpe (SR0)",
        "Declared Trials K",
        "Sample Size T",
        "Sample Skewness",
        "Sample Kurtosis",
        "PBO Estimate",
        "Logits Distribution Mean",
        "Logits Distribution Std",
        "Parameter Fragility Max Curvature",
        "Bonferroni Haircut Sharpe",
    ):
        assert f"| {metric} | {OMITTED_MARKER} |" in report.report_markdown, metric
    assert "0.95" not in report.report_markdown

    verifier = EvidenceGroundingVerifier()
    result = verifier.verify_report(report.report_markdown, b.dossier, b.validation, b.ledger, b.hypothesis)
    assert result.is_grounded


def test_reject_verdict_report_is_grounded_and_truthful(generator: Section33ReportGenerator) -> None:
    b = make_bundle(verdict=ValidationGateVerdict.REJECT_MULTIPLE_TESTING_FWER, stat_blocks=False)
    report = generator.generate(b.hypothesis, b.ledger, b.validation, b.dossier)
    assert b.validation.verdict.value in report.report_markdown
    verifier = EvidenceGroundingVerifier()
    result = verifier.verify_report(report.report_markdown, b.dossier, b.validation, b.ledger, b.hypothesis)
    assert result.is_grounded


# ---------------------------------------------------------------------------
# 9. Immutability / lifecycle non-mutation
# ---------------------------------------------------------------------------


def test_evidence_object_frozen_prevents_mutation(bundle: Bundle) -> None:
    with pytest.raises(ValidationError):
        bundle.dossier.lifecycle_state = AlphaLifecycleState.HYPOTHESIS
    with pytest.raises(ValidationError):
        bundle.dossier.capital_authority_usd = Decimal("1.00")


def test_generation_does_not_mutate_lifecycle(bundle: Bundle, generator: Section33ReportGenerator) -> None:
    generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    assert bundle.dossier.lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED
    assert bundle.dossier.capital_authority_usd == Decimal("0.00")


# ---------------------------------------------------------------------------
# 10. Governance firewall / static scope audit
# ---------------------------------------------------------------------------


def _reporting_module_paths() -> Tuple[Path, ...]:
    from acash.research import ai as ai_pkg

    return tuple(Path(ai_pkg.__file__).parent.glob("reporting/**/*.py"))


def _assert_no_forbidden_imports(src_text: str) -> None:
    tree = ast.parse(src_text)
    banned_prefixed: Tuple[str, ...] = (
        "acash.execution",
        "acash.portfolio",
        "acash.runtime",
        "acash.backtest",
        "acash.risk",
        "acash.data",
        "MetaTrader5",
        "mt5",
        "httpx",
        "requests",
        "socket",
        "numpy",
        "pandas",
    )
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
    for mod in imported_modules:
        assert not any(mod == banned or mod.startswith(banned + ".") for banned in banned_prefixed), mod


def test_reporting_import_firewall_and_no_network() -> None:
    for path in _reporting_module_paths():
        src = path.read_text(encoding="utf-8")
        _assert_no_forbidden_imports(src)
        assert "HYP_003" not in src
        assert "import datetime" not in src and "from datetime" not in src


def test_reporting_sources_never_reference_hyp_003() -> None:
    from acash.research.ai.reporting import generator as _gen

    assert "HYP_003" not in Path(_gen.__file__).read_text(encoding="utf-8")