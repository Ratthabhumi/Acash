"""Multiple-Testing Corrections and Haircut Sharpe Engine (Phase 6).

Mathematical implementation based on:
- Holm, S. (1979). "A Simple Sequentially Rejective Multiple Test Procedure." Scandinavian Journal of Statistics, 6(2), 65–70.
- Benjamini, Y., & Hochberg, Y. (1995). "Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing." Journal of the Royal Statistical Society: Series B, 57(1), 289–300.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). "... and the Cross-Section of Expected Returns." Review of Financial Studies, 29(1), 5–68.

Strictly enforces:
- Holm-Bonferroni step-down procedure for strict Family-Wise Error Rate (FWER) control across K trials.
- Benjamini-Hochberg procedure for False Discovery Rate (FDR) q-values.
- Harvey-Liu-Zhu multiple-testing haircut Sharpe hurdle deduction.
"""

from decimal import Decimal
import math
from typing import List, Sequence, Tuple, Union
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.validation.schema import MultipleTestingResult


class MultipleTestingEngine:
    """Controls multiple testing inflation across exploratory search paths and trials."""

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

        return [to_decimal18(Decimal(f"{p:.12f}")) or Decimal("1.0") for p in adj_p_original]

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

        return [to_decimal18(Decimal(f"{q:.12f}")) or Decimal("1.0") for p in q_original]

    @staticmethod
    def calculate_haircut_sharpe(
        estimated_sharpe: float,
        effective_trials_k: int,
        sample_size_t: int,
    ) -> Decimal:
        """Calculate Haircut Sharpe Ratio adjusting for K trials and sample length T (Harvey, Liu, & Zhu 2016).

        Mathematical Formulation:
        Under the null hypothesis of zero true alpha across K orthogonal trials, the expected maximum
        t-statistic asymptotically scales as E[max t_k] ~ sqrt(2 * ln(K)).
        Since t = SR * sqrt(T), the multiple-testing threshold hurdle is SR_hurdle = sqrt(2 * ln(K)) / sqrt(T).
        The Haircut Sharpe ratio deducts this selection hurdle:
        Haircut_SR = max(0.0, estimated_sharpe - (sqrt(2 * ln(K)) / sqrt(T)))
        """
        K = max(1, effective_trials_k)
        T = max(2, sample_size_t)
        sr = max(0.0, estimated_sharpe)

        if K == 1 or sr <= 1e-12:
            return to_decimal18(Decimal(f"{sr:.12f}")) or Decimal("0.0")

        hurdle = math.sqrt(2.0 * math.log(K)) / math.sqrt(T)
        haircut_sr = max(0.0, sr - hurdle)

        return to_decimal18(Decimal(f"{haircut_sr:.12f}")) or Decimal("0.0")

    @classmethod
    def evaluate_multiple_testing(
        cls,
        p_values: Sequence[Union[Decimal, float]],
        estimated_sharpe: float,
        sample_size_t: int,
        confidence_level_alpha: float = 0.05,
    ) -> MultipleTestingResult:
        """Evaluate full multiple testing battery across K trials."""
        raw_dec = [to_decimal18(Decimal(f"{float(p):.12f}")) or Decimal("1.0") for p in p_values]
        holm_p = cls.holm_bonferroni_correction(p_values)
        bh_q = cls.benjamini_hochberg_fdr(p_values)
        haircut_sr = cls.calculate_haircut_sharpe(estimated_sharpe, len(p_values), sample_size_t)

        min_holm = min((float(p) for p in holm_p), default=1.0)
        is_significant = min_holm <= confidence_level_alpha

        return MultipleTestingResult(
            raw_p_values=raw_dec,
            holm_bonferroni_p_values=holm_p,
            benjamini_hochberg_q_values=bh_q,
            haircut_sharpe_ratio=haircut_sr,
            is_fwer_significant=is_significant,
        )
