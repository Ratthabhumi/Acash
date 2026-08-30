"""Unit tests for Combinatorial Purged Cross-Validation (CPCV) and boundary purging."""

import math
import numpy as np
import pytest


from acash.core.domain.exceptions import DataContractError
from acash.validation.cpcv import CombinatorialPurgedCrossValidation
from acash.validation.schema import ValidationConfig


def test_cpcv_combinations_count_and_disjoint_partitions() -> None:
    """Verify that CPCV generates exactly C = (N choose k) partitions and non-empty index sets."""
    config = ValidationConfig(cpcv_num_groups_n=6, cpcv_num_test_groups_k=2, embargo_bars=2)
    cpcv = CombinatorialPurgedCrossValidation(config)

    # N = 6, k = 2 -> (6 choose 2) = 15 combinations
    partitions = cpcv.generate_partitions(sample_size=120, label_horizon=3)
    assert len(partitions) == 15

    has_purged = False
    for p in partitions:
        assert len(p.test_group_indices) == 2
        assert len(p.test_indices) == 40  # 2 groups of 20 bars each
        assert len(p.train_indices) > 0
        if len(p.purged_indices) > 0:
            has_purged = True

        # Assert no overlap between train and test
        assert set(p.train_indices).isdisjoint(set(p.test_indices))
        # Assert no overlap between train and purged
        assert set(p.train_indices).isdisjoint(set(p.purged_indices))
        # Assert no overlap between train and embargoed
        assert set(p.train_indices).isdisjoint(set(p.embargoed_indices))

    assert has_purged is True


def test_cpcv_strict_label_purging_boundary_invariance() -> None:
    """Verify that training samples whose forward label window overlaps with test window are strictly purged."""
    config = ValidationConfig(cpcv_num_groups_n=4, cpcv_num_test_groups_k=1, embargo_bars=0)
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
    config = ValidationConfig(cpcv_num_groups_n=6, cpcv_num_test_groups_k=2, embargo_bars=1)
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


def test_cpcv_combinatorial_assignment_structure_invariants() -> None:
    """Adversarially verify the exact combinatorial assignment structure of pseudo-OOS paths."""
    N = 6
    k = 2
    T = 180
    config = ValidationConfig(cpcv_num_groups_n=N, cpcv_num_test_groups_k=k, embargo_bars=2)
    cpcv = CombinatorialPurgedCrossValidation(config)

    partitions = cpcv.generate_partitions(sample_size=T, label_horizon=4)
    paths = cpcv.reconstruct_pseudo_oos_paths(partitions, sample_size=T)

    phi = (k * len(partitions)) // N  # (2 * 15) // 6 = 5
    assert len(paths) == phi

    group_size = T // N  # 30
    group_bounds = {g: (g * group_size, (g + 1) * group_size) for g in range(N)}

    # 1. Verify pairwise disjointness and exact union of group bounds
    covered_indices = set()
    for g1 in range(N):
        g1_start, g1_end = group_bounds[g1]
        g1_set = set(range(g1_start, g1_end))
        covered_indices.update(g1_set)
        for g2 in range(g1 + 1, N):
            g2_start, g2_end = group_bounds[g2]
            g2_set = set(range(g2_start, g2_end))
            assert g1_set.isdisjoint(g2_set), f"Group {g1} and {g2} overlap!"

    assert covered_indices == set(range(T))

    # 2. Verify each path has exactly one test assignment per group
    group_test_counts_across_paths = {g: 0 for g in range(N)}

    for path_idx, path in enumerate(paths):
        # Group membership of indices in this path
        group_counts_in_path = {g: 0 for g in range(N)}
        for combo_id, sample_idx in path:
            # Map sample_idx to its group
            g_of_idx = sample_idx // group_size
            group_counts_in_path[g_of_idx] += 1

        for g in range(N):
            assert group_counts_in_path[g] == group_size, (
                f"Path {path_idx} does not contain exactly group {g}'s {group_size} bars (got {group_counts_in_path[g]})."
            )
            group_test_counts_across_paths[g] += 1

    # 3. Across all phi paths, every group was tested exactly phi times
    for g in range(N):
        assert group_test_counts_across_paths[g] == phi, (
            f"Group {g} tested {group_test_counts_across_paths[g]} times across paths, expected {phi}."
        )


def test_cpcv_cscv_matrix_evaluation_and_pbo_pipeline() -> None:
    """Verify that evaluate_cscv_sharpe_matrices constructs valid (C, M) IS/OOS matrices and integrates with PBO."""
    from acash.validation.overfitting import OverfittingEngine

    N = 6
    k = 2
    T = 240
    M = 10
    config = ValidationConfig(cpcv_num_groups_n=N, cpcv_num_test_groups_k=k, embargo_bars=2)
    cpcv = CombinatorialPurgedCrossValidation(config)

    # Synthetic return matrix for M models
    np.random.seed(42)
    return_matrix = np.random.normal(0.0005, 0.01, (T, M))

    # Evaluate CSCV matrices
    is_mat, oos_mat = cpcv.evaluate_cscv_sharpe_matrices(
        return_matrix=return_matrix,
        label_horizon=4,
        embargo_bars=2,
    )

    C = math.comb(N, k)  # 15
    assert is_mat.shape == (C, M)
    assert oos_mat.shape == (C, M)

    # Verify no NaN or Inf
    assert not np.isnan(is_mat).any()
    assert not np.isnan(oos_mat).any()
    assert not np.isinf(is_mat).any()
    assert not np.isinf(oos_mat).any()

    # Pass to calculate_pbo
    pbo, logits_mean, logits_std = OverfittingEngine.calculate_pbo(is_mat, oos_mat)
    assert 0.0 <= pbo <= 1.0
    assert isinstance(logits_mean, float)
    assert isinstance(logits_std, float)


def test_cscv_balanced_split_enforcement() -> None:
    """Verify that CSCV mode strictly enforces balanced half/half partition (N even, k = N / 2)."""
    # 1. Reject odd N in ValidationConfig
    with pytest.raises(DataContractError, match="cscv_num_groups_n must be an even integer"):
        ValidationConfig(cscv_num_groups_n=5, cscv_num_test_groups_k=2)

    # 2. Reject unbalanced k in ValidationConfig
    with pytest.raises(DataContractError, match="cscv_num_test_groups_k .* must strictly equal cscv_num_groups_n // 2"):
        ValidationConfig(cscv_num_groups_n=6, cscv_num_test_groups_k=2)

    # 3. Accept balanced (N=6, k=3)
    config_balanced = ValidationConfig(cscv_num_groups_n=6, cscv_num_test_groups_k=3)
    cpcv_balanced = CombinatorialPurgedCrossValidation(config_balanced)
    partitions = cpcv_balanced.generate_partitions(sample_size=120, label_horizon=1, enforce_cscv_balanced=True)
    assert len(partitions) == math.comb(6, 3)  # 20 splits


def test_cpcv_matrix_rejects_non_finite_returns() -> None:
    """Verify that evaluate_cscv_sharpe_matrices rejects NaN or Inf return entries."""
    config = ValidationConfig(cpcv_num_groups_n=4, cpcv_num_test_groups_k=2)
    cpcv = CombinatorialPurgedCrossValidation(config)

    mat_nan = np.ones((40, 3))
    mat_nan[5, 1] = np.nan
    with pytest.raises(DataContractError, match="return_matrix contains non-finite values"):
        cpcv.evaluate_cscv_sharpe_matrices(mat_nan)

    mat_inf = np.ones((40, 3))
    mat_inf[10, 0] = np.inf
    with pytest.raises(DataContractError, match="return_matrix contains non-finite values"):
        cpcv.evaluate_cscv_sharpe_matrices(mat_inf)


def test_cpcv_matrix_fails_closed_on_zero_variance_split() -> None:
    """Verify that evaluate_cscv_sharpe_matrices strictly fails closed when any split has zero variance."""
    config = ValidationConfig(cpcv_num_groups_n=4, cpcv_num_test_groups_k=2)
    cpcv = CombinatorialPurgedCrossValidation(config)

    # Constant matrix -> std = 0.0 in all splits
    mat_zero_var = np.ones((40, 3), dtype=np.float64) * 0.01
    with pytest.raises(DataContractError, match="Zero or near-zero In-Sample return variance"):
        cpcv.evaluate_cscv_sharpe_matrices(mat_zero_var)


def test_reconstruct_pseudo_oos_paths_rejects_empty_partitions() -> None:
    """Verify that reconstruct_pseudo_oos_paths rejects empty partitions list."""
    cpcv = CombinatorialPurgedCrossValidation()
    with pytest.raises(DataContractError, match="Cannot reconstruct pseudo-OOS paths from empty partitions"):
        cpcv.reconstruct_pseudo_oos_paths([], sample_size=100)


def test_reconstruct_pseudo_oos_paths_rejects_non_uniform_k() -> None:
    """Verify that reconstruct_pseudo_oos_paths rejects partitions with non-uniform test group sizes k."""
    config = ValidationConfig(cpcv_num_groups_n=4, cpcv_num_test_groups_k=2)
    cpcv = CombinatorialPurgedCrossValidation(config)
    partitions = cpcv.generate_partitions(sample_size=100, label_horizon=1)

    # Corrupt partition 1 to have k=1 instead of uniform k=2
    corrupted_partitions = list(partitions)
    corrupted_partitions[1] = corrupted_partitions[1].model_copy(update={"test_group_indices": [0]})

    with pytest.raises(DataContractError, match="does not match expected uniform test group size k=2"):
        cpcv.reconstruct_pseudo_oos_paths(corrupted_partitions, sample_size=100)



def test_reconstruct_pseudo_oos_paths_rejects_duplicate_combinations() -> None:
    """Verify that reconstruct_pseudo_oos_paths rejects duplicated partition combinations."""
    config = ValidationConfig(cpcv_num_groups_n=4, cpcv_num_test_groups_k=2)
    cpcv = CombinatorialPurgedCrossValidation(config)
    partitions = cpcv.generate_partitions(sample_size=100, label_horizon=1)

    # Corrupt by replacing partition 1 with partition 0's test groups
    corrupted_partitions = list(partitions)
    corrupted_partitions[1] = corrupted_partitions[1].model_copy(
        update={"test_group_indices": list(partitions[0].test_group_indices)}
    )

    with pytest.raises(DataContractError, match="Duplicate test group combination"):
        cpcv.reconstruct_pseudo_oos_paths(corrupted_partitions, sample_size=100)


def test_reconstruct_pseudo_oos_paths_rejects_incomplete_universe() -> None:
    """Verify that reconstruct_pseudo_oos_paths rejects partitions with missing group indices in the universe."""
    config = ValidationConfig(cpcv_num_groups_n=4, cpcv_num_test_groups_k=2)
    cpcv = CombinatorialPurgedCrossValidation(config)
    partitions = cpcv.generate_partitions(sample_size=100, label_horizon=1)

    # Corrupt all partitions where group 3 appears, replacing with group 0
    corrupted_partitions = []
    for p in partitions:
        new_groups = [0 if g == 3 else g for g in p.test_group_indices]
        # Ensure distinct per partition
        if len(set(new_groups)) < len(new_groups):
            new_groups = [1, 2]
        corrupted_partitions.append(p.model_copy(update={"test_group_indices": new_groups}))

    with pytest.raises(DataContractError):
        cpcv.reconstruct_pseudo_oos_paths(corrupted_partitions, sample_size=100)


def test_reconstruct_pseudo_oos_paths_rejects_partition_count_mismatch() -> None:
    """Verify that reconstruct_pseudo_oos_paths rejects when partition count != (N choose k)."""
    config = ValidationConfig(cpcv_num_groups_n=4, cpcv_num_test_groups_k=2)
    cpcv = CombinatorialPurgedCrossValidation(config)
    partitions = cpcv.generate_partitions(sample_size=100, label_horizon=1)

    # Remove the last partition: C = 5 instead of 6
    truncated_partitions = partitions[:-1]
    with pytest.raises(DataContractError, match="Partition count mismatch: received 5 partitions, expected exactly"):
        cpcv.reconstruct_pseudo_oos_paths(truncated_partitions, sample_size=100)





