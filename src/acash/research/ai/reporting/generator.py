"""ACASH Section 33 Automated Research Report Generator (Phase 14, Slice 4).

Deterministic, offline, post-validation summarizer. Renders an audit-compliant
Section 33 research report strictly from sealed, verified ACASH evidence:
HypothesisSpecification, SearchTrialLedger, ValidationReport, and
AlphaQualificationDossier.

REPORTING PRINCIPLES (adjudicated D-2 / determinism contract):
- Every reported metric is lifted verbatim from a sealed evidence field.
- Nothing is recomputed, inferred, substituted, or fabricated.
- Section 33 metrics without a corresponding sealed entry are OMITTED and
  explicitly marked "NOT PRESENT IN SEALED EVIDENCE - OMITTED".
- Only omitted metrics are annotated; reported figures are never neutralized.

DETERMINISM:
- Identical sealed inputs produce byte-identical report output.
- Decimal text uses exponent-free canonical formatting; no randomness; no
  network; no timestamps appear in canonical report content.
"""

from decimal import Decimal
import hashlib
from importlib.resources import files
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError
from acash.research.alpha_schema import AlphaLifecycleState, AlphaQualificationDossier
from acash.research.schema import HypothesisSpecification
from acash.validation.schema import (
    DSRResult,
    MultipleTestingResult,
    OverfittingReport,
    SearchTrialLedger,
    ValidationGateVerdict,
    ValidationReport,
)
from acash.research.ai.reporting.citation_verifier import validate_evidence_chain

OMITTED_MARKER = "NOT PRESENT IN SEALED EVIDENCE - OMITTED"

_TEMPLATE_RESOURCE = ("templates", "section33_report.md")

_SECTION_TOKENS: Tuple[str, ...] = (
    "EXEC_SUMMARY",
    "RATIONALE_LINEAGE",
    "PROVENANCE",
    "PERFORMANCE",
    "STATISTICS",
    "ECONOMIC",
    "FACTS_VS_MODEL",
    "BOUNDARIES",
)


class Section33Report(BaseModel):
    """Deterministic Section 33 report artifact bound to the sealed evidence chain."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    alpha_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    report_markdown: str = Field(min_length=1)
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hypothesis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    trial_ledger_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_report_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    dossier_digest: str = Field(pattern=r"^([0-9a-f]{64})?$")


def _load_template() -> str:
    template_path = files("acash.research.ai.reporting").joinpath(*_TEMPLATE_RESOURCE)
    return template_path.read_text(encoding="utf-8")


def _fdecimal(value: Optional[Decimal]) -> str:
    if value is None:
        return OMITTED_MARKER
    if not value.is_finite():
        raise DataContractError(f"Non-finite Decimal encountered in report rendering: '{value}'.")
    return format(value, "f")


def _row(label: str, value_text: str) -> str:
    return f"| {label} | {value_text} |"


def _opt_row(label: str, value: Optional[Union[Decimal, int]]) -> str:
    if value is None:
        return _row(label, OMITTED_MARKER)
    if isinstance(value, Decimal):
        return _row(label, _fdecimal(value))
    return _row(label, str(value))


def _bool_or_omitted(value: Optional[bool]) -> str:
    if value is None:
        return OMITTED_MARKER
    return "True" if value else "False"


def _render_exec_summary(
    dossier: AlphaQualificationDossier, validation_report: ValidationReport
) -> str:
    lines: List[str] = [
        _row("Strategy ID", dossier.strategy_id),
        _row("Hypothesis ID", validation_report.hypothesis_id),
        _row("Alpha ID", dossier.alpha_id),
        _row("Lifecycle State", dossier.lifecycle_state.value),
        _row("Validation Gate Verdict", validation_report.verdict.value),
        _row("Tradeable Alpha Flag", str(validation_report.is_tradeable_alpha)),
    ]
    return "\n".join(["| Field | Value |", "| --- | --- |", *lines])


def _render_rationale_lineage(hypothesis: HypothesisSpecification) -> str:
    inv = hypothesis.invalidation_criteria
    lines: List[str] = [
        f"**Economic Rationale:** {hypothesis.economic_rationale}",
        f"**Registered Author:** {hypothesis.author}",
        f"**Hypothesis ID:** {hypothesis.hypothesis_id}",
        f"**Hypothesis Version:** {hypothesis.hypothesis_version}",
        f"**Parent Hypothesis ID:** {hypothesis.parent_hypothesis_id or 'None'}",
        f"**Target Symbol:** {hypothesis.target_symbol}",
        f"**Expected Direction:** {hypothesis.expected_direction.value}",
        f"**Primary Horizon (bars):** {hypothesis.primary_horizon}",
        f"**Target Horizons (bars):** {', '.join(str(h) for h in hypothesis.target_horizons)}",
        f"**Feature Dependencies:** {', '.join(hypothesis.feature_dependencies)}",
        "**Pre-Registered Invalidation Criteria:** "
        f"min_in_sample_rank_ic={_fdecimal(inv.min_in_sample_rank_ic)}, "
        f"min_hac_t_stat={_fdecimal(inv.min_hac_t_stat)}, "
        f"max_feature_autocorrelation={_fdecimal(inv.max_feature_autocorrelation)}, "
        f"min_cost_adjusted_spread_ratio={_fdecimal(inv.min_cost_adjusted_spread_ratio)}",
    ]
    return "\n".join(lines)


def _render_provenance(
    hypothesis: HypothesisSpecification,
    ledger: SearchTrialLedger,
    validation_report: ValidationReport,
) -> str:
    lines: List[str] = [
        _row("Target Symbol", hypothesis.target_symbol),
        _row("Feature Dependencies", ", ".join(hypothesis.feature_dependencies)),
        _row("Sharpe Space", ledger.sharpe_space.value),
        _row("Declared Trial Count K", str(len(ledger.trials))),
        _opt_row("OOS Retention", validation_report.oos_retention_pct),
        _row("Training Split Dates", OMITTED_MARKER),
        _row("Validation Split Dates", OMITTED_MARKER),
        _row("Held-Out OOS Split Dates", OMITTED_MARKER),
    ]
    return "\n".join(["| Metric | Value |", "| --- | --- |", *lines])


def _render_performance(validation_report: ValidationReport) -> str:
    lines: List[str] = [
        _opt_row("In-Sample Sharpe", validation_report.in_sample_sharpe),
        _opt_row("Out-of-Sample Sharpe", validation_report.out_of_sample_sharpe),
        _row("Sortino", OMITTED_MARKER),
        _row("Max Drawdown", OMITTED_MARKER),
        _row("Calmar", OMITTED_MARKER),
        _row("Profit Factor", OMITTED_MARKER),
        _row("Observed Return Series", OMITTED_MARKER),
    ]
    return "\n".join(["| Metric | Value |", "| --- | --- |", *lines])


def _render_statistics(validation_report: ValidationReport) -> str:
    dsr: Optional[DSRResult] = validation_report.dsr_result
    mt: Optional[MultipleTestingResult] = validation_report.multiple_testing_result
    oof: Optional[OverfittingReport] = validation_report.overfitting_report

    lines: List[str] = [
        _opt_row("DSR Probability", dsr.dsr_probability if dsr else None),
        _opt_row("DSR p-value", dsr.dsr_p_value if dsr else None),
        _opt_row("DSR Statistic", dsr.dsr_statistic if dsr else None),
        _opt_row("Estimated Sharpe", dsr.estimated_sharpe if dsr else None),
        _opt_row("Benchmark Sharpe", dsr.benchmark_sharpe if dsr else None),
        _opt_row("Expected Maximum Sharpe (SR0)", dsr.expected_max_sharpe_sr0 if dsr else None),
        _opt_row("Declared Trials K", dsr.declared_trials_k if dsr else None),
        _opt_row("Sample Size T", dsr.sample_size_t if dsr else None),
        _opt_row("Sample Skewness", dsr.sample_skewness if dsr else None),
        _opt_row("Sample Kurtosis", dsr.sample_kurtosis if dsr else None),
        _opt_row("PBO Estimate", oof.pbo_estimate if oof else None),
        _opt_row("Logits Distribution Mean", oof.logits_distribution_mean if oof else None),
        _opt_row("Logits Distribution Std", oof.logits_distribution_std if oof else None),
        _opt_row(
            "Parameter Fragility Max Curvature",
            oof.parameter_fragility_max_curvature if oof else None,
        ),
        _opt_row(
            "Bonferroni Haircut Sharpe",
            mt.bonferroni_haircut_sharpe_ratio if mt else None,
        ),
        _row("FWER Significant", _bool_or_omitted(mt.is_fwer_significant if mt else None)),
        _row("PBO Acceptable", _bool_or_omitted(oof.is_pbo_acceptable if oof else None)),
        _row(
            "Parameter Stable",
            _bool_or_omitted(oof.is_parameter_stable if oof else None),
        ),
        _row(
            "Friction Monotonicity Passed",
            _bool_or_omitted(oof.analytical_friction_monotonicity_passed if oof else None),
        ),
        _row("Friction Sensitivity Matrix", OMITTED_MARKER),
    ]
    return "\n".join(["| Metric | Value |", "| --- | --- |", *lines])


def _render_economic(dossier: AlphaQualificationDossier) -> str:
    econ = dossier.economic_decomposition
    lines: List[str] = [
        _row("Gross Trading Alpha", f"{_fdecimal(econ.gross_trading_pnl_bps)} bps"),
        _row(
            "Realized Spread + Slippage",
            f"{_fdecimal(econ.realized_spread_slippage_bps)} bps",
        ),
        _row("Broker Commissions", f"{_fdecimal(econ.broker_commissions_bps)} bps"),
        _row("Net Trading Alpha", f"{_fdecimal(econ.net_trading_alpha_bps)} bps"),
        _row("Broker Rebate Income", f"{_fdecimal(econ.broker_rebate_income_bps)} bps"),
        _row("Total Realized Economic", f"{_fdecimal(econ.total_realized_economic_bps)} bps"),
        _row("Zero-Rebate Hurdle Excess", OMITTED_MARKER),
    ]
    note = (
        "Economic decomposition arithmetic invariants (Net equals Gross minus Friction; Total equals "
        "Net plus Rebate) are enforced by the sealed AlphaEconomicDecomposition contract; this report "
        "reproduces sealed fields only and computes nothing."
    )
    return "\n".join(["| Metric | Value |", "| --- | --- |", *lines, "", note])


def _render_facts_vs_model(
    validation_report: ValidationReport,
    hypothesis: HypothesisSpecification,
) -> str:
    if validation_report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA:
        verdict_text = (
            "The sealed statistical validation gate returned a PASS_TRADEABLE_ALPHA verdict. This "
            "certifies evidence completeness under pre-registered governance thresholds only and is "
            "not a guarantee of future performance."
        )
    else:
        verdict_text = (
            "The sealed statistical validation gate returned verdict "
            f"{validation_report.verdict.value}. This report documents the sealed outcome without "
            "drawing any economic or trading inference."
        )
    facts = (
        "**Observed Empirical Facts (Deterministic):** Every numeric figure in this report is an exact "
        "value lifted from the sealed evidence artifacts. No metric is computed, inferred, or fabricated "
        "by this summarizer."
    )
    model = (
        f"**Model Interpretations & Lineage Commentary (NOT Empirical Evidence):** {verdict_text} "
        f"The registered economic rationale under review is: {hypothesis.economic_rationale}"
    )
    return "\n\n".join([facts, model])


def _render_boundaries() -> str:
    omitted = (
        "Sortino, Max Drawdown, Calmar, Profit Factor, Friction Sensitivity Matrix stress levels, "
        "Zero-Rebate Hurdle Excess, split-date coordinates, observed return series"
    )
    lines: List[str] = [
        "**Non-Guarantee Statement:** Observed Profit != Proven Edge. Historical or in-sample figures "
        "do not constitute a guarantee of future out-of-sample profitability, non-zero alpha, or "
        "time-series stationarity.",
        f"**Omitted Section 33 Metrics:** {omitted} were requested by Section 33 but have no "
        f"corresponding sealed entry in the canonical evidence inputs; they are OMITTED rather than "
        "fabricated, recomputed, inferred, or substituted. Omitted slack is never silently "
        "neutralized; the report remains truthful even when metrics are unavailable.",
        "**Epistemic Classification:** This report is a REPORTED summary artifact. It is NOT empirical "
        "evidence, NOT a validation certificate, NOT alpha qualification, NOT a strategy registration, "
        "and NOT a trading or capital authority. It conveys zero governance authority on any state "
        "machine. Capital authority remains zero.",
        "**Determinism Guarantee:** Identical sealed inputs reproduce byte-identical report output; "
        "the report contains no network access, no model inference, no randomness, and no timestamps.",
    ]
    return "\n\n".join(lines)


class Section33ReportGenerator:
    """Deterministic Section 33 report renderer bound to sealed evidence lineage."""

    def __init__(self) -> None:
        self._template = _load_template()

    def generate(
        self,
        hypothesis_spec: HypothesisSpecification,
        search_trial_ledger: SearchTrialLedger,
        validation_report: ValidationReport,
        alpha_qualification_dossier: AlphaQualificationDossier,
    ) -> Section33Report:
        """Render the report only from sealed, cross-linked evidence.

        Raises DataContractError fail-closed when the evidence chain is not
        sealed, internally consistent, or digest-linked. The raw markdown is
        returned in Section33Report.report_markdown; the authoritative numeric
        grounding check is performed by EvidenceGroundingVerifier.
        """
        chain = validate_evidence_chain(
            alpha_qualification_dossier=alpha_qualification_dossier,
            validation_report=validation_report,
            search_trial_ledger=search_trial_ledger,
            hypothesis_spec=hypothesis_spec,
        )

        sections = {
            "EXEC_SUMMARY": _render_exec_summary(alpha_qualification_dossier, validation_report),
            "RATIONALE_LINEAGE": _render_rationale_lineage(hypothesis_spec),
            "PROVENANCE": _render_provenance(hypothesis_spec, search_trial_ledger, validation_report),
            "PERFORMANCE": _render_performance(validation_report),
            "STATISTICS": _render_statistics(validation_report),
            "ECONOMIC": _render_economic(alpha_qualification_dossier),
            "FACTS_VS_MODEL": _render_facts_vs_model(validation_report, hypothesis_spec),
            "BOUNDARIES": _render_boundaries(),
        }

        report_markdown = self._template
        for token in _SECTION_TOKENS:
            placeholder = "{{%s}}" % token
            if placeholder not in report_markdown:
                raise DataContractError(f"Section 33 template is missing placeholder '{placeholder}'.")
            if sections[token].strip() == "":
                raise DataContractError(
                    f"Section 33 section '{token}' rendered empty; report would be incomplete."
                )
            report_markdown = report_markdown.replace(placeholder, sections[token])

        report_sha256 = hashlib.sha256(report_markdown.encode("utf-8")).hexdigest()
        return Section33Report(
            alpha_id=alpha_qualification_dossier.alpha_id,
            strategy_id=alpha_qualification_dossier.strategy_id,
            hypothesis_id=validation_report.hypothesis_id,
            report_markdown=report_markdown,
            report_sha256=report_sha256,
            hypothesis_digest=chain.hypothesis_digest,
            trial_ledger_digest=chain.trial_ledger_digest,
            validation_report_decision_digest=chain.validation_report_decision_digest,
            dossier_digest=chain.dossier_digest,
        )


if __name__ == "__main__":  # pragma: no cover
    raise DataContractError("generator module is not executable.")