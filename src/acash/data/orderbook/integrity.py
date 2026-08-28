"""Data Integrity Validator for Canonical Order Book Snapshots and Deltas (Phase 3B).

Strictly enforces:
- PyArrow Schema conformance.
- ASCII-only source_order_key verification.
- CLEAR control action payload invariants: price=None, size=None, level_idx=None, order_id=None, side in {BID, ASK, ALL}.
- MBP vs MBO order_id invariants:
  - MBP: order_id MUST be NULL.
  - MBO: order_id MUST be non-null and non-empty for ADD, MODIFY, CANCEL, DELETE.
- Snapshot Frame Metadata Consistency: all rows sharing the same snapshot_id must share identical timestamps, dates, sequence, and completeness flag.
- Intra-batch and Global duplicate Snapshot/Delta Row Identity rejection.
- Decimal128 range/precision bounds validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
import pyarrow as pa

from acash.data.integrity import (
    ValidationErrorRecord,
    ValidationMetrics,
    ValidationReport,
)
from acash.data.orderbook.schema import (
    BOOK_DELTA_ROW_IDENTITY_COLUMNS,
    BOOK_SNAPSHOT_COMPOUND_FRAME_COLUMNS,
    BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS,
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
    VALID_DELTA_ACTIONS,
    VALID_DELTA_SIDES,
    VALID_DELTA_TYPES,
    VALID_SNAPSHOT_SIDES,
    SnapshotShapePolicy,
)
from acash.data.schema import (
    DataContractError,
    IntegrityViolationError,
    validate_decimal128_bounds,
)


def _is_ascii(s: str) -> bool:
    """Check if string consists strictly of ASCII characters (0x00 to 0x7F)."""
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


class OrderBookIntegrityValidator:
    """Data integrity and contract validator for Order Book Snapshots and Deltas."""

    def __init__(
        self,
        max_clock_skew_ms: int = 5000,
        shape_policy: SnapshotShapePolicy = SnapshotShapePolicy.FIXED_DEPTH_N,
    ) -> None:
        self.max_clock_skew_ms = max_clock_skew_ms
        self.shape_policy = shape_policy

    def validate_snapshot_table(
        self,
        table: pa.Table,
        existing_snapshot_identity_lookup: Optional[Dict[Tuple[Any, ...], bool]] = None,
    ) -> Tuple[ValidationReport, pa.Table]:
        """Validate a PyArrow table against CANONICAL_BOOK_SNAPSHOT_SCHEMA and contract invariants."""
        # 1. Schema Check
        for field in CANONICAL_BOOK_SNAPSHOT_SCHEMA:
            if field.name not in table.column_names:
                raise DataContractError(f"Missing column in Book Snapshot table: {field.name}")
            col_field = table.schema.field(field.name)
            if col_field.type != field.type:
                raise DataContractError(
                    f"Column '{field.name}' type mismatch: expected {field.type}, got {col_field.type}"
                )

        if table.num_rows == 0:
            metrics = ValidationMetrics(total_rows=0, stream_count=0)
            return ValidationReport(is_valid=True, metrics=metrics), table


        pydict = table.to_pydict()
        num_rows = table.num_rows

        seen_batch_identities: Set[Tuple[Any, ...]] = set()
        frame_metadata_registry: Dict[str, Dict[str, Any]] = {}

        for i in range(num_rows):
            # A. ASCII-only source_order_key
            order_key = str(pydict["source_order_key"][i])
            if not _is_ascii(order_key):
                raise IntegrityViolationError(
                    f"Row {i}: source_order_key '{order_key}' contains non-ASCII characters"
                )

            # B. Price and Size bounds
            px = pydict["price"][i]
            sz = pydict["size"][i]
            if not isinstance(px, Decimal):
                px = Decimal(str(px))
            if not isinstance(sz, Decimal):
                sz = Decimal(str(sz))

            if px <= Decimal("0") or not px.is_finite():
                raise IntegrityViolationError(f"Row {i}: Price must be > 0 and finite, got {px}")
            if sz < Decimal("0") or not sz.is_finite():
                raise IntegrityViolationError(f"Row {i}: Size must be >= 0 and finite, got {sz}")

            validate_decimal128_bounds(px, "price")
            validate_decimal128_bounds(sz, "size")

            # C. Side & Level Validation
            side = str(pydict["side"][i]).upper()
            if side not in VALID_SNAPSHOT_SIDES:
                raise IntegrityViolationError(f"Row {i}: Invalid snapshot side '{side}'")
            level_idx = int(pydict["level_idx"][i])
            if level_idx < 0:
                raise IntegrityViolationError(f"Row {i}: level_idx must be >= 0, got {level_idx}")

            # D. Snapshot Row Identity Duplicate Check
            row_id = (
                str(pydict["source_id"][i]),
                str(pydict["channel_id"][i]),
                str(pydict["symbol"][i]),
                pydict["trading_date"][i],
                int(pydict["source_seq_num"][i]),
                side,
                level_idx,
            )

            if row_id in seen_batch_identities:
                raise IntegrityViolationError(
                    f"BATCH_SNAPSHOT_IDENTITY_DUPLICATE: Duplicate Snapshot Row Identity in batch: {row_id}"
                )
            seen_batch_identities.add(row_id)

            if existing_snapshot_identity_lookup and row_id in existing_snapshot_identity_lookup:
                raise IntegrityViolationError(
                    f"GLOBAL_SNAPSHOT_IDENTITY_DUPLICATE: Snapshot Row Identity already exists in storage: {row_id}"
                )

            # E. Frame Metadata Consistency & Price Level Uniqueness Check
            snap_id = str(pydict["snapshot_id"][i])
            row_meta = {
                "exchange_time_utc": pydict["exchange_time_utc"][i],
                "feed_time_utc": pydict["feed_time_utc"][i],
                "knowledge_time_utc": pydict["knowledge_time_utc"][i],
                "trading_date": pydict["trading_date"][i],
                "source_seq_num": int(pydict["source_seq_num"][i]),
                "source_order_key": order_key,
                "is_snapshot_complete": bool(pydict["is_snapshot_complete"][i]),
            }

            if snap_id not in frame_metadata_registry:
                frame_metadata_registry[snap_id] = row_meta
            else:
                existing_meta = frame_metadata_registry[snap_id]
                for k, v in row_meta.items():
                    if existing_meta[k] != v:
                        raise IntegrityViolationError(
                            f"FRAME_METADATA_INCONSISTENCY: Snapshot frame '{snap_id}' has conflicting metadata for '{k}': {existing_meta[k]} != {v}"
                        )

            # F. Price Level Uniqueness per Side within Snapshot Frame
            snap_side_key = (snap_id, side, px)
            if snap_side_key in seen_batch_identities:
                raise IntegrityViolationError(
                    f"DUPLICATE_PRICE_LEVEL: Duplicate price level {px} detected for side {side} in snapshot frame '{snap_id}'"
                )
            seen_batch_identities.add(snap_side_key)


        metrics = ValidationMetrics(
            total_rows=num_rows,
            stream_count=1,
        )
        return ValidationReport(is_valid=True, metrics=metrics), table

    def validate_delta_table(
        self,
        table: pa.Table,
        existing_delta_identity_lookup: Optional[Dict[Tuple[Any, ...], bool]] = None,
    ) -> Tuple[ValidationReport, pa.Table]:
        """Validate a PyArrow table against CANONICAL_BOOK_DELTA_SCHEMA and contract invariants."""
        # 1. Schema Check
        for field in CANONICAL_BOOK_DELTA_SCHEMA:
            if field.name not in table.column_names:
                raise DataContractError(f"Missing column in Book Delta table: {field.name}")
            col_field = table.schema.field(field.name)
            if col_field.type != field.type:
                raise DataContractError(
                    f"Column '{field.name}' type mismatch: expected {field.type}, got {col_field.type}"
                )

        if table.num_rows == 0:
            metrics = ValidationMetrics(total_rows=0, stream_count=0)
            return ValidationReport(is_valid=True, metrics=metrics), table

        pydict = table.to_pydict()
        num_rows = table.num_rows

        seen_batch_identities: Set[Tuple[Any, ...]] = set()

        for i in range(num_rows):
            # A. ASCII-only source_order_key
            order_key = str(pydict["source_order_key"][i])
            if not _is_ascii(order_key):
                raise IntegrityViolationError(
                    f"Row {i}: source_order_key '{order_key}' contains non-ASCII characters"
                )

            # B. Actions, Sides & Delta Types
            action = str(pydict["action"][i]).upper()
            if action not in VALID_DELTA_ACTIONS:
                raise IntegrityViolationError(f"Row {i}: Invalid delta action '{action}'")

            side = str(pydict["side"][i]).upper()
            if side not in VALID_DELTA_SIDES:
                raise IntegrityViolationError(f"Row {i}: Invalid delta side '{side}'")

            delta_type = str(pydict["delta_type"][i]).upper()
            if delta_type not in VALID_DELTA_TYPES:
                raise IntegrityViolationError(f"Row {i}: Invalid delta_type '{delta_type}'")

            px = pydict["price"][i]
            sz = pydict["size"][i]
            order_id = pydict["order_id"][i]
            level_idx = pydict["level_idx"][i]

            # C. CLEAR Control Action Invariants
            if action == "CLEAR":
                if px is not None or sz is not None or level_idx is not None or order_id is not None:
                    raise IntegrityViolationError(
                        f"Row {i}: CLEAR action MUST have price=None, size=None, level_idx=None, order_id=None"
                    )
            else:
                # Non-CLEAR action
                if side == "ALL":
                    raise IntegrityViolationError(f"Row {i}: side='ALL' is only permitted for CLEAR action")

                if px is None:
                    raise IntegrityViolationError(f"Row {i}: Non-CLEAR action requires non-null price")
                if not isinstance(px, Decimal):
                    px = Decimal(str(px))
                if px <= Decimal("0") or not px.is_finite():
                    raise IntegrityViolationError(f"Row {i}: Price must be > 0 and finite, got {px}")
                validate_decimal128_bounds(px, "price")

                if action != "DELETE":
                    if sz is None:
                        raise IntegrityViolationError(f"Row {i}: {action} action requires non-null size")
                    if not isinstance(sz, Decimal):
                        sz = Decimal(str(sz))
                    if sz < Decimal("0") or not sz.is_finite():
                        raise IntegrityViolationError(f"Row {i}: Size must be >= 0 and finite, got {sz}")
                    validate_decimal128_bounds(sz, "size")

                # D. MBP vs MBO order_id and level_idx invariants
                if delta_type == "MBP":
                    if order_id is not None:
                        raise IntegrityViolationError(
                            f"Row {i}: MBP delta MUST have order_id=None, got '{order_id}'"
                        )
                elif delta_type == "MBO":
                    if order_id is None or str(order_id).strip() == "":
                        raise IntegrityViolationError(
                            f"Row {i}: MBO {action} delta MUST have non-null and non-empty order_id"
                        )

            # E. Delta Row Identity Duplicate Check
            row_id = (
                str(pydict["source_id"][i]),
                str(pydict["channel_id"][i]),
                str(pydict["symbol"][i]),
                pydict["trading_date"][i],
                int(pydict["source_seq_num"][i]),
                int(pydict["action_sub_idx"][i]),
            )

            if row_id in seen_batch_identities:
                raise IntegrityViolationError(
                    f"BATCH_DELTA_IDENTITY_DUPLICATE: Duplicate Delta Row Identity in batch: {row_id}"
                )
            seen_batch_identities.add(row_id)

            if existing_delta_identity_lookup and row_id in existing_delta_identity_lookup:
                raise IntegrityViolationError(
                    f"GLOBAL_DELTA_IDENTITY_DUPLICATE: Delta Row Identity already exists in storage: {row_id}"
                )

        metrics = ValidationMetrics(
            total_rows=num_rows,
            stream_count=1,
        )
        return ValidationReport(is_valid=True, metrics=metrics), table

