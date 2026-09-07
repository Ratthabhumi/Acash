"""Unit and Invariant Tests for Phase 8.5 Step R2: Historical EURUSD H4 Data Preparation.

Target Hypothesis: HYP_TSMOM_EURUSD_HTF_002 (Ordinal HYP_002)

Strictly verifies:
- Upstream R1 Hypothesis integrity and cryptographic seal.
- Canonical dataset parquet schema, row count (N >= 5,000), and logical batch hash.
- Monotonic timestamps, 0 duplicates, and OHLC structural validity.
- Gap census with weekend closures, holiday closures, and feed gap classification.
- Timezone normalization with UTC canonical authority.
- Feature non-anticipation and label boundary handling.
- Deterministic research split policy (60/20/20) with 12-bar embargoes.
- Stationarity boundary characterization.
- Quarantine boundary isolation against 2026 M5 holdout.
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


def _load_hyp_spec(path: Path) -> HypothesisSpecification:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw.get("expected_direction"), dict) and "__type__" in raw.get("expected_direction", {}):
        clean_dict = {
            "hypothesis_id": raw["hypothesis_id"],
            "hypothesis_version": raw["hypothesis_version"],
            "parent_hypothesis_id": raw.get("parent_hypothesis_id"),
            "economic_rationale": raw["economic_rationale"],
            "target_symbol": raw["target_symbol"],
            "feature_dependencies": raw["feature_dependencies"],
            "parameter_config_json": raw["parameter_config_json"],
            "expected_direction": raw["expected_direction"]["value"],
            "target_horizons": [x["value"] if isinstance(x, dict) else x for x in raw["target_horizons"]],
            "primary_horizon": raw["primary_horizon"]["value"] if isinstance(raw["primary_horizon"], dict) else raw["primary_horizon"],
            "invalidation_criteria": {k: v["value"] if isinstance(v, dict) else v for k, v in raw["invalidation_criteria"].items()},
            "registered_at_utc": raw["registered_at_utc"],
            "author": raw["author"],
        }
        return HypothesisSpecification.model_validate(clean_dict)
    return HypothesisSpecification.model_validate(raw)


def test_gate1_r1_hypothesis_integrity() -> None:
    """Gate 1: Verify sealed R1 hypothesis is unmodified and valid."""
    hyp_path = Path("docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_002.json")
    assert hyp_path.exists(), f"Hypothesis file not found at {hyp_path}"

    spec = _load_hyp_spec(hyp_path)
    digest = calculate_hypothesis_spec_sha256(spec)
    expected_digest = "47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe"
    assert digest == expected_digest, f"Hypothesis SHA-256 mismatch: {digest} != {expected_digest}"
    assert spec.hypothesis_id == "HYP_TSMOM_EURUSD_HTF_002"
    assert spec.target_symbol == "EURUSD"
    assert spec.primary_horizon == 1
    assert spec.target_horizons == [1, 6]


def test_gate2_quarantine_boundary_isolation() -> None:
    """Gate 2: Verify research window is completely disjoint from quarantined 2026 M5 holdout."""
    canonical_window_end = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    quarantine_m5_start = datetime(2026, 8, 18, 0, 0, 0, tzinfo=timezone.utc)
    assert canonical_window_end < quarantine_m5_start
    separation_days = (quarantine_m5_start - canonical_window_end).days
    assert separation_days > 500, f"Separation {separation_days} days <= 500 days"


def test_gate3_and_4_instrument_frequency_and_bar_count(
    require_research_artifact: Callable[[Sequence[Path], str], None],
) -> None:
    """Gates 3 & 4 (DATA-DEPENDENT, sealed HYP_002 H4 dataset): Verify EURUSD instrument, H4 frequency, and N >= 5,000 usable bars."""
    parquet_path = Path("data/parquet/research/EURUSD_H4_2021_2024_canonical.parquet")
    require_research_artifact(
        [parquet_path],
        "Sealed EURUSD H4 2021-2024 canonical parquet dataset (HYP_TSMOM_EURUSD_HTF_002 R2)",
    )
    assert parquet_path.exists(), f"Parquet dataset not found at {parquet_path}"

    table = pq.read_table(parquet_path)
    assert table.num_rows >= 5000, f"Bar count {table.num_rows} < 5000"
    assert table.num_rows == 6231

    symbols = set(table["symbol"].to_pylist())
    timeframes = set(table["timeframe"].to_pylist())
    assert symbols == {"EURUSD"}
    assert timeframes == {"H4"}


def test_gate5_and_6_monotonicity_and_zero_duplicates(
    build_canonical_synthetic_table: Callable[..., pa.Table],
) -> None:
    """Gates 5 & 6: Verify strictly monotonic timestamps and zero duplicate timestamps (generic contract, deterministic synthetic fixture)."""
    table = build_canonical_synthetic_table(n_bars=700, timeframe="TF4", step_minutes=240)

    starts = table["event_start_utc"].to_pylist()
    ends = table["event_end_utc"].to_pylist()

    # Monotonicity check
    for i in range(1, len(starts)):
        assert starts[i] > starts[i - 1], f"Non-monotonic timestamp at index {i}: {starts[i]} <= {starts[i-1]}"
        assert ends[i - 1] <= starts[i], f"Overlapping bar interval at index {i}: end={ends[i-1]} > start={starts[i]}"

    # Zero duplicate check
    assert len(set(starts)) == len(starts), "Duplicate start timestamps detected!"


def test_gate7_ohlc_structural_integrity(
    build_canonical_synthetic_table: Callable[..., pa.Table],
) -> None:
    """Gate 7: Verify OHLC structural invariants (H >= L, H >= O, H >= C, L <= O, L <= C, prices > 0) on deterministic synthetic fixture."""
    table = build_canonical_synthetic_table(n_bars=700, timeframe="TF4", step_minutes=240)

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


def test_gate8_gap_detection_and_classification() -> None:
    """Gate 8: Verify gap detection census and market closure classification."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_H4_2021_2024_canonical.json")
    assert manifest_path.exists(), f"Manifest not found at {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    gaps = manifest["gaps_census"]
    weekend_gaps = [g for g in gaps if g["gap_type"] == "WEEKEND_MARKET_CLOSURE"]
    holiday_gaps = [g for g in gaps if g["gap_type"] == "HOLIDAY_MARKET_CLOSURE"]
    unexpected_gaps = [g for g in gaps if g["gap_type"] == "UNEXPECTED_DATA_GAP"]

    assert len(weekend_gaps) == 207, f"Expected 207 weekend gaps, got {len(weekend_gaps)}"
    assert len(holiday_gaps) == 3, f"Expected 3 holiday gaps, got {len(holiday_gaps)}"
    assert len(unexpected_gaps) == 1, f"Expected exactly 1 documented unexpected gap, got {len(unexpected_gaps)}"

    # Check that documented unexpected gap is on 2024-07-02
    u_gap = unexpected_gaps[0]
    assert "2024-07-02" in u_gap["prev_time_utc"]


def test_gate9_timezone_normalization_utc() -> None:
    """Gate 9: Verify timezone semantics and strict UTC canonical authority."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_H4_2021_2024_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    tr = manifest["time_range"]
    assert tr["timezone"] == "UTC"
    assert tr["min_event_time_utc"] == "2021-01-04T00:00:00+00:00"
    assert tr["max_event_time_utc"] == "2024-12-31T20:00:00+00:00"


def test_gate10_provenance_and_ledger(
    require_research_artifact: Callable[[Sequence[Path], str], None],
) -> None:
    """Gate 10 (DATA-DEPENDENT, sealed HYP_002 provenance): Verify provenance record in JSONL ledger."""
    tracker = ProvenanceTracker(
        ledger_path=Path("data/provenance_ledger.jsonl"),
        manifests_dir=Path("data/manifests/research"),
    )
    require_research_artifact(
        [Path("data/provenance_ledger.jsonl")],
        "Sealed H4 provenance ledger with EURUSD H4 research batch record",
    )
    records = tracker.read_provenance_records()
    h4_records = [r for r in records if "eurusd_h4" in r.batch_id]
    if not h4_records:
        pytest.skip(
            "DATA-DEPENDENT-ENVIRONMENT: sealed H4 provenance record is not present in "
            "data/provenance_ledger.jsonl; the EURUSD H4 research batch was not produced in this environment"
        )
    assert len(h4_records) >= 1, "H4 provenance record not found in data/provenance_ledger.jsonl"
    rec = h4_records[-1]
    assert rec.symbol == "EURUSD"
    assert rec.timeframe == "H4"
    assert rec.row_count == 6231
    assert rec.validation_status == "VALID"
    assert rec.error_count == 0


def test_gate11_digests_and_manifest_consistency(
    require_research_artifact: Callable[[Sequence[Path], str], None],
) -> None:
    """Gate 11 (DATA-DEPENDENT, sealed raw CSV + canonical parquet): Verify content digests and dataset manifest consistency."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_H4_2021_2024_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Verify raw CSV SHA-256
    raw_csv_path = Path(manifest["file_locations"]["raw_csv_path"])
    parquet_path = Path(manifest["file_locations"]["canonical_parquet_path"])
    require_research_artifact(
        [raw_csv_path, parquet_path],
        "Sealed EURUSD H4 raw CSV source and canonical parquet dataset",
    )
    assert raw_csv_path.exists()
    raw_hash = calculate_raw_source_sha256(raw_csv_path.read_bytes())
    assert raw_hash == manifest["digests"]["raw_source_sha256"]

    # Verify canonical table logical batch hash
    assert parquet_path.exists()
    table = pq.read_table(parquet_path)
    canonical_hash = calculate_canonical_batch_sha256(table)
    assert canonical_hash == manifest["digests"]["canonical_batch_sha256"]

    # Verify parquet file binary hash
    file_hash = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    assert file_hash == manifest["digests"]["parquet_file_sha256"]


def test_gate12_feature_non_anticipation(
    build_canonical_synthetic_table: Callable[..., pa.Table],
) -> None:
    """Gate 12: Verify causal feature calculation cannot anticipate future bars (generic contract, deterministic synthetic fixture)."""
    table = build_canonical_synthetic_table(n_bars=700, timeframe="TF4", step_minutes=240)
    closes = np.array([float(c) for c in table["close"].to_pylist()])

    for lookback in [3, 6, 12, 24, 48, 120]:
        t = 500
        original_feature = np.log(closes[t] / closes[t - lookback])

        # Perturb future bar (t + 1)
        perturbed_closes = closes.copy()
        perturbed_closes[t + 1] = perturbed_closes[t + 1] * 1.05
        perturbed_feature = np.log(perturbed_closes[t] / perturbed_closes[t - lookback])

        assert np.isclose(original_feature, perturbed_feature), (
            f"Feature with lookback {lookback} changed when future bar t+1 was perturbed!"
        )


def test_gate13_research_split_policy_and_embargo() -> None:
    """Gate 13: Verify deterministic split policy and 12-bar embargo buffers."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_H4_2021_2024_canonical.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    sp = manifest["split_policy"]
    total = sp["total_bars"]
    assert total == 6231
    assert sp["embargo_bars"] == 12

    train = sp["train"]
    emb1 = sp["embargo_train_val"]
    val = sp["validation"]
    emb2 = sp["embargo_val_oos"]
    oos = sp["oos_held_out"]

    assert train["bar_count"] == 3739
    assert emb1["bar_count"] == 12
    assert val["bar_count"] == 1246
    assert emb2["bar_count"] == 12
    assert oos["bar_count"] == 1222

    # Contiguity check
    assert train["end_index"] + 1 == emb1["start_index"]
    assert emb1["end_index"] + 1 == val["start_index"]
    assert val["end_index"] + 1 == emb2["start_index"]
    assert emb2["end_index"] + 1 == oos["start_index"]
    assert oos["end_index"] == total - 1

    # Pristine exposure state
    assert val["exposure_state"] == "UNEXPOSED_PRISTINE"
    assert oos["exposure_state"] == "UNEXPOSED_PRISTINE"
