"""Combinatorial Purged Cross-Validation (CPCV) Generator (Phase 6).

Implements Marcos López de Prado's Combinatorial Purged Cross-Validation:
- Divides time series of T observations into N contiguous groups.
- Evaluates all C = (N choose k) combinations of k test groups.
- Applies strict interval purging: training samples whose forward label windows [t+1, t+H] overlap
  with test evaluation windows [T_test_start, T_test_end) are purged.
- Applies post-test embargo buffers [T_test_end, T_test_end + embargo_bars) to prevent post-test
  boundary dependence leakage.
- Reconstructs phi = (k / N) * (N choose k) continuous, non-overlapping pseudo-OOS backtest paths.
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
    ) -> List[CPCVPartition]:
        """Generate all C = (N choose k) CPCV partitions with exact boundary purging and embargoing.

        Args:
            sample_size: Total number of observations T.
            label_horizon: Forward-looking label evaluation window H (bars).
            embargo_bars: Optional override for post-test embargo buffer (defaults to config.embargo_bars).

        Returns:
            List of CPCVPartition objects containing explicit index sets.
        """
        N = self.config.num_groups_n
        k = self.config.num_test_groups_k
        embargo = embargo_bars if embargo_bars is not None else self.config.embargo_bars

        if sample_size < N * 2:
            raise DataContractError(
                f"Sample size {sample_size} is too small for {N} CPCV groups. Minimum required: {N * 2} bars."
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

            # Determine Purged and Embargoed indices from remaining candidate training samples
            candidate_train_set = all_indices - test_indices_set
            purged_set: Set[int] = set()
            embargoed_set: Set[int] = set()

            for t in candidate_train_set:
                # Forward label interval for observation t is [t + 1, t + label_horizon] (inclusive)
                label_start = t + 1
                label_end = t + label_horizon

                is_purged = False
                is_embargoed = False

                for test_start, test_end in test_intervals:
                    # Purge condition: Training sample's label interval overlaps with test interval [test_start, test_end)
                    # Overlap occurs when (label_start < test_end) and (label_end >= test_start)
                    if (label_start < test_end) and (label_end >= test_start):
                        is_purged = True
                        break

                    # Embargo condition: Training sample falls within post-test window [test_end, test_end + embargo)
                    if embargo > 0 and (test_end <= t < test_end + embargo):
                        is_embargoed = True
                        break

                if is_purged:
                    purged_set.add(t)
                elif is_embargoed:
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

        Each path is composed by taking group g's exact slice [g_start, g_end) from the j-th combination
        that tested group g, guaranteeing complete, non-overlapping coverage of [0, sample_size) per path.

        Returns:
            List of phi paths, where each path is a list of (combination_id, test_sample_index) pairings covering [0, sample_size).
        """
        N = self.config.num_groups_n
        k = self.config.num_test_groups_k
        total_combos = len(partitions)
        expected_paths = (k * total_combos) // N

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

        # 2. For each group g, identify all combinations where g was one of the k test groups
        # By combinatorial identity, each group is tested in exactly (N-1 choose k-1) = phi combinations
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

        # 3. Construct the phi distinct pseudo-OOS paths
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
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute In-Sample and Out-of-Sample Sharpe matrices for all M models across all C = (N choose k) splits.

        Implements Combinatorially Symmetric Cross-Validation (CSCV / Bailey et al. 2016) with strict
        interval purging and post-test embargo buffers (López de Prado 2018).

        Args:
            return_matrix: 2D numpy array of shape (T observations, M candidate strategies/models).
            label_horizon: Forward-looking label evaluation window H (bars).
            embargo_bars: Post-test embargo window (defaults to config.embargo_bars).
            periods_per_year: Number of periods per year for standard sqrt(periods_per_year) Sharpe annualization.

        Returns:
            Tuple[is_sharpe_matrix, oos_sharpe_matrix] where each has shape (C combinations, M models).
        """
        if return_matrix.ndim != 2:
            raise DataContractError(f"return_matrix must be 2D array of shape (T, M), got shape {return_matrix.shape}")

        T, M = return_matrix.shape
        partitions = self.generate_partitions(sample_size=T, label_horizon=label_horizon, embargo_bars=embargo_bars)
        C = len(partitions)

        is_sharpe_mat = np.zeros((C, M), dtype=np.float64)
        oos_sharpe_mat = np.zeros((C, M), dtype=np.float64)

        sqrt_ann = math.sqrt(periods_per_year) if periods_per_year > 0 else 1.0


        for c, p in enumerate(partitions):
            # In-Sample evaluation (purged and embargoed indices excluded)
            train_idx = p.train_indices
            if len(train_idx) > 1:
                is_slice = return_matrix[train_idx, :]
                is_mean = np.mean(is_slice, axis=0)
                is_std = np.std(is_slice, axis=0, ddof=1)
                is_sr = np.where(is_std > 1e-12, (is_mean / is_std) * sqrt_ann, 0.0)
                is_sharpe_mat[c, :] = is_sr

            # Out-of-Sample evaluation (pure testing window)
            test_idx = p.test_indices
            if len(test_idx) > 1:
                oos_slice = return_matrix[test_idx, :]
                oos_mean = np.mean(oos_slice, axis=0)
                oos_std = np.std(oos_slice, axis=0, ddof=1)
                oos_sr = np.where(oos_std > 1e-12, (oos_mean / oos_std) * sqrt_ann, 0.0)
                oos_sharpe_mat[c, :] = oos_sr

        return is_sharpe_mat, oos_sharpe_mat

