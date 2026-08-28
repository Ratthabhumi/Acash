"""Unit tests for Combinatorial Purged Cross-Validation (CPCV) and boundary purging."""

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.cpcv import CombinatorialPurgedCrossValidation
from acash.validation.schema import ValidationConfig


def test_cpcv_combinations_count_and_disjoint_partitions() -> None:
    """Verify that CPCV generates exactly C = (N choose k) partitions and non-empty index sets."""
    config = ValidationConfig(num_groups_n=6, num_test_groups_k=2, embargo_bars=2)
    cpcv = CombinatorialPurgedCrossValidation(config)

    # N = 6, k = 2 -> (6 choose 2) = 15 combinations
    partitions = cpcv.generate_partitions(sample_size=120, label_horizon=3)
    assert len(partitions) == 15

    for p in partitions:
        assert len(p.test_group_indices) == 2
        assert len(p.test_indices) == 40  # 2 groups of 20 bars each
        assert len(p.train_indices) > 0
        assert len(p.purged_indices) > 0

        # Assert no overlap between train and test
        assert set(p.train_indices).isdisjoint(set(p.test_indices))
        # Assert no overlap between train and purged
        assert set(p.train_indices).isdisjoint(set(p.purged_indices))
        # Assert no overlap between train and embargoed
        assert set(p.train_indices).isdisjoint(set(p.embargoed_indices))


def test_cpcv_strict_label_purging_boundary_invariance() -> None:
    """Verify that training samples whose forward label window overlaps with test window are strictly purged."""
    config = ValidationConfig(num_groups_n=4, num_test_groups_k=1, embargo_bars=0)
    cpcv = CombinatorialPurgedCrossValidation(config)

    # 4 groups of 25 bars: G0=[0, 25), G1=[25, 50), G2=[50, 75), G3=[75, 100)
    # Test group = G1 ([25, 50))
    # Forward label horizon H = 5
    # Samples t in [20, 24] have forward label windows [t+1, t+5] which overlap with [25, 50):
    # e.g., t=24 -> [25, 29] overlaps G1; t=20 -> [21, 25] overlaps G1 at 25.
    partitions = cpcv.generate_partitions(sample_size=100, label_horizon=5)

    # Find partition where test_group is G1 (index 1)
    p_g1 = next(p for p in partitions if p.test_group_indices == [1])

    for t_purged in [20, 21, 22, 23, 24]:
        assert t_purged in p_g1.purged_indices
        assert t_purged not in p_g1.train_indices


def test_cpcv_pseudo_oos_paths_reconstruction_complete_coverage() -> None:
    """Verify that all phi pseudo-OOS paths cover [0, T) chronologically without duplication or gaps."""
    config = ValidationConfig(num_groups_n=6, num_test_groups_k=2, embargo_bars=1)
    cpcv = CombinatorialPurgedCrossValidation(config)

    partitions = cpcv.generate_partitions(sample_size=120, label_horizon=3)
    paths = cpcv.reconstruct_pseudo_oos_paths(partitions, sample_size=120)

    # Expected paths phi = (k / N) * (N choose k) = (2 / 6) * 15 = 5 paths
    assert len(paths) == 5

    expected_full_series = list(range(120))
    for path in paths:
        assert len(path) == 120
        # Check that test indices strictly form [0, 1, ..., 119]
        actual_indices = [idx for _, idx in path]
        assert actual_indices == expected_full_series
