"""Multiple-Testing Corrections and Haircut Sharpe Engine (Phase 6).

Mathematical implementation based on:
- Holm, S. (1979). "A Simple Sequentially Rejective Multiple Test Procedure." Scandinavian Journal of Statistics, 6(2), 65–70.
- Benjamini, Y., & Hochberg, Y. (1995). "Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing." Journal of the Royal Statistical Society: Series B, 57(1), 289–300.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). "... and the Cross-Section of Expected Returns." Review of Financial Studies, 29(1), 5–68.

Strictly enforces:
- Authoritative K coupling: len(p_values) == effective_trials_k across all estimators.
- Holm-Bonferroni step-down procedure for strict Family-Wise Error Rate (FWER) control across K trials.
- Benjamini-Hochberg procedure for False Discovery Rate (FDR) q-values.
- Harvey-Liu-Zhu multiple-testing haircut Sharpe hurdle deduction.
"""

from decimal import Decimal
import math
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.validation.deflated_sharpe import _standard_normal_ppf
from acash.validation.schema import MultipleTestingResult, SharpeSpace




class MultipleTestingEngine:
    """Controls multiple testing inflation across exploratory search paths and trials.

    MATHEMATICAL PRIMITIVE NOTICE:
    This engine is a low-level mathematical calculator. Direct primitive invocation
    does NOT constitute a Gate 6 validation decision. Sovereign governance authority
    resides exclusively in StatisticalValidationGate.
    """


    @staticmethod
    def holm_bonferroni_correction(p_values: Sequence[Union[Decimal, float]]) -> List[Decimal]:
        """Apply Holm-Bonferroni step-down correction for Family-Wise Error Rate (FWER).

        Sorts p-values in ascending order: p_(1) <= p_(2) <= ... <= p_(K)
        Adjusted p-value: p_adj_(i) = min(1.0, max(p_adj_(i-1), (K - i + 1) * p_(i)))
        """
        K = len(p_values)
        if K == 0:
            return []

        raw_p: List[float] = []
        for idx, p in enumerate(p_values):
            pf = float(p)
            if not math.isfinite(pf) or pf < 0.0 or pf > 1.0:
                raise DataContractError(f"p-value at index {idx} must be finite and within [0.0, 1.0], got {p}")
            raw_p.append(pf)

        sorted_indices = np.argsort(raw_p)
        sorted_p = np.array(raw_p)[sorted_indices]

        adj_p_sorted = np.zeros(K, dtype=np.float64)
        running_max = 0.0

        for i in range(K):
            multiplier = K - i
            val = min(1.0, multiplier * sorted_p[i])
            running_max = max(running_max, val)
            adj_p_sorted[i] = running_max

        # Restore original input ordering
        adj_p_original = np.zeros(K, dtype=np.float64)
        adj_p_original[sorted_indices] = adj_p_sorted

        return [
            dec if (dec := to_decimal18(Decimal(f"{p_val:.12f}"))) is not None else Decimal("1.0")
            for p_val in adj_p_original
        ]

    @staticmethod
    def benjamini_hochberg_fdr(p_values: Sequence[Union[Decimal, float]]) -> List[Decimal]:
        """Apply Benjamini-Hochberg procedure for False Discovery Rate (FDR) q-values.

        q_(i) = min_{j >= i} ( (K / j) * p_(j) )
        """
        K = len(p_values)
        if K == 0:
            return []

        raw_p: List[float] = []
        for idx, p in enumerate(p_values):
            pf = float(p)
            if not math.isfinite(pf) or pf < 0.0 or pf > 1.0:
                raise DataContractError(f"p-value at index {idx} must be finite and within [0.0, 1.0], got {p}")
            raw_p.append(pf)

        sorted_indices = np.argsort(raw_p)
        sorted_p = np.array(raw_p)[sorted_indices]

        q_sorted = np.zeros(K, dtype=np.float64)
        running_min = 1.0

        for i in range(K - 1, -1, -1):
            rank = i + 1
            val = min(1.0, (K / rank) * sorted_p[i])
            running_min = min(running_min, val)
            q_sorted[i] = running_min

        # Restore original input ordering
        q_original = np.zeros(K, dtype=np.float64)
        q_original[sorted_indices] = q_sorted

        return [
            dec if (dec := to_decimal18(Decimal(f"{q_val:.12f}"))) is not None else Decimal("1.0")
            for q_val in q_original
        ]

    @staticmethod
    def calculate_bonferroni_haircut_sharpe(
        estimated_sharpe: float,
        effective_trials_k: int,
        sample_size_t: int,
        raw_p_value: Optional[float] = None,
        sharpe_space: SharpeSpace = SharpeSpace.ANNUAL,
        periods_per_year: float = 252.0,
    ) -> Decimal:
        """Calculate ACASH Bonferroni Haircut Sharpe Ratio in the requested SharpeSpace.

        Methodological Specification & Provenance:
        - Inspired by the multiple-testing threshold philosophy of Harvey, Liu, & Zhu (2016).
        - IMPORTANT METHODOLOGICAL DISTINCTION: This implementation uses a direct Bonferroni-adjusted
          two-sided normal tail probability inverse mapping:
            p_adj = min(1.0, K * p_raw) -> |t_adj| = Phi^-1(1 - p_adj / 2) -> Haircut_SR_period = |t_adj| / sqrt(T)
        - FREQUENCY-SPACE ALIGNMENT INVARIANT:
          Statistical t-test inference and p-value inversion are strictly evaluated in PERIOD return space:
            SR_period = estimated_sharpe / sqrt(periods_per_year)  (if sharpe_space == ANNUAL)
            t_raw = SR_period * sqrt(T)
            Haircut_SR_period = max(0.0, |t_adj| / sqrt(T))
            Haircut_SR_annual = Haircut_SR_period * sqrt(periods_per_year)
        """
        K = max(1, effective_trials_k)
        T = max(2, sample_size_t)
        sr = max(0.0, estimated_sharpe)

        if K <= 1 or sr <= 1e-12:
            dec = to_decimal18(Decimal(f"{sr:.12f}"))
            return dec if dec is not None else Decimal("0.0")

        # 1. Frequency Alignment: Convert to PERIOD space for mathematical statistical inference
        ann_factor = math.sqrt(periods_per_year) if periods_per_year > 0 else 1.0
        if sharpe_space == SharpeSpace.ANNUAL:
            sr_period = sr / ann_factor
        else:
            sr_period = sr

        t_raw = sr_period * math.sqrt(T)
        if t_raw <= 1e-12:
            return Decimal("0.0")

        # 2. Single-test two-sided p-value in period return space
        if raw_p_value is not None:
            pf = float(raw_p_value)
            if not math.isfinite(pf) or pf < 0.0 or pf > 1.0:
                raise DataContractError(f"raw_p_value must be finite and within [0.0, 1.0], got {raw_p_value}")
            p_raw = pf
        else:
            p_raw = math.erfc(t_raw / math.sqrt(2.0))

        # 3. Multiple-testing adjusted p-value across K declared search trials
        p_adj = min(1.0, p_raw * float(K))

        if p_adj >= 1.0 - 1e-15:
            return Decimal("0.0")

        if p_adj <= 1e-15:
            t_adj = t_raw
        else:
            # 4. Equivalent adjusted t-statistic: |t_adj| = Phi^-1(1 - p_adj / 2)
            prob = 1.0 - (p_adj / 2.0)
            prob = max(1e-15, min(1.0 - 1e-15, prob))
            t_adj = _standard_normal_ppf(prob)

        # 5. Non-linear Haircut Sharpe Ratio in PERIOD space
        haircut_sr_period = max(0.0, t_adj / math.sqrt(T))

        # 6. Scale to target return space
        if sharpe_space == SharpeSpace.ANNUAL:
            haircut_sr_reported = haircut_sr_period * ann_factor
        else:
            haircut_sr_reported = haircut_sr_period

        dec_out = to_decimal18(Decimal(f"{haircut_sr_reported:.12f}"))
        return dec_out if dec_out is not None else Decimal("0.0")

    # Backward-compatible alias
    calculate_haircut_sharpe = calculate_bonferroni_haircut_sharpe

    @classmethod
    def evaluate_multiple_testing(
        cls,
        p_values: Sequence[Union[Decimal, float]],
        estimated_sharpe: float,
        sample_size_t: int,
        effective_trials_k: Optional[int] = None,
        confidence_level_alpha: float = 0.05,
        primary_candidate_index: int = 0,
        sharpe_space: SharpeSpace = SharpeSpace.ANNUAL,
        periods_per_year: float = 252.0,
    ) -> MultipleTestingResult:
        """Evaluate full multiple testing battery across K trials targeting the pre-registered primary candidate.

        INPUT CONTRACT & STATISTICAL SPECIFICATION:
        - `p_values`: Sequence of unadjusted, raw two-sided asymptotic zero-Sharpe normal test p-values
          (H_0: SR_m = 0) recorded in the candidate SearchTrialLedger.
        - These are NOT Deflated Sharpe Ratio (DSR) probabilities (which account for higher moments and
          expected maximum Sharpe).
        - MultipleTestingEngine performs:
          1. Holm-Bonferroni step-down Family-Wise Error Rate (FWER) control targeting primary_candidate_index.
          2. Benjamini-Hochberg False Discovery Rate (FDR) q-value adjustments.
          3. Harvey-Liu-Zhu Bonferroni Haircut Sharpe penalization strictly evaluated in PERIOD inference space.
        """

        K = len(p_values)
        if effective_trials_k is not None and effective_trials_k != K:
            raise DataContractError(
                f"MultipleTestingEngine K mismatch: p_values vector contains {K} trials, but declared effective_trials_k={effective_trials_k}."
            )

        if K == 0:
            raise DataContractError("Cannot evaluate multiple testing on empty p_values collection.")

        if primary_candidate_index < 0 or primary_candidate_index >= K:
            raise DataContractError(
                f"primary_candidate_index {primary_candidate_index} out of range for ledger with {K} trials."
            )

        # 1. Holm-Bonferroni FWER step-down correction
        holm_adj = cls.holm_bonferroni_correction(p_values)

        # 2. Benjamini-Hochberg FDR q-values
        bh_q = cls.benjamini_hochberg_fdr(p_values)

        # 3. Non-linear ACASH Bonferroni Haircut Sharpe Ratio for the PRIMARY candidate
        # Strict pairing invariant: estimated_sharpe and raw_p_value are both from the primary candidate
        primary_p = float(p_values[primary_candidate_index])

        # Compute Haircut Sharpe in reported space (default ANNUAL)
        haircut_sr = cls.calculate_bonferroni_haircut_sharpe(
            estimated_sharpe=estimated_sharpe,
            effective_trials_k=K,
            sample_size_t=sample_size_t,
            raw_p_value=primary_p,
            sharpe_space=sharpe_space,
            periods_per_year=periods_per_year,
        )

        # Compute Haircut Sharpe strictly in PERIOD space
        haircut_sr_period = cls.calculate_bonferroni_haircut_sharpe(
            estimated_sharpe=estimated_sharpe,
            effective_trials_k=K,
            sample_size_t=sample_size_t,
            raw_p_value=primary_p,
            sharpe_space=SharpeSpace.PERIOD,
            periods_per_year=periods_per_year,
        )

        # Primary candidate FWER significance: check adjusted p-value of primary candidate against alpha hurdle
        primary_holm_p = float(holm_adj[primary_candidate_index])
        is_significant = primary_holm_p <= confidence_level_alpha
        raw_dec = [
            dec if (dec := to_decimal18(Decimal(f"{float(p):.12f}"))) is not None else Decimal("1.0")
            for p in p_values
        ]

        return MultipleTestingResult(
            effective_trials_k=K,
            raw_p_values=raw_dec,
            holm_bonferroni_p_values=holm_adj,
            benjamini_hochberg_q_values=bh_q,
            bonferroni_haircut_sharpe_ratio=haircut_sr,
            haircut_sharpe_ratio=haircut_sr,
            bonferroni_haircut_sharpe_ratio_period=haircut_sr_period,
            sharpe_space=sharpe_space,
            inference_space=SharpeSpace.PERIOD,
            is_fwer_significant=is_significant,
        )






