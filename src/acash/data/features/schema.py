"""Canonical PyArrow schemas, Pydantic configuration models, and FeatureManifest for the ACASH Microstructure Feature Engine (Phase 3C).

Strictly enforces:
- CANONICAL_TRADE_FEATURES_SCHEMA: Trade-derived microstructure signals (Delta, CVD, VWAP, Volume Profile, Imbalances).
- CANONICAL_BOOK_FEATURES_SCHEMA: Book-derived microstructure signals (Spread, Micro-Price, OBI Top-1/5/10, Depth).
- FeatureManifest with explicit temporal lineage and cryptographic provenance.
- Zero trading strategy / signal logic.
"""

from datetime import date, datetime
from decimal import Decimal
import json
from typing import Any, Dict, Final, List, Optional
import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Feature Parameter Configuration Models
# ---------------------------------------------------------------------------


class TradeFeaturesConfig(BaseModel):
    """Configurable research parameters for Trade Flow & Volume features."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    value_area_pct: Decimal = Field(default=Decimal("0.70"), ge=Decimal("0.01"), le=Decimal("1.00"))
    imbalance_ratio: Decimal = Field(default=Decimal("3.00"), ge=Decimal("1.00"))
    min_imbalance_volume_diff: Decimal = Field(default=Decimal("10.0"), ge=Decimal("0.0"))
    stacked_imbalance_min_levels: int = Field(default=3, ge=2)
    absorption_volume_multiplier: Decimal = Field(default=Decimal("2.5"), ge=Decimal("1.0"))
    absorption_rejection_ratio: Decimal = Field(default=Decimal("0.30"), ge=Decimal("0.0"), le=Decimal("1.0"))
    bar_interval_seconds: int = Field(default=60, ge=1)
    tick_size: Decimal = Field(default=Decimal("0.25"), gt=Decimal("0.0"))

    def to_canonical_json(self) -> str:
        """Serialize configuration parameters into canonical sorted JSON string."""
        d = {
            "value_area_pct": f"{self.value_area_pct:.4f}",
            "imbalance_ratio": f"{self.imbalance_ratio:.4f}",
            "min_imbalance_volume_diff": f"{self.min_imbalance_volume_diff:.4f}",
            "stacked_imbalance_min_levels": self.stacked_imbalance_min_levels,
            "absorption_volume_multiplier": f"{self.absorption_volume_multiplier:.4f}",
            "absorption_rejection_ratio": f"{self.absorption_rejection_ratio:.4f}",
            "bar_interval_seconds": self.bar_interval_seconds,
            "tick_size": f"{self.tick_size:.4f}",
        }
        return json.dumps(d, sort_keys=True)



class BookFeaturesConfig(BaseModel):
    """Configurable research parameters for Order Book Microstructure features."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    obi_depth_levels: List[int] = Field(default_factory=lambda: [1, 5, 10])
    use_linear_depth_weights: bool = Field(default=True)
    sampling_interval_ms: int = Field(default=1000, ge=10)

    def to_canonical_json(self) -> str:
        """Serialize configuration parameters into canonical sorted JSON string."""
        d = {
            "obi_depth_levels": sorted(self.obi_depth_levels),
            "use_linear_depth_weights": self.use_linear_depth_weights,
            "sampling_interval_ms": self.sampling_interval_ms,
        }
        return json.dumps(d, sort_keys=True)


# ---------------------------------------------------------------------------
# Feature Lineage Manifest
# ---------------------------------------------------------------------------


class FeatureManifest(BaseModel):
    """Cryptographically verified Feature Manifest documenting temporal lineage and provenance."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    feature_set_name: str
    feature_definition_version: str
    symbol: str
    trading_date: str

    # Explicit Temporal Lineage Coordinates
    decision_time_utc: str
    knowledge_cutoff_utc: str
    input_event_start_utc: str
    input_event_end_utc: str

    # Cryptographic Provenance Hashes
    input_trades_sha256: Optional[str]
    input_book_sha256: Optional[str]
    parameter_config_sha256: str
    parameter_config_json: str
    software_version: str
    feature_output_sha256: str

    row_count: int
    computed_at_utc: str


# ---------------------------------------------------------------------------
# PyArrow Canonical Feature Schemas
# ---------------------------------------------------------------------------

CANONICAL_TRADE_FEATURES_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("bar_start_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("bar_end_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("open", pa.decimal128(38, 18), nullable=False),
    pa.field("high", pa.decimal128(38, 18), nullable=False),
    pa.field("low", pa.decimal128(38, 18), nullable=False),
    pa.field("close", pa.decimal128(38, 18), nullable=False),
    pa.field("volume", pa.decimal128(38, 18), nullable=False),
    pa.field("buy_volume", pa.decimal128(38, 18), nullable=False),
    pa.field("sell_volume", pa.decimal128(38, 18), nullable=False),
    pa.field("delta", pa.decimal128(38, 18), nullable=False),
    pa.field("cvd", pa.decimal128(38, 18), nullable=False),
    pa.field("vwap", pa.decimal128(38, 18), nullable=True),  # Nullable when total volume == 0
    pa.field("vwap_std", pa.decimal128(38, 18), nullable=True),  # Nullable when total volume == 0
    pa.field("poc_price", pa.decimal128(38, 18), nullable=True),  # Nullable when total volume == 0
    pa.field("vah_price", pa.decimal128(38, 18), nullable=True),  # Nullable when total volume == 0
    pa.field("val_price", pa.decimal128(38, 18), nullable=True),  # Nullable when total volume == 0
    pa.field("has_stacked_buy_imbalance", pa.bool_(), nullable=False),
    pa.field("has_stacked_sell_imbalance", pa.bool_(), nullable=False),
    pa.field("is_absorption_bar", pa.bool_(), nullable=False),
])

CANONICAL_BOOK_FEATURES_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("spread", pa.decimal128(38, 18), nullable=False),
    pa.field("micro_price", pa.decimal128(38, 18), nullable=True),  # Nullable when total depth == 0
    pa.field("obi_top1", pa.decimal128(38, 18), nullable=False),
    pa.field("obi_top5", pa.decimal128(38, 18), nullable=False),
    pa.field("obi_top10", pa.decimal128(38, 18), nullable=False),
    pa.field("total_bid_depth", pa.decimal128(38, 18), nullable=False),
    pa.field("total_ask_depth", pa.decimal128(38, 18), nullable=False),
    pa.field("is_crossed", pa.bool_(), nullable=False),
])
