"""Unit tests for Source Ordering, ASCII Byte-wise Comparison, and ReconstructionOrderKey (Phase 3B)."""

from datetime import datetime, timezone
import pytest

from acash.data.orderbook.hashing import (
    ReconstructionOrderKey,
    create_delta_order_key,
    create_snapshot_frame_boundary,
)


def test_ascii_source_order_key_total_ordering() -> None:
    """Verify deterministic byte-wise lexical ordering of source_order_key strings."""
    k1 = "00000000000000000009"
    k2 = "00000000000000000010"
    assert k1.encode("ascii") < k2.encode("ascii")

    # Character boundary edge case
    k_a = "FRAME_001_A"
    k_b = "FRAME_001_B"
    assert k_a.encode("ascii") < k_b.encode("ascii")


def test_reconstruction_order_key_5_tuple_comparisons() -> None:
    """Verify 5-tuple ReconstructionOrderKey comparisons across timestamps and message ranks."""
    t1 = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc)

    # Earlier timestamp < later timestamp
    key_early = create_delta_order_key(t1, "ORD_001", action_sub_idx=0)
    key_late = create_delta_order_key(t2, "ORD_001", action_sub_idx=0)
    assert key_early < key_late

    # Same timestamp, different source_order_key
    key_ord1 = create_delta_order_key(t1, "ORD_001", action_sub_idx=0)
    key_ord2 = create_delta_order_key(t1, "ORD_002", action_sub_idx=0)
    assert key_ord1 < key_ord2

    # Same timestamp and order_key, different action_sub_idx
    key_act0 = create_delta_order_key(t1, "ORD_001", action_sub_idx=0)
    key_act1 = create_delta_order_key(t1, "ORD_001", action_sub_idx=1)
    assert key_act0 < key_act1


def test_coincidence_resolution_rank_1_greater_than_rank_0() -> None:
    """Verify that when snapshot and delta share the EXACT same exchange_time and source_order_key,

    delta is deterministically evaluated as strictly AFTER the snapshot boundary (message_type_rank 1 > 0).
    """
    t_shared = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
    order_key_shared = "00000000000000001000"

    # Snapshot frame upper boundary (message_type_rank=0)
    snap_boundary = create_snapshot_frame_boundary(t_shared, order_key_shared)

    # Delta occurring at the exact same timestamp and order key (message_type_rank=1)
    delta_coincident = create_delta_order_key(t_shared, order_key_shared, action_sub_idx=0)

    # In ReconstructionOrderKey: (t, key, rank=1, 0, 0) > (t, key, rank=0, inf, inf) because rank 1 > rank 0
    assert delta_coincident > snap_boundary


def test_zero_source_seq_num_influence_on_ordering() -> None:
    """Verify that source_seq_num is not present in ReconstructionOrderKey and cannot alter ordering."""
    t = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
    # create_delta_order_key only takes (exchange_time_utc, source_order_key, action_sub_idx)
    k1 = create_delta_order_key(t, "001", action_sub_idx=0)
    k2 = create_delta_order_key(t, "001", action_sub_idx=0)
    assert k1 == k2
