"""Combinatorial Purged Cross-Validation (CPCV) & CSCV Generator (Phase 6).

Implements:
1. Combinatorial Purged Cross-Validation (CPCV / Marcos López de Prado 2018):
   - Divides time series of T observations into N contiguous groups.
   - Evaluates all C = (N choose k) combinations of k test groups.
   - Applies strict interval purging: training samples whose forward label windows [t+1, t+H] overlap
     with test evaluation windows [T_test_start, T_test_end) are purged to eliminate lookahead leakage.
   - Applies post-test embargo buffers [T_test_end, T_test_end + embargo_bars) to prevent post-test
     boundary dependency leakage.
2. Combinatorially Symmetric Cross-Validation (CSCV / Bailey et al. 2016):
   - Specific PBO evaluation configuration where N is strictly even and k = N / 2 (balanced half/half split).
   - Evaluates all C = (N choose N/2) symmetric splits for In-Sample (IS) and Out-of-Sample (OOS) performance.
   - Reconstructs exactly phi = (k / N) * (N choose k) = 0.5 * (N choose N/2) continuous, non-overlapping
     pseudo-OOS backtest paths through canonical bijective slice decomposition.
"""

from decimal import Decimal
import itertools
import math
from typing import Dict, List, Optional, Sequence, Set, Tuple
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.validation.schema import CPCVPartition, ValidationConfig


class CombinatorialPurgedCrossValidation:
    """Generates purged and embargoed combinatorial cross-validation splits and pseudo-OOS paths."""

    def __init__(self, config: Optional[ValidationConfig] = None) -> None:
        self.config = config or ValidationConfig()

    def generate_partitions(
        self,
        sample_size: int,
        label_horizon: int,
        embargo_bars: Optional[int] = None,
        enforce_cscv_balanced: bool = False,
    ) -> List[CPCVPartition]:
        """Generate all C = (N choose k) CPCV/CSCV partitions with exact boundary purging and embargoing.

        Args:
            sample_size: Total number of observations T.
            label_horizon: Forward-looking label evaluation window H (bars).
            embargo_bars: Optional override for post-test embargo buffer (defaults to config.embargo_bars).
            enforce_cscv_balanced: If True, enforces CSCV balance contract (N is even and k = N / 2).

        Returns:
            List of CPCVPartition objects containing explicit index sets.
        """
        N = self.config.num_groups_n
        k = self.config.num_test_groups_k
        embargo = embargo_bars if embargo_bars is not None else self.config.embargo_bars

        if enforce_cscv_balanced:
            N = self.config.cscv_num_groups_n
            k = self.config.cscv_num_test_groups_k
            if N % 2 != 0 or k != N // 2:
                raise DataContractError(
                    f"CSCV (PBO mode) requires an even number of blocks N and balanced half-splits k = N / 2. "
                    f"Got N={N}, k={k}."
                )
        else:
            N = self.config.cpcv_num_groups_n
            k = self.config.cpcv_num_test_groups_k

        embargo = embargo_bars if embargo_bars is not None else self.config.embargo_bars

        if sample_size < N * 2:
            # ACASH Minimum Data Sufficiency Governance Policy:
            # Enforces a minimum of 2 observations per partition block (T >= 2N) to guarantee
            # well-defined, non-degenerate sample variance calculations within individual splits.
            raise DataContractError(
                f"Sample size {sample_size} is too small for {N} CPCV groups. "
                f"ACASH governance policy requires at least 2 bars per block (minimum: {N * 2} bars)."
            )
        if k >= N or k < 1:
            raise DataContractError(f"Invalid test groups k={k} for total groups N={N}. Must satisfy 1 <= k < N.")
        if label_horizon < 1:
            raise DataContractError(f"Label horizon must be positive: {label_horizon}")

        # 1. Compute contiguous group boundaries [g_start, g_end)
        group_bounds: List[Tuple[int, int]] = []
        base_size = sample_size // N
        remainder = sample_size % N

        start = 0
        for i in range(N):
            size = base_size + (1 if i < remainder else 0)
            end = start + size
            group_bounds.append((start, end))
            start = end

        # 2. Generate all C = (N choose k) combinations of test groups
        all_combinations = list(itertools.combinations(range(N), k))
        partitions: List[CPCVPartition] = []

        all_indices = set(range(sample_size))

        for combo_id, test_groups in enumerate(all_combinations):
            # Collect test indices and test window intervals [start, end)
            test_indices_set: Set[int] = set()
            test_intervals: List[Tuple[int, int]] = []

            for g_idx in test_groups:
                g_start, g_end = group_bounds[g_idx]
                test_intervals.append((g_start, g_end))
                test_indices_set.update(range(g_start, g_end))

            test_indices = sorted(list(test_indices_set))

            # 3. Purging: remove training samples whose forward label window overlaps with ANY test window
            candidate_train_set = all_indices - test_indices_set
            purged_set: Set[int] = set()

            for t in candidate_train_set:
                label_end = t + label_horizon
                for t_start, t_end in test_intervals:
                    if t < t_end and label_end >= t_start:
                        purged_set.add(t)
                        break

            # 4. Embargoing: remove training samples within embargo window immediately after ANY test window
            embargoed_set: Set[int] = set()
            if embargo > 0:
                for _, t_end in test_intervals:
                    for t in range(t_end, min(sample_size, t_end + embargo)):
                        if t in candidate_train_set and t not in purged_set:
                            embargoed_set.add(t)

            # Final clean training set
            train_indices = sorted(list(candidate_train_set - purged_set - embargoed_set))
            purged_indices = sorted(list(purged_set))
            embargoed_indices = sorted(list(embargoed_set))

            partitions.append(
                CPCVPartition(
                    combination_id=combo_id,
                    test_group_indices=list(test_groups),
                    train_indices=train_indices,
                    test_indices=test_indices,
                    purged_indices=purged_indices,
                    embargoed_indices=embargoed_indices,
                )
            )

        return partitions

    def reconstruct_pseudo_oos_paths(
        self,
        partitions: List[CPCVPartition],
        sample_size: int,
    ) -> List[List[Tuple[int, int]]]:
        """Reconstruct exactly phi = (k / N) * (N choose k) continuous, non-overlapping pseudo-OOS paths.

        ARCHITECTURAL SPECIFICATION & EVIDENCE BOUNDARY:
        - The pseudo-OOS path reconstruction (phi paths) is a structural mechanism for generating full-length,
          continuous chronological return trajectories over [0, T) for downstream equity curve dispersion,
          drawdown distribution, and tail-risk analysis.
        - The Probability of Backtest Overfitting (PBO) calculation in `OverfittingEngine.calculate_pbo()`
          directly consumes the discrete (C, M) In-Sample and Out-of-Sample Sharpe matrices over all C
          combinations produced by `evaluate_cscv_sharpe_matrices()`.

        Combinatorial Decomposition & Bijective Coverage Proof:
        1. Universe of OOS slices: Across all C = (N choose k) combinations, exactly C * k testing slices are generated.
        2. Group slice distribution: By combinatorial symmetry, each group g in {0, ..., N-1} appears in exactly
           (N-1 choose k-1) = (k / N) * (N choose k) = phi combinations.
        3. Canonical Path Construction: Let S_g = [c_(g, 0), c_(g, 1), ..., c_(g, phi-1)] be the lexicographically
           ordered list of combination IDs in which group g is tested. For path p in {0, ..., phi-1}, we extract
           group g's slice from combination c_(g, p).
        4. Totality & Non-overlap:
           - Each path p contains exactly one slice for every group g in {0, ..., N-1}.
           - Since groups partition [0, sample_size) contiguously, each path p covers [0, sample_size) completely with zero overlap.
           - Across all phi paths, exactly phi * N = k * C slices are used, establishing an exact bijection with the OOS slice universe.

        STRICT STRUCTURAL PARTITION VALIDATION:
        Before reconstruction, the supplied partition battery is unconditionally validated against all
        combinatorial structure axioms:
        1. Uniform k: For all p in P, |TestGroups(p)| == k.
        2. Uniqueness: For all p_i != p_j, TestGroups(p_i) != TestGroups(p_j) (no duplicate combinations).
        3. Complete Contiguous Universe: Union_p TestGroups(p) == {0, 1, ..., N - 1} with no gaps or negative indices.
        4. Total Combinatorial Count: |P| == (N choose k).
        5. Valid Bounds: 1 <= k < N and sample_size >= 2 * N.

        Returns:
            List of phi paths, where each path is a list of (combination_id, test_sample_index) pairings covering [0, sample_size).
        """
        if not partitions:
            raise DataContractError("Cannot reconstruct pseudo-OOS paths from empty partitions.")

        # 1. Structural Validation: Uniform test group size k and uniqueness of combinations
        k = len(partitions[0].test_group_indices)
        if k < 1:
            raise DataContractError(f"Invalid test group size k={k}. Must have at least 1 test group per partition.")

        seen_combinations: Set[Tuple[int, ...]] = set()
        all_groups_set: Set[int] = set()

        for p_idx, p in enumerate(partitions):
            p_test_groups = p.test_group_indices
            if len(p_test_groups) != k:
                raise DataContractError(
                    f"Partition {p_idx} (combination_id={p.combination_id}) has test group size {len(p_test_groups)} "
                    f"which does not match expected uniform test group size k={k}."
                )
            if len(set(p_test_groups)) != k:
                raise DataContractError(
                    f"Partition {p_idx} (combination_id={p.combination_id}) contains internal duplicate test groups: {p_test_groups}."
                )

            combo_key = tuple(sorted(p_test_groups))
            if combo_key in seen_combinations:
                raise DataContractError(
                    f"Duplicate test group combination {combo_key} detected at partition {p_idx} (combination_id={p.combination_id}). "
                    f"All combinatorial partitions must be strictly unique."
                )
            seen_combinations.add(combo_key)
            all_groups_set.update(p_test_groups)

        N = len(all_groups_set)
        if k >= N or N < 2:
            raise DataContractError(
                f"Invalid combinatorial partition universe: N={N}, k={k}. Must satisfy 1 <= k < N with N >= 2."
            )

        # 2. Structural Validation: Union of test groups must form exact contiguous set {0, 1, ..., N - 1}
        expected_universe = set(range(N))
        if all_groups_set != expected_universe:
            missing_groups = sorted(list(expected_universe - all_groups_set))
            invalid_groups = sorted(list(all_groups_set - expected_universe))
            raise DataContractError(
                f"Partition group indices do not form a complete contiguous universe {{0, ..., {N-1}}}. "
                f"Missing groups: {missing_groups}, Invalid groups: {invalid_groups}."
            )

        # 3. Structural Validation: Total partition count must strictly equal (N choose k)
        expected_total_combos = math.comb(N, k)
        if len(partitions) != expected_total_combos:
            raise DataContractError(
                f"Partition count mismatch: received {len(partitions)} partitions, "
                f"expected exactly ({N} choose {k}) = {expected_total_combos} combinations."
            )

        # 4. Data Sufficiency Governance Policy
        if sample_size < N * 2:
            raise DataContractError(
                f"Sample size {sample_size} is too small for {N} CPCV groups. "
                f"ACASH governance policy requires at least 2 bars per block (minimum: {N * 2} bars)."
            )

        expected_paths = (k * expected_total_combos) // N

        # 5. Compute contiguous group boundaries [g_start, g_end)
        group_bounds: List[Tuple[int, int]] = []
        base_size = sample_size // N
        remainder = sample_size % N

        start = 0
        for i in range(N):
            size = base_size + (1 if i < remainder else 0)
            end = start + size
            group_bounds.append((start, end))
            start = end

        # 6. For each group g, identify all combinations where g was one of the k test groups
        group_to_testing_combos: Dict[int, List[int]] = {g: [] for g in range(N)}
        for p in partitions:
            for g in p.test_group_indices:
                group_to_testing_combos[g].append(p.combination_id)

        # Verify that each group has exactly expected_paths testing combinations
        for g in range(N):
            if len(group_to_testing_combos[g]) != expected_paths:
                raise DataContractError(
                    f"Group {g} has {len(group_to_testing_combos[g])} testing combinations, expected {expected_paths}"
                )

        # 7. Construct the phi distinct pseudo-OOS paths
        paths: List[List[Tuple[int, int]]] = []
        for path_idx in range(expected_paths):
            path_pairs: List[Tuple[int, int]] = []
            for g in range(N):
                combo_id = group_to_testing_combos[g][path_idx]
                g_start, g_end = group_bounds[g]
                # For group g, extract ONLY the indices belonging to group g [g_start, g_end)
                for t in range(g_start, g_end):
                    path_pairs.append((combo_id, t))

            # Invariant verification: Each path must cover exactly all sample_size indices in chronological order
            if len(path_pairs) != sample_size or [t for _, t in path_pairs] != list(range(sample_size)):
                raise DataContractError(f"Path {path_idx} failed full chronological coverage invariant over [0, {sample_size})")

            paths.append(path_pairs)

        return paths


    def evaluate_cscv_sharpe_matrices(
        self,
        return_matrix: np.ndarray,
        label_horizon: int = 1,
        embargo_bars: Optional[int] = None,
        periods_per_year: float = 252.0,
        enforce_cscv_balanced: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute In-Sample and Out-of-Sample Sharpe matrices for all M models across all C = (N choose k) splits.

        Implements Combinatorial Purged Cross-Validation (CPCV / López de Prado 2018) and Combinatorially Symmetric
        Cross-Validation (CSCV / Bailey et al. 2016) with strict interval purging and post-test embargo buffers.

        FAIL-CLOSED NUMERICAL INTEGRITY:
        Every split is verified to have sufficient observations (len > 1), strictly positive sample variance
        (std > 1e-12 across all candidate models), and finite Sharpe values. Zero or near-zero variance splits
        immediately raise DataContractError rather than fabricating artificial 0.0 Sharpe ratios that distort
        downstream rank statistics and PBO estimation.

        Args:
            return_matrix: 2D numpy array of shape (T observations, M candidate strategies/models).
            label_horizon: Forward-looking label evaluation window H (bars).
            embargo_bars: Post-test embargo window (defaults to config.embargo_bars).
            periods_per_year: Number of periods per year for standard sqrt(periods_per_year) Sharpe annualization.
            enforce_cscv_balanced: If True, strictly enforces balanced CSCV (N even, k = N / 2) for PBO evaluation.

        Returns:
            Tuple[is_sharpe_matrix, oos_sharpe_matrix] where each has shape (C combinations, M models).
        """
        if return_matrix.ndim != 2:
            raise DataContractError(f"return_matrix must be 2D array of shape (T, M), got shape {return_matrix.shape}")

        if not np.all(np.isfinite(return_matrix)):
            raise DataContractError("return_matrix contains non-finite values (NaN, +inf, or -inf).")

        T, M = return_matrix.shape
        partitions = self.generate_partitions(
            sample_size=T,
            label_horizon=label_horizon,
            embargo_bars=embargo_bars,
            enforce_cscv_balanced=enforce_cscv_balanced,
        )
        C = len(partitions)

        is_sharpe_mat = np.zeros((C, M), dtype=np.float64)
        oos_sharpe_mat = np.zeros((C, M), dtype=np.float64)

        sqrt_ann = math.sqrt(periods_per_year) if periods_per_year > 0 else 1.0

        for c, p in enumerate(partitions):
            # In-Sample evaluation (purged and embargoed indices excluded)
            train_idx = p.train_indices
            if len(train_idx) <= 1:
                raise DataContractError(
                    f"Insufficient in-sample observations in partition split {c}: {len(train_idx)} <= 1."
                )
            is_slice = return_matrix[train_idx, :]
            is_mean = np.mean(is_slice, axis=0)
            is_std = np.std(is_slice, axis=0, ddof=1)

            if np.any(is_std <= 1e-12):
                min_std = float(np.min(is_std))
                raise DataContractError(
                    f"Zero or near-zero In-Sample return variance (min std={min_std:.2e} <= 1e-12) encountered in partition split {c}. "
                    f"Sharpe ratio is mathematically undefined."
                )

            is_sr = (is_mean / is_std) * sqrt_ann
            if not np.all(np.isfinite(is_sr)):
                raise DataContractError(
                    f"Non-finite In-Sample Sharpe ratio encountered in partition split {c}."
                )
            is_sharpe_mat[c, :] = is_sr

            # Out-of-Sample evaluation (pure testing window)
            test_idx = p.test_indices
            if len(test_idx) <= 1:
                raise DataContractError(
                    f"Insufficient out-of-sample observations in partition split {c}: {len(test_idx)} <= 1."
                )
            oos_slice = return_matrix[test_idx, :]
            oos_mean = np.mean(oos_slice, axis=0)
            oos_std = np.std(oos_slice, axis=0, ddof=1)

            if np.any(oos_std <= 1e-12):
                min_std = float(np.min(oos_std))
                raise DataContractError(
                    f"Zero or near-zero Out-of-Sample return variance (min std={min_std:.2e} <= 1e-12) encountered in partition split {c}. "
                    f"Sharpe ratio is mathematically undefined."
                )

            oos_sr = (oos_mean / oos_std) * sqrt_ann
            if not np.all(np.isfinite(oos_sr)):
                raise DataContractError(
                    f"Non-finite Out-of-Sample Sharpe ratio encountered in partition split {c}."
                )
            oos_sharpe_mat[c, :] = oos_sr

        return is_sharpe_mat, oos_sharpe_mat


    def evaluate_balanced_cscv_sharpe_matrices(
        self,
        return_matrix: np.ndarray,
        label_horizon: int = 1,
        embargo_bars: Optional[int] = None,
        periods_per_year: float = 252.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convenience method enforcing strict CSCV balanced half/half partition (N even, k = N / 2)."""
        return self.evaluate_cscv_sharpe_matrices(
            return_matrix=return_matrix,
            label_horizon=label_horizon,
            embargo_bars=embargo_bars,
            periods_per_year=periods_per_year,
            enforce_cscv_balanced=True,
        )



