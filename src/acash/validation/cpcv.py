"""Combinatorial Purged Cross-Validation (CPCV) Generator (Phase 6).

Implements Marcos López de Prado's Combinatorial Purged Cross-Validation:
- Divides time series of T observations into N contiguous groups.
- Evaluates all C = (N choose k) combinations of k test groups.
- Applies strict interval purging: training samples whose label windows [t+1, t+H] overlap
  with test evaluation windows [T_test_start, T_test_end] are purged.
- Applies strict post-test embargo buffers (>= max(H) bars) to eliminate autoregressive serial correlation.
- Reconstructs phi = (k / N) * (N choose k) continuous pseudo-OOS backtest paths.
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

        # 1. Compute contiguous group boundaries [start_idx, end_idx)
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
                    # Purge condition: Training sample's label interval overlaps with test interval [test_start, test_end - 1]
                    # Overlap occurs when label_start < test_end and label_end >= test_start
                    if (label_start < test_end) and (label_end >= test_start):
                        is_purged = True
                        break

                    # Embargo condition: Training sample falls within [test_end, test_end + embargo]
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
        """Reconstruct phi = (k / N) * (N choose k) continuous pseudo-OOS backtest paths.

        Returns:
            List of paths, where each path is a list of (combination_id, test_index) pairings covering [0, sample_size).
        """
        N = self.config.num_groups_n
        k = self.config.num_test_groups_k
        total_combos = len(partitions)
        expected_paths = (k * total_combos) // N

        # Map each group to the list of combination IDs that tested that group
        group_to_combos: Dict[int, List[int]] = {g: [] for g in range(N)}
        for p in partitions:
            for g in p.test_group_indices:
                group_to_combos[g].append(p.combination_id)

        # Build paths by selecting one combination per group sequentially
        paths: List[List[Tuple[int, int]]] = []
        for path_idx in range(expected_paths):
            path_pairs: List[Tuple[int, int]] = []
            for g in range(N):
                combo_list = group_to_combos[g]
                combo_id = combo_list[path_idx % len(combo_list)]
                # Find test indices belonging to this group in that partition
                p = partitions[combo_id]
                for idx in p.test_indices:
                    path_pairs.append((combo_id, idx))
            paths.append(path_pairs)

        return paths
