"""Length-Prefixed Binary Serialization and Logical SHA-256 Hashing for Features (Phase 3C).

Strictly enforces:
- Invariant to Parquet chunking, row groups, codecs, or memory layouts.
- Invariant to row ordering (sorted by feature primary temporal key ASC).
- Cryptographic parameter configuration hashing.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import struct
from typing import Any, Dict, Optional, Union
import pyarrow as pa

from acash.data.features.schema import (
    CANONICAL_BOOK_FEATURES_SCHEMA,
    CANONICAL_TRADE_FEATURES_SCHEMA,
    BookFeaturesConfig,
    TradeFeaturesConfig,
)
from acash.data.orderbook.hashing import (
    NULL_INT32_SENTINEL,
    NULL_INT64_SENTINEL,
    NULL_UINT8_SENTINEL,
    NULL_UINT32_TAG,
    RECORD_SEPARATOR,
    serialize_bool_binary,
    serialize_date32_binary,
    serialize_decimal128_binary,
    serialize_string_binary,
    serialize_timestamp_ns_binary,
    serialize_timestamp_us_binary,
)
from acash.data.schema import DataContractError


def calculate_parameter_config_sha256(config: Union[TradeFeaturesConfig, BookFeaturesConfig, Dict[str, Any]]) -> str:
    """Calculate deterministic SHA-256 hash over canonical JSON parameter configuration."""
    if isinstance(config, (TradeFeaturesConfig, BookFeaturesConfig)):
        json_str = config.to_canonical_json()
    else:
        json_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def serialize_trade_features_row_binary(
    symbol: str,
    trading_date: Union[date, str],
    bar_start_utc: Union[datetime, int],
    bar_end_utc: Union[datetime, int],
    open_px: Union[Decimal, str, int, float],
    high_px: Union[Decimal, str, int, float],
    low_px: Union[Decimal, str, int, float],
    close_px: Union[Decimal, str, int, float],
    volume: Union[Decimal, str, int, float],
    buy_volume: Union[Decimal, str, int, float],
    sell_volume: Union[Decimal, str, int, float],
    delta: Union[Decimal, str, int, float],
    cvd: Union[Decimal, str, int, float],
    vwap: Optional[Union[Decimal, str, int, float]],
    vwap_std: Optional[Union[Decimal, str, int, float]],
    poc_price: Optional[Union[Decimal, str, int, float]],
    vah_price: Optional[Union[Decimal, str, int, float]],
    val_price: Optional[Union[Decimal, str, int, float]],
    has_stacked_buy_imbalance: bool,
    has_stacked_sell_imbalance: bool,
    is_absorption_bar: bool,
) -> bytes:
    """Serialize a single trade feature row into unambiguous length-prefixed bytes."""
    buf = bytearray()
    buf.extend(serialize_string_binary(symbol))
    buf.extend(serialize_date32_binary(trading_date))
    buf.extend(serialize_timestamp_ns_binary(bar_start_utc))
    buf.extend(serialize_timestamp_ns_binary(bar_end_utc))
    buf.extend(serialize_decimal128_binary(open_px))
    buf.extend(serialize_decimal128_binary(high_px))
    buf.extend(serialize_decimal128_binary(low_px))
    buf.extend(serialize_decimal128_binary(close_px))
    buf.extend(serialize_decimal128_binary(volume))
    buf.extend(serialize_decimal128_binary(buy_volume))
    buf.extend(serialize_decimal128_binary(sell_volume))
    buf.extend(serialize_decimal128_binary(delta))
    buf.extend(serialize_decimal128_binary(cvd))
    buf.extend(serialize_decimal128_binary(vwap))
    buf.extend(serialize_decimal128_binary(vwap_std))
    buf.extend(serialize_decimal128_binary(poc_price))
    buf.extend(serialize_decimal128_binary(vah_price))
    buf.extend(serialize_decimal128_binary(val_price))
    buf.extend(serialize_bool_binary(has_stacked_buy_imbalance))
    buf.extend(serialize_bool_binary(has_stacked_sell_imbalance))
    buf.extend(serialize_bool_binary(is_absorption_bar))
    buf.extend(RECORD_SEPARATOR)
    return bytes(buf)


def serialize_book_features_row_binary(
    symbol: str,
    trading_date: Union[date, str],
    exchange_time_utc: Union[datetime, int],
    knowledge_time_utc: Union[datetime, int],
    spread: Union[Decimal, str, int, float],
    micro_price: Optional[Union[Decimal, str, int, float]],
    obi_top1: Union[Decimal, str, int, float],
    obi_top5: Union[Decimal, str, int, float],
    obi_top10: Union[Decimal, str, int, float],
    total_bid_depth: Union[Decimal, str, int, float],
    total_ask_depth: Union[Decimal, str, int, float],
    is_crossed: bool,
) -> bytes:
    """Serialize a single book feature row into unambiguous length-prefixed bytes."""
    buf = bytearray()
    buf.extend(serialize_string_binary(symbol))
    buf.extend(serialize_date32_binary(trading_date))
    buf.extend(serialize_timestamp_ns_binary(exchange_time_utc))
    buf.extend(serialize_timestamp_us_binary(knowledge_time_utc))
    buf.extend(serialize_decimal128_binary(spread))
    buf.extend(serialize_decimal128_binary(micro_price))
    buf.extend(serialize_decimal128_binary(obi_top1))
    buf.extend(serialize_decimal128_binary(obi_top5))
    buf.extend(serialize_decimal128_binary(obi_top10))
    buf.extend(serialize_decimal128_binary(total_bid_depth))
    buf.extend(serialize_decimal128_binary(total_ask_depth))
    buf.extend(serialize_bool_binary(is_crossed))
    buf.extend(RECORD_SEPARATOR)
    return bytes(buf)


def calculate_canonical_trade_features_sha256(table: pa.Table) -> str:
    """Compute logical, deterministic SHA-256 fingerprint for a trade features table."""
    for field in CANONICAL_TRADE_FEATURES_SCHEMA:
        if field.name not in table.column_names:
            raise DataContractError(f"Missing column in Trade Features table: {field.name}")

    if table.num_rows == 0:
        return hashlib.sha256(b"CANONICAL_TRADE_FEATURES_EMPTY_TABLE_V1").hexdigest()

    # Sort table by Primary Temporal Key: (symbol, trading_date, bar_start_utc)
    sort_indices = pa.compute.sort_indices(
        table,
        sort_keys=[("symbol", "ascending"), ("trading_date", "ascending"), ("bar_start_utc", "ascending")],
    )
    sorted_table = table.take(sort_indices)

    hasher = hashlib.sha256()
    hasher.update(b"ACASH_CANONICAL_TRADE_FEATURES_V1.1\n")

    pydict = sorted_table.to_pydict()
    for i in range(sorted_table.num_rows):
        row_bytes = serialize_trade_features_row_binary(
            symbol=str(pydict["symbol"][i]),
            trading_date=pydict["trading_date"][i],
            bar_start_utc=pydict["bar_start_utc"][i],
            bar_end_utc=pydict["bar_end_utc"][i],
            open_px=pydict["open"][i],
            high_px=pydict["high"][i],
            low_px=pydict["low"][i],
            close_px=pydict["close"][i],
            volume=pydict["volume"][i],
            buy_volume=pydict["buy_volume"][i],
            sell_volume=pydict["sell_volume"][i],
            delta=pydict["delta"][i],
            cvd=pydict["cvd"][i],
            vwap=pydict["vwap"][i],
            vwap_std=pydict["vwap_std"][i],
            poc_price=pydict["poc_price"][i],
            vah_price=pydict["vah_price"][i],
            val_price=pydict["val_price"][i],
            has_stacked_buy_imbalance=bool(pydict["has_stacked_buy_imbalance"][i]),
            has_stacked_sell_imbalance=bool(pydict["has_stacked_sell_imbalance"][i]),
            is_absorption_bar=bool(pydict["is_absorption_bar"][i]),
        )
        hasher.update(row_bytes)

    return hasher.hexdigest()


def calculate_canonical_book_features_sha256(table: pa.Table) -> str:
    """Compute logical, deterministic SHA-256 fingerprint for a book features table."""
    for field in CANONICAL_BOOK_FEATURES_SCHEMA:
        if field.name not in table.column_names:
            raise DataContractError(f"Missing column in Book Features table: {field.name}")

    if table.num_rows == 0:
        return hashlib.sha256(b"CANONICAL_BOOK_FEATURES_EMPTY_TABLE_V1").hexdigest()

    # Sort table by Primary Temporal Key: (symbol, trading_date, exchange_time_utc)
    sort_indices = pa.compute.sort_indices(
        table,
        sort_keys=[("symbol", "ascending"), ("trading_date", "ascending"), ("exchange_time_utc", "ascending")],
    )
    sorted_table = table.take(sort_indices)

    hasher = hashlib.sha256()
    hasher.update(b"ACASH_CANONICAL_BOOK_FEATURES_V1.1\n")

    pydict = sorted_table.to_pydict()
    for i in range(sorted_table.num_rows):
        row_bytes = serialize_book_features_row_binary(
            symbol=str(pydict["symbol"][i]),
            trading_date=pydict["trading_date"][i],
            exchange_time_utc=pydict["exchange_time_utc"][i],
            knowledge_time_utc=pydict["knowledge_time_utc"][i],
            spread=pydict["spread"][i],
            micro_price=pydict["micro_price"][i],
            obi_top1=pydict["obi_top1"][i],
            obi_top5=pydict["obi_top5"][i],
            obi_top10=pydict["obi_top10"][i],
            total_bid_depth=pydict["total_bid_depth"][i],
            total_ask_depth=pydict["total_ask_depth"][i],
            is_crossed=bool(pydict["is_crossed"][i]),
        )
        hasher.update(row_bytes)

    return hasher.hexdigest()
