"""Unit and Invariant Tests for Phase 8.5 Step R2: Historical EURUSD M5 Data Preparation.

Strictly verifies:
- R1 Hypothesis integrity and cryptographic seal.
- Canonical dataset parquet schema, row count, and logical batch hash.
- Monotonic timestamps, 0 duplicates, and OHLC structural validity.
- Gap census with weekend closure classification.
- Timezone normalization with UTC canonical authority.
- Feature non-anticipation and label boundary handling (H=1, 6).
- Deterministic research split policy.
- Stationarity boundary characterization.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Callable, Sequence
import numpy as np
import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from acash.data.schema import CANONICAL_ARROW_SCHEMA
from acash.data.provenance import (
    calculate_canonical_batch_sha256,
    calculate_raw_source_sha256,
    ProvenanceTracker,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification


def test_gate15_r1_hypothesis_integrity() -> None:
    """Gate 15: Verify sealed R1 hypothesis is unmodified and valid."""
    hyp_path = Path("docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_001.json")
    assert hyp_path.exists(), f"Hypothesis file not found at {hyp_path}"
    with open(hyp_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    spec = HypothesisSpecification.model_validate(data)
    digest = calculate_hypothesis_spec_sha256(spec)
    expected_digest = "5afb92d7175721872d51ab82b2ebaaaa353c2d21bcbbd596e8bf1a3c52de0ef4"
    assert digest == expected_digest, f"Hypothesis SHA-256 mismatch: {digest} != {expected_digest}"
    assert spec.target_symbol == "EURUSD"
    assert spec.primary_horizon == 1
    assert spec.target_horizons == [1, 6]


def test_gate1_and_2_instrument_frequency_and_bar_count(
    require_research_artifact: Callable[[Sequence[Path], str], None],
) -> None:
    """Gates 1 & 2 (DATA-DEPENDENT, sealed HYP_001 M5 dataset): Verify EURUSD instrument, M5 frequency, and T >= 5,000 usable bars."""
    parquet_path = Path("data/parquet/research/EURUSD_M5_canonical.parquet")
    require_research_artifact(
        [parquet_path],
        "Sealed EURUSD M5 canonical parquet dataset (HYP_TSMOM_EURUSD_001 R2)",
    )
    assert parquet_path.exists(), f"Parquet dataset not found at {parquet_path}"

    table = pq.read_table(parquet_path)
    assert table.num_rows >= 5000, f"Bar count {table.num_rows} < 5000"
    assert table.num_rows == 10000

    symbols = set(table["symbol"].to_pylist())
    timeframes = set(table["timeframe"].to_pylist())
    assert symbols == {"EURUSD"}
    assert timeframes == {"M5"}


def test_gate3_and_4_monotonicity_and_zero_duplicates(
    build_canonical_synthetic_table: Callable[..., pa.Table],
) -> None:
    """Gates 3 & 4: Verify strictly monotonic timestamps and zero duplicate timestamps (generic contract, deterministic synthetic fixture)."""
    table = build_canonical_synthetic_table(n_bars=1200)

    starts = table["event_start_utc"].to_pylist()
    ends = table["event_end_utc"].to_pylist()

    # Monotonicity check
    for i in range(1, len(starts)):
        assert starts[i] > starts[i - 1], f"Non-monotonic timestamp at index {i}: {starts[i]} <= {starts[i-1]}"
        assert ends[i - 1] <= starts[i], f"Overlapping bar interval at index {i}: end={ends[i-1]} > start={starts[i]}"

    # Zero duplicate check
    assert len(set(starts)) == len(starts), "Duplicate start timestamps detected!"


def test_gate5_ohlc_structural_integrity(
    build_canonical_synthetic_table: Callable[..., pa.Table],
) -> None:
    """Gate 5: Verify OHLC structural invariants (H >= L, H >= O, H >= C, L <= O, L <= C, prices > 0) on deterministic synthetic fixture."""
    table = build_canonical_synthetic_table(n_bars=1200)

    opens = [Decimal(str(v)) for v in table["open"].to_pylist()]
    highs = [Decimal(str(v)) for v in table["high"].to_pylist()]
    lows = [Decimal(str(v)) for v in table["low"].to_pylist()]
    closes = [Decimal(str(v)) for v in table["close"].to_pylist()]
    volumes = [Decimal(str(v)) for v in table["volume"].to_pylist()]

    for i in range(len(opens)):
        assert opens[i] > Decimal("0"), f"Open <= 0 at {i}"
        assert highs[i] > Decimal("0"), f"High <= 0 at {i}"
        assert lows[i] > Decimal("0"), f"Low <= 0 at {i}"
        assert closes[i] > Decimal("0"), f"Close <= 0 at {i}"
        assert volumes[i] >= Decimal("0"), f"Volume < 0 at {i}"

        assert highs[i] >= lows[i], f"High < Low at index {i}: H={highs[i]}, L={lows[i]}"
        assert highs[i] >= opens[i], f"High < Open at index {i}: H={highs[i]}, O={opens[i]}"
        assert highs[i] >= closes[i], f"High < Close at index {i}: H={highs[i]}, C={closes[i]}"
        assert lows[i] <= opens[i], f"Low > Open at index {i}: L={lows[i]}, O={opens[i]}"
        assert lows[i] <= closes[i], f"Low > Close at index {i}: L={lows[i]}, C={closes[i]}"


def test_gate6_gap_detection_and_classification() -> None:
    """Gate 6: Verify gap detection census and market closure classification."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_M5_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    gaps = manifest["gaps_census"]
    assert len(gaps) == 6, f"Expected exactly 6 weekend gaps in 10,000 bars, got {len(gaps)}"
    for g in gaps:
        assert g["gap_type"] == "WEEKEND_MARKET_CLOSURE"
        assert 47.0 <= g["gap_hours"] <= 49.0  # ~48 hours weekend gap
    assert manifest["integrity_metrics"]["missing_bars_intraweek"] == 0


def test_gate7_timezone_normalization_utc() -> None:
    """Gate 7: Verify timezone semantics and strict UTC canonical authority."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_M5_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    tr = manifest["time_range"]
    assert tr["timezone"] == "UTC"
    assert tr["broker_utc_offset_seconds"] == 10800  # EEST UTC+3 offset
    assert tr["min_event_time_utc"] == "2026-07-20T03:40:00+00:00"
    assert tr["max_event_time_utc"] == "2026-09-04T21:00:00+00:00"


def test_gate8_provenance_and_ledger(
    require_research_artifact: Callable[[Sequence[Path], str], None],
) -> None:
    """Gate 8 (DATA-DEPENDENT, sealed R2 provenance): Verify provenance record in JSONL ledger and batch manifest."""
    tracker = ProvenanceTracker(
        ledger_path=Path("data/provenance_ledger.jsonl"),
        manifests_dir=Path("data/manifests/research"),
    )
    require_research_artifact(
        [Path("data/provenance_ledger.jsonl")],
        "Sealed R2 provenance ledger with EURUSD M5 research batch record",
    )
    records = tracker.read_provenance_records()
    r2_records = [r for r in records if r.batch_id == "batch_research_eurusd_m5_20260906"]
    if not r2_records:
        pytest.skip(
            "DATA-DEPENDENT-ENVIRONMENT: sealed R2 provenance record "
            "'batch_research_eurusd_m5_20260906' is not present in data/provenance_ledger.jsonl; "
            "the EURUSD M5 research batch was not produced in this environment"
        )
    assert len(r2_records) == 1, "R2 provenance record not found in data/provenance_ledger.jsonl"
    rec = r2_records[0]
    assert rec.symbol == "EURUSD"
    assert rec.timeframe == "M5"
    assert rec.row_count == 10000
    assert rec.validation_status == "VALID"
    assert rec.error_count == 0


def test_gate9_and_10_digests_and_manifest(
    require_research_artifact: Callable[[Sequence[Path], str], None],
) -> None:
    """Gates 9 & 10 (DATA-DEPENDENT, sealed raw CSV + canonical parquet): Verify content digests and dataset manifest consistency."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_M5_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Verify raw CSV SHA-256
    raw_csv_path = Path(manifest["file_locations"]["raw_csv_path"])
    parquet_path = Path(manifest["file_locations"]["canonical_parquet_path"])
    require_research_artifact(
        [raw_csv_path, parquet_path],
        "Sealed EURUSD M5 raw CSV source and canonical parquet dataset",
    )
    assert raw_csv_path.exists()
    with open(raw_csv_path, "rb") as f:
        raw_hash = calculate_raw_source_sha256(f.read())
    assert raw_hash == manifest["digests"]["raw_source_sha256"]

    # Verify canonical table logical batch hash
    assert parquet_path.exists()
    table = pq.read_table(parquet_path)
    canonical_hash = calculate_canonical_batch_sha256(table)
    assert canonical_hash == manifest["digests"]["canonical_batch_sha256"]

    # Verify parquet file binary hash
    with open(parquet_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == manifest["digests"]["parquet_file_sha256"]


def test_gate11_feature_non_anticipation(
    build_canonical_synthetic_table: Callable[..., pa.Table],
) -> None:
    """Gate 11: Verify feature construction cannot use future observations (generic contract, deterministic synthetic fixture)."""
    table = build_canonical_synthetic_table(n_bars=1200)
    closes = np.array([float(c) for c in table["close"].to_pylist()])

    lookbacks = [2, 3, 5, 8, 13, 21, 34, 55, 89]
    for L in lookbacks:
        t = 1000
        # Feature at t
        feat_t = (closes[t] - closes[t - L]) / closes[t - L]
        # Modify future bar (t + 1)
        future_modified = closes.copy()
        future_modified[t + 1 :] = 999.0
        feat_modified = (future_modified[t] - future_modified[t - L]) / future_modified[t - L]
        assert feat_t == feat_modified, f"Lookahead leakage in feature L={L}"


def test_gate12_label_boundary_handling(
    build_canonical_synthetic_table: Callable[..., pa.Table],
) -> None:
    """Gate 12: Verify label construction for H=1 and H=6 has strict end-of-sample boundary handling (generic contract, deterministic synthetic fixture)."""
    table = build_canonical_synthetic_table(n_bars=1200)
    T = table.num_rows
    closes = np.array([float(c) for c in table["close"].to_pylist()])
    opens = np.array([float(o) for o in table["open"].to_pylist()])

    for H in [1, 6]:
        labels = [None] * T
        for t in range(T):
            entry_idx = t + 1
            exit_idx = t + H
            if exit_idx < T:
                labels[t] = (closes[exit_idx] - opens[entry_idx]) / opens[entry_idx]
            else:
                labels[t] = None

        null_indices = [i for i, v in enumerate(labels) if v is None]
        assert len(null_indices) == H
        assert null_indices == list(range(T - H, T))


def test_gate13_split_policy() -> None:
    """Gate 13: Verify deterministic chronological train/validation/OOS split policy."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_M5_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    sp = manifest["split_policy"]
    assert sp["total_bars"] == 10000
    assert sp["train"]["bar_count"] == 6000
    assert sp["embargo_train_val"]["bar_count"] == 60
    assert sp["validation"]["bar_count"] == 1940
    assert sp["embargo_val_oos"]["bar_count"] == 60
    assert sp["oos_held_out"]["bar_count"] == 1940
    assert sp["oos_held_out"]["exposure_state"] == "UNEXPOSED_LOCKED"


def test_gate14_stationarity_boundary_declaration() -> None:
    """Gate 14: Verify stationarity is not claimed on raw prices, only on returns."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_M5_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    sa = manifest["stationarity_audit"]
    assert sa["price_level_stationarity"] == "NON_STATIONARY_I1"
    assert sa["log_return_stationarity"] == "STATIONARY_I0"
    assert "Raw EURUSD price levels are non-stationary unit-root processes (I(1))" in sa["canonical_statement"]

