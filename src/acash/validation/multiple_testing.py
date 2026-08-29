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
from acash.validation.schema import MultipleTestingResult



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

        raw_p = [float(p) for p in p_values]
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

        return [to_decimal18(Decimal(f"{p_val:.12f}")) or Decimal("1.0") for p_val in adj_p_original]

    @staticmethod
    def benjamini_hochberg_fdr(p_values: Sequence[Union[Decimal, float]]) -> List[Decimal]:
        """Apply Benjamini-Hochberg procedure for False Discovery Rate (FDR) q-values.

        q_(i) = min_{j >= i} ( (K / j) * p_(j) )
        """
        K = len(p_values)
        if K == 0:
            return []

        raw_p = [float(p) for p in p_values]
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

        return [to_decimal18(Decimal(f"{q_val:.12f}")) or Decimal("1.0") for q_val in q_original]

    @staticmethod
    def calculate_haircut_sharpe(
        estimated_sharpe: float,
        effective_trials_k: int,
        sample_size_t: int,
        raw_p_value: Optional[float] = None,
    ) -> Decimal:
        """Calculate Haircut Sharpe Ratio adjusting for K trials and sample length T (Harvey, Liu, & Zhu 2016).

        Reference:
        Harvey, C. R., Liu, Y., & Zhu, H. (2016). "... and the Cross-Section of Expected Returns."
        Review of Financial Studies, 29(1), 5–68.

        Canonical Methodology:
        1. Compute raw t-statistic from estimated Sharpe ratio and sample length T:
           t_raw = estimated_sharpe * sqrt(T)
        2. Compute two-sided single-test unadjusted p-value:
           p_raw = 2 * (1 - Phi(|t_raw|)) = erfc(|t_raw| / sqrt(2)) (or use provided raw_p_value)
        3. Compute multiple-testing adjusted p-value across K trials:
           p_adj = min(1.0, p_raw * K)
        4. Derive adjusted t-statistic corresponding to p_adj:
           |t_adj| = Phi^-1(1 - p_adj / 2) if p_adj < 1.0 else 0.0
        5. Calculate non-linear Haircut Sharpe Ratio:
           Haircut_SR = max(0.0, estimated_sharpe * (t_adj / max(1e-6, abs(t_raw))))
           (which equals max(0.0, t_adj / sqrt(T)))
        """
        K = max(1, effective_trials_k)
        T = max(2, sample_size_t)
        sr = max(0.0, estimated_sharpe)

        if K <= 1 or sr <= 1e-12:
            return to_decimal18(Decimal(f"{sr:.12f}")) or Decimal("0.0")

        t_raw = sr * math.sqrt(T)
        if t_raw <= 1e-12:
            return Decimal("0.0")

        # 2. Single-test two-sided p-value
        if raw_p_value is not None:
            p_raw = float(raw_p_value)
        else:
            p_raw = math.erfc(t_raw / math.sqrt(2.0))

        # 3. Multiple-testing adjusted p-value
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

        # 5. Non-linear Haircut Sharpe Ratio
        haircut_sr = max(0.0, t_adj / math.sqrt(T))

        return to_decimal18(Decimal(f"{haircut_sr:.12f}")) or Decimal("0.0")

    @classmethod
    def evaluate_multiple_testing(
        cls,
        p_values: Sequence[Union[Decimal, float]],
        estimated_sharpe: float,
        sample_size_t: int,
        effective_trials_k: Optional[int] = None,
        confidence_level_alpha: float = 0.05,
    ) -> MultipleTestingResult:
        """Evaluate full multiple testing battery across K trials with authoritative K verification."""
        k_count = len(p_values)
        if effective_trials_k is not None and k_count != effective_trials_k:
            raise DataContractError(
                f"MultipleTestingEngine K mismatch: len(p_values)={k_count} != authoritative effective_trials_k={effective_trials_k}"
            )
        authoritative_k = effective_trials_k or k_count

        raw_dec = [to_decimal18(Decimal(f"{float(p):.12f}")) or Decimal("1.0") for p in p_values]
        holm_p = cls.holm_bonferroni_correction(p_values)
        bh_q = cls.benjamini_hochberg_fdr(p_values)
        min_p = min((float(p) for p in p_values), default=None)
        haircut_sr = cls.calculate_haircut_sharpe(
            estimated_sharpe=estimated_sharpe,
            effective_trials_k=authoritative_k,
            sample_size_t=sample_size_t,
            raw_p_value=min_p,
        )

        min_holm = min((float(p) for p in holm_p), default=1.0)
        is_significant = min_holm <= confidence_level_alpha

        return MultipleTestingResult(
            effective_trials_k=authoritative_k,
            raw_p_values=raw_dec,
            holm_bonferroni_p_values=holm_p,
            benjamini_hochberg_q_values=bh_q,
            haircut_sharpe_ratio=haircut_sr,
            is_fwer_significant=is_significant,
        )


