"""ACASH Evidence Grounding Verifier (Phase 14, Slice 4).

Single authority over every numeric claim emitted into a Section 33 research
report. Class name follows Master Research Architecture Plan Rev 1.2 Section 10:
the moniker "ZeroHallucinationVerifier" is replaced by EvidenceGroundingVerifier.

ENFORCEMENT CONTRACT (adjudicated D-1 / D-3 / D-5):
- Evidence set: ALPHA_QUALIFICATION_DOSSIER and VALIDATION_REPORT are both
  ingested deterministically. The SearchTrialLedger is additionally required so
  that the dossier's trial_ledger_digest cross-link can be verified.
- Cryptographic lineage: before any claim scan, the sealed evidence chain is
  cross-linked (D-5):
    1. SearchTrialLedger.compute_ledger_digest() == dossier.trial_ledger_digest
    2. ValidationReport.decision_digest == dossier.validation_report_digest
    3. Strategy/hypothesis identifiers are mutually consistent across artifacts.
    4. A provided HypothesisSpecification digest matches dossier.hypothesis_digest
       (computed via the canonical calculate_hypothesis_spec_sha256 authority).
    5. dossier.dossier_digest, when non-empty, matches compute_dossier_digest().
- Every failure is fail-closed: DataContractError is raised; the verifier never
  returns a "failed but tolerated" verdict and never silently corrects claims.

CLAIM-REGISTRY POLICY (adjudicated D-3):
- The union registry is the single authority: all claim types named by the
  canonical documents are recognized. Recognized claim types with no
  corresponding sealed field (Profit Factor, PnL, Drawdown, Sortino, Calmar,
  unqualified Sharpe, unqualified Sharpe Ratio, unqualified SR0) resolve to
  nothing and therefore REJECT any report that cites them numerically.
- A claim must match a declared numeric value within the canonical tolerance
  (+-0.01) and carry an admissible unit; any deviation raises DataContractError.
"""

from decimal import Decimal
import hashlib
import re
from typing import Dict, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError
from acash.research.alpha_schema import AlphaQualificationDossier
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification
from acash.validation.schema import SearchTrialLedger, ValidationReport

CANONICAL_CLAIM_TOLERANCE: Decimal = Decimal("0.01")

_STANDARD_UNIT = "plain"
_BPS_UNIT = "bps"
_PCT_UNIT = "pct"

# Multi-word phrases MUST precede their single-word alternatives so regex
# alternation resolves the most specific label deterministically.
_CLAIM_LABELS_ORDERED: Tuple[str, ...] = (
    "expected maximum sharpe (sr0)",
    "out-of-sample sharpe",
    "out of sample sharpe",
    "in-sample sharpe",
    "in sample sharpe",
    "bonferroni haircut sharpe",
    "parameter fragility max curvature",
    "logits distribution mean",
    "logits distribution std",
    "total realized economic",
    "broker rebate income",
    "realized spread + slippage",
    "realized spread slippage",
    "broker commissions",
    "gross trading alpha",
    "gross trading pnl",
    "net trading alpha",
    "oos retention",
    "dsr probability",
    "dsr p-value",
    "dsr p value",
    "dsr pvalue",
    "dsr statistic",
    "estimated sharpe",
    "benchmark sharpe",
    "declared trial count k",
    "declared trials k",
    "sample size t",
    "sample skewness",
    "sample kurtosis",
    "pbo estimate",
    "haircut sharpe",
    "profit factor",
    "sharpe ratio",
    "max drawdown",
    "oos sharpe",
    "parameter fragility",
    "sr0",
    "pbo",
    "drawdown",
    "sortino",
    "calmar",
    "pnl",
    "sharpe",
)

# Sealed field resolution: label -> (artifact group, field name).
# Any recognized label absent from this table is a claim type without a sealed
# field and therefore always rejects numerically (fail-closed).
_LABEL_RESOLVER: Mapping[str, Tuple[str, str]] = {
    "expected maximum sharpe (sr0)": ("dsr", "expected_max_sharpe_sr0"),
    "expected maximum sharpe": ("dsr", "expected_max_sharpe_sr0"),
    "sr0": ("dsr", "expected_max_sharpe_sr0"),
    "out-of-sample sharpe": ("validation", "out_of_sample_sharpe"),
    "out of sample sharpe": ("validation", "out_of_sample_sharpe"),
    "oos sharpe": ("validation", "out_of_sample_sharpe"),
    "in-sample sharpe": ("validation", "in_sample_sharpe"),
    "in sample sharpe": ("validation", "in_sample_sharpe"),
    "estimated sharpe": ("dsr", "estimated_sharpe"),
    "benchmark sharpe": ("dsr", "benchmark_sharpe"),
    "bonferroni haircut sharpe": ("multiple_testing", "bonferroni_haircut_sharpe_ratio"),
    "haircut sharpe": ("multiple_testing", "bonferroni_haircut_sharpe_ratio"),
    "parameter fragility max curvature": ("overfitting", "parameter_fragility_max_curvature"),
    "parameter fragility": ("overfitting", "parameter_fragility_max_curvature"),
    "logits distribution mean": ("overfitting", "logits_distribution_mean"),
    "logits distribution std": ("overfitting", "logits_distribution_std"),
    "total realized economic": ("economic", "total_realized_economic_bps"),
    "broker rebate income": ("economic", "broker_rebate_income_bps"),
    "realized spread + slippage": ("economic", "realized_spread_slippage_bps"),
    "realized spread slippage": ("economic", "realized_spread_slippage_bps"),
    "broker commissions": ("economic", "broker_commissions_bps"),
    "gross trading alpha": ("economic", "gross_trading_pnl_bps"),
    "gross trading pnl": ("economic", "gross_trading_pnl_bps"),
    "net trading alpha": ("economic", "net_trading_alpha_bps"),
    "oos retention": ("validation", "oos_retention_pct"),
    "dsr probability": ("dsr", "dsr_probability"),
    "dsr p-value": ("dsr", "dsr_p_value"),
    "dsr p value": ("dsr", "dsr_p_value"),
    "dsr pvalue": ("dsr", "dsr_p_value"),
    "dsr statistic": ("dsr", "dsr_statistic"),
    "declared trial count k": ("ledger", "trial_count"),
    "declared trials k": ("dsr", "declared_trials_k"),
    "sample size t": ("dsr", "sample_size_t"),
    "sample skewness": ("dsr", "sample_skewness"),
    "sample kurtosis": ("dsr", "sample_kurtosis"),
    "pbo estimate": ("overfitting", "pbo_estimate"),
    "pbo": ("overfitting", "pbo_estimate"),
}

# Unit cardinality per sealed field group. "plain" fields accept no unit token;
# "bps" and "pct" fields additionally accept their explicit unit tokens.
_UNIT_POLICY: Mapping[str, Tuple[str, ...]] = {
    "validation": (_STANDARD_UNIT, _PCT_UNIT),
    "dsr": (_STANDARD_UNIT,),
    "multiple_testing": (_STANDARD_UNIT,),
    "overfitting": (_STANDARD_UNIT,),
    "economic": (_STANDARD_UNIT, _BPS_UNIT),
    "ledger": (_STANDARD_UNIT,),
}

_CLAIM_RE = re.compile(
    r"\b(" + "|".join(re.escape(label) for label in _CLAIM_LABELS_ORDERED) + r")"
    r"(?P<sep>[^\w\d]*?)"
    r"(?P<num>[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"(?P<unit>(?:\s*bps|\s*pct|%))?",
    re.IGNORECASE,
)


class VerifiedClaim(BaseModel):
    """A single successfully grounded numeric claim in the report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_label: str = Field(min_length=1)
    raw_token: str = Field(min_length=1)
    parsed_value: Decimal
    resolved_field: str = Field(min_length=1)
    sealed_value: Decimal


class GroundingVerificationResult(BaseModel):
    """Successful verdict of the EvidenceGroundingVerifier.

    The verifier raises DataContractError before ever returning this object when
    any claim, unit, tolerance, or lineage condition is violated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_grounded: bool = True
    verified_claims: Tuple[VerifiedClaim, ...]
    tolerance: Decimal = CANONICAL_CLAIM_TOLERANCE
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hypothesis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    trial_ledger_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_report_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    dossier_digest: str = Field(pattern=r"^([0-9a-f]{64})?$")


class EvidenceChainStatus(BaseModel):
    """Normalized cryptographic lineage bindings of a validated evidence chain."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_valid: bool = True
    hypothesis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    trial_ledger_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_report_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    dossier_digest: str = Field(pattern=r"^([0-9a-f]{64})?$")


def _require_sealed_decimal(value: object, context: str) -> Decimal:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise DataContractError(f"Non-finite sealed Decimal '{context}': '{value}'.")
        return value
    if isinstance(value, int):
        return Decimal(str(value))
    raise DataContractError(f"Sealed field '{context}' is not a numeric value: {value!r}.")


def _extract_sealed(
    label_key: str,
    validation_report: ValidationReport,
    alpha_qualification_dossier: AlphaQualificationDossier,
    search_trial_ledger: SearchTrialLedger,
) -> Optional[Decimal]:
    group, field = _LABEL_RESOLVER[label_key]
    if group == "validation":
        raw = getattr(validation_report, field)
    elif group == "dsr":
        raw = getattr(validation_report.dsr_result, field) if validation_report.dsr_result is not None else None
    elif group == "multiple_testing":
        raw = (
            getattr(validation_report.multiple_testing_result, field)
            if validation_report.multiple_testing_result is not None
            else None
        )
    elif group == "overfitting":
        raw = (
            getattr(validation_report.overfitting_report, field)
            if validation_report.overfitting_report is not None
            else None
        )
    elif group == "ledger":
        raw = len(search_trial_ledger.trials) if search_trial_ledger is not None else None
    else:
        raw = getattr(alpha_qualification_dossier.economic_decomposition, field)
    if raw is None:
        return None
    return _require_sealed_decimal(raw, f"{group}.{field}")


def _normalize_number(raw_num: str) -> Decimal:
    token = raw_num.strip()
    if not token:
        raise DataContractError(f"Malformed numeric claim token: '{raw_num}'.")
    digits_only = token.replace("-", "").replace("+", "").replace(".", "").replace(",", "")
    if not digits_only.isdigit():
        raise DataContractError(f"Malformed numeric claim token: '{raw_num}'.")
    return Decimal(token.replace(",", ""))


def validate_evidence_chain(
    alpha_qualification_dossier: AlphaQualificationDossier,
    validation_report: ValidationReport,
    search_trial_ledger: SearchTrialLedger,
    hypothesis_spec: Optional[HypothesisSpecification] = None,
) -> EvidenceChainStatus:
    """Verify lineage integrity of the sealed evidence chain before any report use.

    Raises DataContractError on any cross-link or internal-consistency violation.
    """
    if not search_trial_ledger.is_sealed or not search_trial_ledger.ledger_digest:
        raise DataContractError(
            f"SearchTrialLedger '{search_trial_ledger.ledger_id}' must be SEALED with a ledger_digest "
            "before it can participate in a Section 33 research report."
        )

    computed_ledger_digest = search_trial_ledger.compute_ledger_digest()
    if computed_ledger_digest != search_trial_ledger.ledger_digest:
        raise DataContractError(
            f"Tampered SearchTrialLedger detected! ledger_digest '{search_trial_ledger.ledger_digest}' "
            f"!= recomputed '{computed_ledger_digest}'."
        )
    if computed_ledger_digest != alpha_qualification_dossier.trial_ledger_digest:
        raise DataContractError(
            "Evidence chain mismatch: dossier.trial_ledger_digest "
            f"'{alpha_qualification_dossier.trial_ledger_digest}' != ledger digest '{computed_ledger_digest}'. "
            "A report may not be generated or accepted from a mismatched evidence chain."
        )

    if alpha_qualification_dossier.validation_report_digest != validation_report.decision_digest:
        raise DataContractError(
            "Evidence chain mismatch: dossier.validation_report_digest "
            f"'{alpha_qualification_dossier.validation_report_digest}' != "
            f"ValidationReport.decision_digest '{validation_report.decision_digest}'."
        )

    if alpha_qualification_dossier.dossier_digest:
        computed_dossier_digest = alpha_qualification_dossier.compute_dossier_digest()
        if computed_dossier_digest != alpha_qualification_dossier.dossier_digest:
            raise DataContractError(
                "Tampered AlphaQualificationDossier detected! dossier_digest "
                f"'{alpha_qualification_dossier.dossier_digest}' != recomputed '{computed_dossier_digest}'."
            )

    if (
        alpha_qualification_dossier.strategy_id != validation_report.strategy_id
        or alpha_qualification_dossier.strategy_id != search_trial_ledger.strategy_id
    ):
        raise DataContractError(
            "Evidence chain inconsistency: strategy_id must be identical across dossier, "
            "ValidationReport, and SearchTrialLedger."
        )
    if search_trial_ledger.hypothesis_id != validation_report.hypothesis_id:
        raise DataContractError(
            "Evidence chain inconsistency: hypothesis_id must be identical across "
            "SearchTrialLedger and ValidationReport."
        )

    if hypothesis_spec is not None:
        if hypothesis_spec.hypothesis_id != validation_report.hypothesis_id:
            raise DataContractError(
                "Evidence chain inconsistency: HypothesisSpecification.hypothesis_id "
                f"'{hypothesis_spec.hypothesis_id}' != ValidationReport.hypothesis_id "
                f"'{validation_report.hypothesis_id}'."
            )
        computed_hyp_digest = calculate_hypothesis_spec_sha256(hypothesis_spec)
        if computed_hyp_digest != alpha_qualification_dossier.hypothesis_digest:
            raise DataContractError(
                "Evidence chain mismatch: dossier.hypothesis_digest "
                f"'{alpha_qualification_dossier.hypothesis_digest}' != "
                f"computed hypothesis digest '{computed_hyp_digest}'."
            )

    return EvidenceChainStatus(
        hypothesis_digest=alpha_qualification_dossier.hypothesis_digest,
        trial_ledger_digest=alpha_qualification_dossier.trial_ledger_digest,
        validation_report_decision_digest=alpha_qualification_dossier.validation_report_digest,
        dossier_digest=alpha_qualification_dossier.dossier_digest,
    )


class EvidenceGroundingVerifier:
    """Deterministic verifier that a Section 33 report only cites sealed evidence.

    Authored per Master Plan Rev 1.2 Section 10 (replacing the
    "ZeroHallucinationVerifier" moniker) and adjudication D-1, D-3, and D-5.
    """

    def __init__(self, tolerance: Decimal = CANONICAL_CLAIM_TOLERANCE) -> None:
        if not tolerance.is_finite() or tolerance < Decimal("0.0"):
            raise DataContractError(f"Verifier tolerance must be finite and >= 0, got '{tolerance}'.")
        self.tolerance = tolerance

    def verify_report(
        self,
        report_markdown: str,
        alpha_qualification_dossier: AlphaQualificationDossier,
        validation_report: ValidationReport,
        search_trial_ledger: SearchTrialLedger,
        hypothesis_spec: Optional[HypothesisSpecification] = None,
    ) -> GroundingVerificationResult:
        """Verify every numeric claim in report_markdown against sealed evidence.

        Raises DataContractError fail-closed on lineage violation, claim with no
        sealed counterpart, unit mismatch, tolerance breach, or malformed token.
        """
        validate_evidence_chain(
            alpha_qualification_dossier=alpha_qualification_dossier,
            validation_report=validation_report,
            search_trial_ledger=search_trial_ledger,
            hypothesis_spec=hypothesis_spec,
        )

        lowered = report_markdown.lower()
        verified: list[VerifiedClaim] = []
        for match in _CLAIM_RE.finditer(lowered):
            label_key = match.group(1).strip()
            raw_num = match.group("num")
            unit_token = (match.group("unit") or "").strip()

            if label_key not in _LABEL_RESOLVER:
                raise DataContractError(
                    "Evidence grounding rejection: metric '{0}' is cited without a corresponding "
                    "sealed evidence entry in ValidationReport or AlphaQualificationDossier.".format(label_key)
                )

            remainder = lowered[match.end():]
            if (
                remainder[:1] in (",", ".")
                and len(remainder) >= 2
                and (remainder[1].isdigit() or remainder[1] in (",", "."))
            ):
                raise DataContractError(
                    "Malformed numeric claim token: '{0}' is not a canonical decimal.".format(raw_num)
                )

            claim_value = _normalize_number(raw_num)
            sealed_value = _extract_sealed(
                label_key,
                validation_report=validation_report,
                alpha_qualification_dossier=alpha_qualification_dossier,
                search_trial_ledger=search_trial_ledger,
            )
            if sealed_value is None:
                raise DataContractError(
                    "Evidence grounding rejection: metric '{0}' is cited numerically but the sealed "
                    "ValidationReport does not contain a corresponding entry (validated fail-closed).".format(label_key)
                )

            field_group, _ = _LABEL_RESOLVER[label_key]
            unit_key = _STANDARD_UNIT if not unit_token else unit_token
            if unit_key == "%":
                unit_key = _PCT_UNIT
            allowed_units = set(_UNIT_POLICY[field_group])
            if unit_key not in allowed_units:
                raise DataContractError(
                    "Evidence grounding rejection: claim '{0}' unit '{1}' is inadmissible for sealed "
                    "field group '{2}'.".format(label_key, unit_token or "<none>", field_group)
                )

            if abs(claim_value - sealed_value) > self.tolerance:
                raise DataContractError(
                    "Evidence grounding rejection: claim '{0}' value {1}{2} deviates from sealed value "
                    "{3} beyond tolerance {4}.".format(
                        label_key,
                        _format_decimal(claim_value),
                        (" " + unit_token) if unit_token else "",
                        _format_decimal(sealed_value),
                        self.tolerance,
                    )
                )

            verified.append(
                VerifiedClaim(
                    claim_label=label_key,
                    raw_token=raw_num,
                    parsed_value=claim_value,
                    resolved_field="{0}.{1}".format(*_LABEL_RESOLVER[label_key]),
                    sealed_value=sealed_value,
                )
            )

        report_digest = hashlib.sha256(report_markdown.encode("utf-8")).hexdigest()
        return GroundingVerificationResult(
            is_grounded=True,
            verified_claims=tuple(verified),
            tolerance=self.tolerance,
            report_sha256=report_digest,
            hypothesis_digest=alpha_qualification_dossier.hypothesis_digest,
            trial_ledger_digest=alpha_qualification_dossier.trial_ledger_digest,
            validation_report_decision_digest=alpha_qualification_dossier.validation_report_digest,
            dossier_digest=alpha_qualification_dossier.dossier_digest,
        )


def _format_decimal(value: Decimal) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


if __name__ == "__main__":  # pragma: no cover
    raise DataContractError("citation_verifier module is not executable.")