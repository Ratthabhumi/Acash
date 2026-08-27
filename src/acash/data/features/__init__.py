"""Canonical Microstructure Feature Engine Subsystem for ACASH (Phase 3C).

Provides:
- CANONICAL_TRADE_FEATURES_SCHEMA & CANONICAL_BOOK_FEATURES_SCHEMA
- TradeFeaturesConfig & BookFeaturesConfig
- FeatureManifest with explicit temporal lineage
- Pure mathematical microstructure functions:
  - calculate_session_vwap_and_dispersion
  - calculate_volume_profile
  - calculate_footprint_analytics
  - calculate_book_microstructure
  - compute_trade_features_table
  - compute_book_features_table
- FeatureStorageEngine with Parquet partitioning & DuckDB PIT queries
- FeatureExtractionPipeline with 4-way anti-leakage guarantees
"""

from acash.data.features.engine import (
    calculate_book_microstructure,
    calculate_footprint_analytics,
    calculate_session_vwap_and_dispersion,
    calculate_volume_profile,
    compute_book_features_table,
    compute_trade_features_table,
)
from acash.data.features.hashing import (
    calculate_canonical_book_features_sha256,
    calculate_canonical_trade_features_sha256,
    calculate_parameter_config_sha256,
    serialize_book_features_row_binary,
    serialize_trade_features_row_binary,
)
from acash.data.features.pipeline import FeatureExtractionPipeline
from acash.data.features.schema import (
    CANONICAL_BOOK_FEATURES_SCHEMA,
    CANONICAL_TRADE_FEATURES_SCHEMA,
    BookFeaturesConfig,
    FeatureManifest,
    TradeFeaturesConfig,
)
from acash.data.features.storage import FeatureStorageEngine

__all__ = [
    # Schemas & Models
    "CANONICAL_TRADE_FEATURES_SCHEMA",
    "CANONICAL_BOOK_FEATURES_SCHEMA",
    "TradeFeaturesConfig",
    "BookFeaturesConfig",
    "FeatureManifest",
    # Hashing & Binary Serialization
    "calculate_parameter_config_sha256",
    "serialize_trade_features_row_binary",
    "serialize_book_features_row_binary",
    "calculate_canonical_trade_features_sha256",
    "calculate_canonical_book_features_sha256",
    # Mathematical Core Engine
    "calculate_session_vwap_and_dispersion",
    "calculate_volume_profile",
    "calculate_footprint_analytics",
    "calculate_book_microstructure",
    "compute_trade_features_table",
    "compute_book_features_table",
    # Storage & Pipeline
    "FeatureStorageEngine",
    "FeatureExtractionPipeline",
]
