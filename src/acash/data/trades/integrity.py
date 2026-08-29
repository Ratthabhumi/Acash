"""Data Integrity Validator for the ACASH Trades Domain (Phase 3A).

Enforces:
- Schema type conformation to CANONICAL_TRADES_SCHEMA (timestamp[ns, tz=UTC], Decimal128(38,18)).
- Price and size positive finite Decimal128 bounds.
- Valid enumerated aggressor_side ("BUY", "SELL", "UNKNOWN") and trade_condition ("REGULAR", "SPREAD", "BLOCK", "AUCTION").
- Nullable trade_id preservation (never invent synthetic exchange identifiers).
- Deterministic match_sub_idx handling for multi-match messages.
- Channel sequence gap & discontinuity classification (EXPECTED_RESET, PACKET_GAP, RECOVERY_DISCONTINUITY, UNKNOWN_DISCONTINUITY).
- Intra-batch and global Trade Row Identity duplicate prevention.
- Clock skew sanity warnings without dropping raw records.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field

from acash.data.schema import (
    DataContractError,
    DomainValidationError,
    IntegrityViolationError,
    validate_decimal128_bounds,
)
from acash.data.trades.schema import (
    CANONICAL_TRADES_SCHEMA,
    VALID_AGGRESSOR_SIDES,
    VALID_TRADE_CONDITIONS,
)


class SequenceDiscontinuityType(str, Enum):
    """Explicit classification for sequence discontinuities."""
    EXPECTED_RESET = "EXPECTED_RESET"
    PACKET_GAP = "PACKET_GAP"
    RECOVERY_DISCONTINUITY = "RECOVERY_DISCONTINUITY"
    UNKNOWN_DISCONTINUITY = "UNKNOWN_DISCONTINUITY"


class TradeValidationErrorRecord(BaseModel):
    """Fatal validation error record for trade rows."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    row_index: int
    field: str
    error_type: str
    message: str


class TradeValidationAnomalyRecord(BaseModel):
    """Preserved anomaly/warning record for trade streams."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    stream_key: str
    anomaly_type: str
    message: str
    affected_seq_num: Optional[int] = None


class TradeValidationMetrics(BaseModel):
    """Aggregate metrics of the trade validation pass."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_rows: int
    valid_rows: int
    error_count: int
    warning_count: int
    total_trades_volume: Decimal = Field(default=Decimal("0"))
    min_exchange_time_utc: Optional[str] = None
    max_exchange_time_utc: Optional[str] = None


class TradeValidationReport(BaseModel):
    """Complete validation report for an incoming trades dataset."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_valid: bool
    status: str
    metrics: TradeValidationMetrics
    errors: List[TradeValidationErrorRecord]
    anomalies: List[TradeValidationAnomalyRecord]


class TradesIntegrityValidator:
    """Validator enforcing strict data contracts and domain integrity for trade streams."""

    def __init__(self, max_clock_skew_ms: int = 5000) -> None:
        self.max_clock_skew_ms = max_clock_skew_ms

    def validate_table(

        self,
        table: pa.Table,
        declared_resets: Optional[Set[Tuple[str, str, str, date]]] = None,
        existing_trade_identity_lookup: Optional[Dict[Tuple[str, str, str, date, int, int], bool]] = None,
    ) -> Tuple[TradeValidationReport, pa.Table]:
        """Validate an incoming PyArrow Table against Canonical Trades data contracts.

        Args:
            table: Incoming PyArrow table with raw/source trade columns.
            declared_resets: Optional set of (source_id, channel_id, symbol, trading_date) streams with declared resets.
            existing_trade_identity_lookup: Optional lookup of already-persisted Trade Row Identities for global deduplication.

        Returns:
            Tuple of (TradeValidationReport, validated_canonical_table).

        Raises:
            IntegrityViolationError: If fatal errors exist (e.g. schema mismatch, duplicates, invalid numerics).
        """
        declared_reset_set = declared_resets or set()
        errors: List[TradeValidationErrorRecord] = []
        anomalies: List[TradeValidationAnomalyRecord] = []

        # 1. Schema Conformance Check
        for field in CANONICAL_TRADES_SCHEMA:
            if field.name not in table.column_names:
                raise DataContractError(f"Missing column in Trades table: {field.name}")

        if table.num_rows == 0:
            metrics = TradeValidationMetrics(
                total_rows=0,
                valid_rows=0,
                error_count=0,
                warning_count=0,
            )
            report = TradeValidationReport(
                is_valid=True,
                status="VALID",
                metrics=metrics,
                errors=[],
                anomalies=[],
            )
            empty_table = pa.Table.from_batches([], schema=CANONICAL_TRADES_SCHEMA)
            return report, empty_table


        # 1. Cast / Conform to CANONICAL_TRADES_SCHEMA
        try:
            canonical_table = table.cast(CANONICAL_TRADES_SCHEMA)
        except Exception as exc:
            raise IntegrityViolationError(
                f"Table schema cannot be cast to CANONICAL_TRADES_SCHEMA: {exc}"
            ) from exc

        # Extract columns
        source_ids = canonical_table["source_id"].to_pylist()
        channel_ids = canonical_table["channel_id"].to_pylist()
        symbols = canonical_table["symbol"].to_pylist()
        trading_dates = canonical_table["trading_date"].to_pylist()
        exchange_times = canonical_table["exchange_time_utc"].to_pylist()
        feed_times = canonical_table["feed_time_utc"].to_pylist()
        knowledge_times = canonical_table["knowledge_time_utc"].to_pylist()
        source_seq_nums = canonical_table["source_seq_num"].to_pylist()
        trade_ids = canonical_table["trade_id"].to_pylist()
        match_sub_indices = canonical_table["match_sub_idx"].to_pylist()
        prices = canonical_table["price"].to_pylist()
        sizes = canonical_table["size"].to_pylist()
        aggressor_sides = canonical_table["aggressor_side"].to_pylist()
        trade_conditions = canonical_table["trade_condition"].to_pylist()

        num_rows = canonical_table.num_rows
        seen_batch_identities: Set[Tuple[str, str, str, date, int, int]] = set()
        total_volume = Decimal("0")

        # 2. Row-level domain checks
        for i in range(num_rows):
            # Check price
            price = prices[i]
            if price is None:
                errors.append(TradeValidationErrorRecord(
                    row_index=i, field="price", error_type="NULL_PRICE", message="Price cannot be null."
                ))
            else:
                try:
                    validate_decimal128_bounds(Decimal(str(price)), "price")
                    if Decimal(str(price)) <= Decimal("0"):
                        errors.append(TradeValidationErrorRecord(
                            row_index=i, field="price", error_type="NON_POSITIVE_PRICE", message=f"Price must be > 0, got {price}."
                        ))
                except DomainValidationError as d_err:
                    errors.append(TradeValidationErrorRecord(
                        row_index=i, field="price", error_type="INVALID_DECIMAL_BOUNDS", message=str(d_err)
                    ))

            # Check size
            size = sizes[i]
            if size is None:
                errors.append(TradeValidationErrorRecord(
                    row_index=i, field="size", error_type="NULL_SIZE", message="Size cannot be null."
                ))
            else:
                try:
                    validate_decimal128_bounds(Decimal(str(size)), "size")
                    if Decimal(str(size)) <= Decimal("0"):
                        errors.append(TradeValidationErrorRecord(
                            row_index=i, field="size", error_type="NON_POSITIVE_SIZE", message=f"Size must be > 0, got {size}."
                        ))
                    else:
                        total_volume += Decimal(str(size))
                except DomainValidationError as d_err:
                    errors.append(TradeValidationErrorRecord(
                        row_index=i, field="size", error_type="INVALID_DECIMAL_BOUNDS", message=str(d_err)
                    ))

            # Check aggressor_side
            side = aggressor_sides[i]
            if side not in VALID_AGGRESSOR_SIDES:
                errors.append(TradeValidationErrorRecord(
                    row_index=i, field="aggressor_side", error_type="INVALID_AGGRESSOR_SIDE",
                    message=f"aggressor_side '{side}' not in {sorted(VALID_AGGRESSOR_SIDES)}."
                ))

            # Check trade_condition
            cond = trade_conditions[i]
            if cond not in VALID_TRADE_CONDITIONS:
                errors.append(TradeValidationErrorRecord(
                    row_index=i, field="trade_condition", error_type="INVALID_TRADE_CONDITION",
                    message=f"trade_condition '{cond}' not in {sorted(VALID_TRADE_CONDITIONS)}."
                ))

            # Check match_sub_idx
            sub_idx = match_sub_indices[i]
            if sub_idx is None or sub_idx < 0:
                errors.append(TradeValidationErrorRecord(
                    row_index=i, field="match_sub_idx", error_type="INVALID_MATCH_SUB_IDX",
                    message=f"match_sub_idx must be >= 0, got {sub_idx}."
                ))

            # Check Trade Row Identity uniqueness
            t_date = trading_dates[i]
            t_date_val = t_date if isinstance(t_date, date) else date.fromisoformat(str(t_date))
            identity_key = (
                str(source_ids[i]),
                str(channel_ids[i]),
                str(symbols[i]),
                t_date_val,
                int(source_seq_nums[i]),
                int(match_sub_indices[i]),
            )

            # Intra-batch duplicate check
            if identity_key in seen_batch_identities:
                errors.append(TradeValidationErrorRecord(
                    row_index=i, field="identity", error_type="BATCH_TRADE_IDENTITY_DUPLICATE",
                    message=f"Duplicate Trade Row Identity within batch: {identity_key}"
                ))
            else:
                seen_batch_identities.add(identity_key)

            # Global duplicate check against existing canonical storage
            if existing_trade_identity_lookup and identity_key in existing_trade_identity_lookup:
                errors.append(TradeValidationErrorRecord(
                    row_index=i, field="identity", error_type="GLOBAL_TRADE_IDENTITY_DUPLICATE",
                    message=f"Trade Row Identity already persisted in canonical storage: {identity_key}"
                ))

            # Clock skew check
            ex_time = exchange_times[i]
            know_time = knowledge_times[i]
            if isinstance(ex_time, datetime) and isinstance(know_time, datetime):
                dt_ex = ex_time.replace(tzinfo=timezone.utc) if ex_time.tzinfo is None else ex_time.astimezone(timezone.utc)
                dt_know = know_time.replace(tzinfo=timezone.utc) if know_time.tzinfo is None else know_time.astimezone(timezone.utc)
                diff_ms = abs((dt_ex.timestamp() - dt_know.timestamp()) * 1000)
                if diff_ms > self.max_clock_skew_ms:
                    anomalies.append(TradeValidationAnomalyRecord(
                        stream_key=f"{source_ids[i]}:{channel_ids[i]}:{symbols[i]}",
                        anomaly_type="CLOCK_SKEW_WARNING",
                        message=f"Clock skew between exchange_time and knowledge_time is {diff_ms:.1f}ms (> {self.max_clock_skew_ms}ms).",
                        affected_seq_num=source_seq_nums[i],
                    ))

        # 3. Stream-level sequence continuity checks per channel scope
        # Group row indices by (source_id, channel_id, symbol, trading_date)
        streams: Dict[Tuple[str, str, str, date], List[int]] = {}
        for i in range(num_rows):
            t_date = trading_dates[i]
            t_date_val = t_date if isinstance(t_date, date) else date.fromisoformat(str(t_date))
            s_key = (str(source_ids[i]), str(channel_ids[i]), str(symbols[i]), t_date_val)
            streams.setdefault(s_key, []).append(i)

        for stream_key, indices in streams.items():
            # Sort stream indices by (exchange_time_utc, source_seq_num, match_sub_idx)
            sorted_indices = sorted(
                indices,
                key=lambda idx: (exchange_times[idx], source_seq_nums[idx], match_sub_indices[idx])
            )
            last_seq = source_seq_nums[sorted_indices[0]]

            for idx in sorted_indices[1:]:
                curr_seq = source_seq_nums[idx]
                if curr_seq > last_seq + 1:
                    # Packet gap detected on active channel
                    anomalies.append(TradeValidationAnomalyRecord(
                        stream_key=f"{stream_key[0]}:{stream_key[1]}:{stream_key[2]}",
                        anomaly_type="PACKET_GAP_DETECTED",
                        message=f"Sequence gap detected on channel {stream_key[1]}: jumped from {last_seq} to {curr_seq}.",
                        affected_seq_num=curr_seq,
                    ))
                elif curr_seq < last_seq:
                    # Sequence decreased
                    if stream_key in declared_reset_set:
                        anomalies.append(TradeValidationAnomalyRecord(
                            stream_key=f"{stream_key[0]}:{stream_key[1]}:{stream_key[2]}",
                            anomaly_type="EXPECTED_RESET",
                            message=f"Declared sequence reset accepted from {last_seq} to {curr_seq}.",
                            affected_seq_num=curr_seq,
                        ))
                    else:
                        anomalies.append(TradeValidationAnomalyRecord(
                            stream_key=f"{stream_key[0]}:{stream_key[1]}:{stream_key[2]}",
                            anomaly_type="UNKNOWN_DISCONTINUITY",
                            message=f"Undeclared sequence drop from {last_seq} to {curr_seq}.",
                            affected_seq_num=curr_seq,
                        ))
                last_seq = curr_seq

        # 4. Compile metrics & report
        min_ex_str = None
        max_ex_str = None
        if exchange_times:
            sorted_ex = sorted([t for t in exchange_times if t is not None])
            if sorted_ex:
                min_ex_str = sorted_ex[0].isoformat() if hasattr(sorted_ex[0], "isoformat") else str(sorted_ex[0])
                max_ex_str = sorted_ex[-1].isoformat() if hasattr(sorted_ex[-1], "isoformat") else str(sorted_ex[-1])

        is_valid = len(errors) == 0
        status = "VALID" if is_valid and len(anomalies) == 0 else ("VALID_WITH_WARNINGS" if is_valid else "INVALID")

        metrics = TradeValidationMetrics(
            total_rows=num_rows,
            valid_rows=num_rows - len(errors),
            error_count=len(errors),
            warning_count=len(anomalies),
            total_trades_volume=total_volume,
            min_exchange_time_utc=min_ex_str,
            max_exchange_time_utc=max_ex_str,
        )

        report = TradeValidationReport(
            is_valid=is_valid,
            status=status,
            metrics=metrics,
            errors=errors,
            anomalies=anomalies,
        )

        if not is_valid:
            error_summary = "; ".join(f"[row {e.row_index}] {e.error_type}: {e.message}" for e in errors[:5])
            if len(errors) > 5:
                error_summary += f" ... ({len(errors) - 5} more errors)"
            raise IntegrityViolationError(f"Trade validation failed with {len(errors)} error(s): {error_summary}")

        return report, canonical_table

    validate_trades_table = validate_table

