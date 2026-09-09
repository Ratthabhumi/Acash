"""Adversarial tests for canonical Out-of-Sample provenance (Phase 14, D5-A ratified).

Attack the ratified D5-A contract: OOS is the canonical SplitPolicy partition, sliced
deterministically from the canonical event stream with explicit inclusive boundaries and embargo
buffers; OOS evidence comes from a SEPARATE held-out Phase 5 run (fresh runner/ledger) whose equity
is never the IS equity; PIT lineage is IN D5 SCOPE and fails closed; dataset identity/provenance is
auditably bound; the OOS evidence record is immutable and content-determined. No synthetic OOS; no
post-hoc construction; no IS-equity reuse.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Sequence

import pyarrow as pa
import pytest

from acash.backtest.adapter import (
    BacktestEventType,
    BacktestMarketEvent,
    CanonicalDataAdapter,
)
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.equity_returns import derive_canonical_equity_returns
from acash.backtest.schema import BacktestEngineConfig
from acash.backtest.strategies.imbalance_actor import MicrostructureImbalanceActor
from acash.core.domain.exceptions import DataContractError
from acash.research.oos_provenance import (
    OOS_MIN_OBSERVATIONS,
    OosEvidenceRecord,
    PitLineageAttestation,
    PriceAdjustmentPolicy,
    build_oos_backtest_evidence,
    extract_oos_event_segment,
    resolve_partition_ranges,
    run_separate_oos_backtest,
    verify_pit_knowledge_ordering,
    verify_pit_lineage,
)
from acash.research.outcomes import partition_dataset_with_embargo
from acash.research.schema import SplitPolicy
from acash.validation.deflated_sharpe import calculate_annualized_sharpe
from acash.validation.gate import _compute_canonical_series_sha256

_PPY = Decimal("252.0")
_TS_BASE_NS = 1_768_833_000_000_000_000
_T60_NS = 60_000_000_000

_POLICY = SplitPolicy(
    train_pct=Decimal("0.60"),
    val_pct=Decimal("0.20"),
    oos_pct=Decimal("0.20"),
    embargo_bars=1,
)

_CLOSES = [
    Decimal("5000.00"),
    Decimal("5002.00"),
    Decimal("5004.00"),
    Decimal("5008.00"),
    Decimal("5012.00"),
    Decimal("5016.00"),
    Decimal("5020.00"),
    Decimal("5026.00"),
    Decimal("5030.00"),
    Decimal("5034.00"),
    Decimal("5040.00"),
    Decimal("5046.00"),
    Decimal("5052.00"),
    Decimal("5058.00"),
    Decimal("5064.00"),
    Decimal("5070.00"),
    Decimal("5076.00"),
    Decimal("5082.00"),
    Decimal("5088.00"),
    Decimal("5094.00"),
    Decimal("5100.00"),
    Decimal("5106.00"),
    Decimal("5112.00"),
    Decimal("5118.00"),
    Decimal("5124.00"),
    Decimal("5130.00"),
    Decimal("5136.00"),
    Decimal("5142.00"),
    Decimal("5148.00"),
    Decimal("5154.00"),
    Decimal("5160.00"),
    Decimal("5166.00"),
    Decimal("5172.00"),
    Decimal("5178.00"),
    Decimal("5184.00"),
    Decimal("5190.00"),
    Decimal("5196.00"),
    Decimal("5202.00"),
    Decimal("5208.00"),
    Decimal("5214.00"),
]


class BuyOnBarActor:
    """Places a single market buy on a global bar index and holds to the end (IS-side actor)."""

    def __init__(self, symbol: str, bar_index: int = 2) -> None:
        self._actor = MicrostructureImbalanceActor(symbol=symbol)
        self._bar_index = bar_index

    def on_bar(self, event: Any, runner: Any) -> None:
        if event.payload["bar_index"] == self._bar_index:
            self._actor.generate_signal_and_order(Decimal("0.40"), runner)

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


class OosEntryActor:
    """Places a single market buy on the first OOS event and holds to the end (OOS-side actor)."""

    def __init__(self, symbol: str) -> None:
        self._actor = MicrostructureImbalanceActor(symbol=symbol)
        self._first = True

    def on_bar(self, event: Any, runner: Any) -> None:
        if self._first:
            self._actor.generate_signal_and_order(Decimal("0.40"), runner)
            self._first = False

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


def _bars_table(embargo_knowledge: bool = True, violate_knowledge_row: bool = False) -> pa.Table:
    n = len(_CLOSES)
    timestamps = [_TS_BASE_NS + (i * _T60_NS) for i in range(n)]
    knowledge = list(timestamps)
    if violate_knowledge_row:
        knowledge[20] = timestamps[20] - 1
    pydict: Dict[str, Any] = {
        "timestamp_utc": timestamps,
        "open": _CLOSES,
        "high": [c + Decimal("1.00") for c in _CLOSES],
        "low": [c - Decimal("1.00") for c in _CLOSES],
        "close": _CLOSES,
        "volume": [Decimal("100.0")] * n,
    }
    if embargo_knowledge:
        pydict["knowledge_time_utc"] = knowledge
    return pa.Table.from_pydict(pydict)


def _events() -> List[BacktestMarketEvent]:
    return CanonicalDataAdapter.from_bars_table(_bars_table(), symbol="ES.FUT")


def _attestation(**overrides: Any) -> PitLineageAttestation:
    base: Dict[str, Any] = {
        "dataset_id": "DATASET_OOS_PROV",
        "dataset_version": "v1",
        "source_kind": "BARS",
        "pit_verified": True,
        "pit_verification_provenance": "Event-level timestamps from source-matched exchange feed with "
        "recorded knowledge_time_utc at each observation",
        "knowledge_time_utc_available": True,
        "price_adjustment_policy": PriceAdjustmentPolicy.NONE_APPLICABLE_RECORDED,
        "corporate_action_provenance": "",
        "canonical_data_hashes": ("d" * 64,),
    }
    base.update(overrides)
    return PitLineageAttestation(**base)


def _is_returns() -> List[Decimal]:
    events = _events()
    parts = partition_dataset_with_embargo(len(_CLOSES), _POLICY)
    is_events = [
        e
        for e in events
        if parts["TRAIN"][0] <= e.payload["bar_index"] <= parts["TRAIN"][1]
        or parts["VAL"][0] <= e.payload["bar_index"] <= parts["VAL"][1]
    ]
    runner = EventBacktestRunner(
        config=BacktestEngineConfig(engine_id="BKT-OOS-IS", symbol="ES.FUT"),
        strategy_actor=BuyOnBarActor("ES.FUT", bar_index=2),
    )
    _, _, equity = runner.run_backtest(
        events=is_events,
        hypothesis_id="HYP_OOS_PROV_IS",
        hypothesis_spec_sha256="a" * 64,
        strategy_config_hash="b" * 64,
        pyproject_toml_sha256="c" * 64,
        git_commit_hash="a" * 40,
        periods_per_year=_PPY,
        canonical_data_hashes=["d" * 64],
    )
    return derive_canonical_equity_returns(equity)


def _build_kwargs(**overrides: Any) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "rows_table": _bars_table(),
        "source_kind": "BARS",
        "events": _events(),
        "strategy_id": "STRAT_OOS_PROV",
        "hypothesis_id": "HYP_OOS_PROV_0001",
        "split_policy": _POLICY,
        "engine_config": BacktestEngineConfig(engine_id="BKT-OOS-PROV", symbol="ES.FUT"),
        "strategy_actor": OosEntryActor("ES.FUT"),
        "periods_per_year": _PPY,
        "hypothesis_spec_sha256": "a" * 64,
        "strategy_config_hash": "b" * 64,
        "pyproject_toml_sha256": "c" * 64,
        "git_commit_hash": "a" * 40,
        "in_sample_returns": _is_returns(),
        "pit_attestation": _attestation(),
        "dataset_id": "DATASET_OOS_PROV",
        "dataset_version": "v1",
    }
    kwargs.update(overrides)
    return kwargs


def _make_event(
    ts_ns: int,
    *,
    bar_index: int | None = None,
    stream_id: str = "TRADES",
) -> BacktestMarketEvent:
    payload: Dict[str, Any] = {"price": Decimal("5000.0")}
    if bar_index is not None:
        payload["bar_index"] = bar_index
    return BacktestMarketEvent(
        event_type=BacktestEventType.TRADE,
        symbol="ES.FUT",
        event_timestamp_ns=ts_ns,
        source_order_key=f"K{ts_ns}",
        message_rank=0,
        stream_id=stream_id,
        row_sub_index=0,
        payload=payload,
    )


class TestPartition:
    def test_resolve_partition_ranges_is_single_authority(self) -> None:
        assert resolve_partition_ranges(40, _POLICY) == partition_dataset_with_embargo(40, _POLICY)

    def test_partition_ranges_contract_40_bars(self) -> None:
        parts = resolve_partition_ranges(40, _POLICY)
        assert parts == {"TRAIN": (0, 23), "VAL": (25, 32), "OOS": (34, 39)}

    def test_partition_ranges_embargo_buffers_are_unallocated(self) -> None:
        parts = resolve_partition_ranges(40, _POLICY)
        allocated = set(range(parts["TRAIN"][0], parts["TRAIN"][1] + 1))
        allocated.update(range(parts["VAL"][0], parts["VAL"][1] + 1))
        allocated.update(range(parts["OOS"][0], parts["OOS"][1] + 1))
        # Bars 24 and 33 are embargo gaps (not train, not val, not OOS).
        assert 24 not in allocated and 33 not in allocated

    def test_partition_ranges_nonpositive_bars_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="num_bars=0 < 1"):
            resolve_partition_ranges(0, _POLICY)


class TestSegment:
    def test_oos_segment_contains_only_oos_bars(self) -> None:
        segment, oos_range, window = extract_oos_event_segment(_events(), 40, _POLICY, _bars_table())
        assert oos_range == (34, 39)
        assert window == (
            _TS_BASE_NS + 34 * _T60_NS,
            _TS_BASE_NS + 39 * _T60_NS,
        )
        assert [e.payload["bar_index"] for e in segment] == [34, 35, 36, 37, 38, 39]

    def test_embargo_bars_excluded_from_oos_segment(self) -> None:
        segment, _, _ = extract_oos_event_segment(_events(), 40, _POLICY, _bars_table())
        indices = {e.payload["bar_index"] for e in segment}
        assert 24 not in indices and 33 not in indices and 23 not in indices and 32 not in indices

    def test_segment_is_deterministic(self) -> None:
        a = extract_oos_event_segment(_events(), 40, _POLICY, _bars_table())[0]
        b = extract_oos_event_segment(_events(), 40, _POLICY, _bars_table())[0]
        assert [e.payload["bar_index"] for e in a] == [e.payload["bar_index"] for e in b]

    def test_non_bar_events_resolved_via_inclusive_window(self) -> None:
        table = _bars_table()
        ts = [_TS_BASE_NS + (i * _T60_NS) for i in range(40)]
        inside = _make_event(ts[34], stream_id="TRADES")
        embargolike = _make_event(ts[33], stream_id="TRADES")
        events = [embargolike, inside]  # ascending timestamp order
        segment, _, window = extract_oos_event_segment(events, 40, _POLICY, table)
        assert segment == (inside,)
        assert window == (ts[34], ts[39])
        assert embargolike not in segment

    def test_non_bar_event_without_bars_table_fails_closed(self) -> None:
        ts = [_TS_BASE_NS + (i * _T60_NS) for i in range(40)]
        with pytest.raises(DataContractError, match="without a canonical bars_table"):
            extract_oos_event_segment([_make_event(ts[34])], 40, _POLICY, None)

    def test_out_of_order_stream_fails_closed(self) -> None:
        events = list(reversed(_events()))
        with pytest.raises(DataContractError, match="Out-of-order"):
            extract_oos_event_segment(events, 40, _POLICY, _bars_table())

    def test_bar_index_out_of_canonical_range_fails_closed(self) -> None:
        event = _make_event(_TS_BASE_NS, bar_index=40)
        with pytest.raises(DataContractError, match="outside canonical range"):
            extract_oos_event_segment([event], 40, _POLICY, _bars_table())

    def test_bar_index_timestamp_contradiction_fails_closed(self) -> None:
        # Claims OOS bar 34 but carries the timestamp of in-sample bar 10.
        ts10 = _TS_BASE_NS + 10 * _T60_NS
        event = _make_event(ts10, bar_index=34)
        with pytest.raises(DataContractError, match="identity contradiction"):
            extract_oos_event_segment([event], 40, _POLICY, _bars_table())

    def test_bars_table_row_mismatch_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="must equal bars_table row count"):
            extract_oos_event_segment(_events(), 39, _POLICY, _bars_table())


class TestPitFailClosed:
    def test_pit_not_verified_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="verified point-in-time"):
            verify_pit_lineage(_attestation(pit_verified=False))

    def test_pit_verified_without_provenance_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="pit_verification_provenance"):
            verify_pit_lineage(_attestation(pit_verification_provenance="  "))

    def test_adjusted_verified_without_proof_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="verified corporate-action"):
            verify_pit_lineage(
                _attestation(price_adjustment_policy=PriceAdjustmentPolicy.ADJUSTED_VERIFIED, corporate_action_provenance="")
            )

    def test_knowledge_time_unavailable_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="knowledge_time_utc availability"):
            verify_pit_lineage(_attestation(knowledge_time_utc_available=False))

    def test_unsupported_source_kind_fails_closed(self) -> None:
        attestation = _attestation(source_kind="ORDERFLOW")
        with pytest.raises(DataContractError, match="Unsupported source_kind"):
            verify_pit_knowledge_ordering(_bars_table(), "ORDERFLOW", attestation)

    def test_missing_knowledge_time_utc_column_fails_closed(self) -> None:
        table = _bars_table(embargo_knowledge=False)
        with pytest.raises(DataContractError, match="knowledge_time_utc.*missing"):
            verify_pit_knowledge_ordering(table, "BARS", _attestation())

    def test_missing_event_anchor_column_fails_closed(self) -> None:
        table = _bars_table().drop(["timestamp_utc"])
        with pytest.raises(DataContractError, match="event-time anchor column.*missing"):
            verify_pit_knowledge_ordering(table, "BARS", _attestation())

    def test_knowledge_ordering_violation_fails_closed(self) -> None:
        table = _bars_table(violate_knowledge_row=True)
        with pytest.raises(DataContractError, match="PIT ordering violation"):
            verify_pit_knowledge_ordering(table, "BARS", _attestation())

    def test_pit_dataset_identity_mismatch_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="dataset identity"):
            build_oos_backtest_evidence(
                **_build_kwargs(
                    pit_attestation=_attestation(dataset_id="DATASET_OTHER", dataset_version="v2")
                )
            )

    def test_valid_attestation_verifies(self) -> None:
        assert verify_pit_lineage(_attestation()) is not None
        assert verify_pit_knowledge_ordering(_bars_table(), "BARS", _attestation()) is True


class TestBuildEvidence:
    def test_happy_path_separate_oos_run(self) -> None:
        record, manifest, _fills, oos_equity, oos_returns = build_oos_backtest_evidence(
            **_build_kwargs()
        )
        ts = [_TS_BASE_NS + (i * _T60_NS) for i in range(40)]

        assert record.oos_range_start == 34 and record.oos_range_end == 39
        assert record.oos_window_start_ns == ts[34] and record.oos_window_end_ns == ts[39]
        assert record.oos_event_count == 6
        assert record.oos_return_count == 5
        assert record.oos_return_series_sha256 == _compute_canonical_series_sha256(oos_returns)
        assert len(record.content_digest()) == 64
        assert record.content_digest() != record.oos_manifest_id

        # OOS identity must be bound to the OOS manifest of the separate run.
        assert record.oos_manifest_id == manifest.manifest_id
        assert manifest.hypothesis_id == "HYP_OOS_PROV_0001"
        # OOS returns derive exclusively from the OOS equity curve.
        assert oos_returns == derive_canonical_equity_returns(oos_equity)
        # OOS equity curve has exactly one row per OOS event (6 events -> 5 returns).
        assert oos_equity.num_rows == 6
        assert record.oos_return_count == oos_equity.num_rows - 1
        # Fresh-run guarantee: the OOS equity curve is its own curve (positive, entry costs applied,
        # distinct from any IS equity by construction of the separate runner).
        first_equity = Decimal(str(oos_equity.column("total_equity")[0].as_py()))
        assert Decimal("0") < first_equity <= Decimal("100000.00")
        # No-IS-reuse invariant is cryptographically asserted.
        record.assert_is_oos_distinct()
        assert len(record.oos_manifest_id) == 32

    def test_is_returns_empty_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="In-sample return series required"):
            build_oos_backtest_evidence(**_build_kwargs(in_sample_returns=[]))

    def test_is_equity_reuse_as_oos_fails_closed(self) -> None:
        _, _, _, _, oos_returns = build_oos_backtest_evidence(**_build_kwargs())
        with pytest.raises(DataContractError, match="must not be reused as OOS"):
            build_oos_backtest_evidence(**_build_kwargs(in_sample_returns=oos_returns))

    def test_insufficient_oos_observations_fails_closed(self) -> None:
        # embargo=60 swallows the dataset: OOS collapses to a single bar -> <5 events.
        policy = SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=60,
        )
        with pytest.raises(DataContractError, match="at least 5 observations"):
            build_oos_backtest_evidence(**_build_kwargs(split_policy=policy))

    def test_empty_pit_attestation_blocks_build(self) -> None:
        with pytest.raises(DataContractError, match="verified point-in-time"):
            build_oos_backtest_evidence(**_build_kwargs(pit_attestation=_attestation(pit_verified=False)))

    def test_direct_fresh_runner_is_used_per_call(self) -> None:
        segment, _, _ = extract_oos_event_segment(_events(), 40, _POLICY, _bars_table())
        manifest_a, _fills_a, eq_a = run_separate_oos_backtest(
            oos_events=segment,
            engine_config=BacktestEngineConfig(engine_id="BKT-OOS-FRESH", symbol="ES.FUT"),
            strategy_actor=OosEntryActor("ES.FUT"),
            hypothesis_id="HYP_OOS_PROV_0001",
            hypothesis_spec_sha256="a" * 64,
            strategy_config_hash="b" * 64,
            pyproject_toml_sha256="c" * 64,
            git_commit_hash="a" * 40,
            periods_per_year=_PPY,
            canonical_data_hashes=["d" * 64],
        )
        assert isinstance(eq_a.num_rows, int)
        assert eq_a.num_rows == 6
        # A second fresh run is content-identical and independently constructed.
        manifest_b, _, _ = run_separate_oos_backtest(
            oos_events=segment,
            engine_config=BacktestEngineConfig(engine_id="BKT-OOS-FRESH", symbol="ES.FUT"),
            strategy_actor=OosEntryActor("ES.FUT"),
            hypothesis_id="HYP_OOS_PROV_0001",
            hypothesis_spec_sha256="a" * 64,
            strategy_config_hash="b" * 64,
            pyproject_toml_sha256="c" * 64,
            git_commit_hash="a" * 40,
            periods_per_year=_PPY,
            canonical_data_hashes=["d" * 64],
        )
        assert manifest_b.manifest_id == manifest_a.manifest_id


class TestRecordDigest:
    def _record_src(self) -> Dict[str, Any]:
        table = _bars_table()
        ts = [_TS_BASE_NS + (i * _T60_NS) for i in range(40)]
        return {
            "strategy_id": "STRAT_OOS_PROV",
            "hypothesis_id": "HYP_OOS_PROV_0001",
            "dataset_id": "DATASET_OOS_PROV",
            "dataset_version": "v1",
            "split_policy_train_pct": str(_POLICY.train_pct),
            "split_policy_val_pct": str(_POLICY.val_pct),
            "split_policy_oos_pct": str(_POLICY.oos_pct),
            "split_policy_embargo_bars": _POLICY.embargo_bars,
            "num_bars": 40,
            "oos_range_start": 34,
            "oos_range_end": 39,
            "oos_window_start_ns": ts[34],
            "oos_window_end_ns": ts[39],
            "oos_event_count": 6,
            "oos_manifest_id": "e" * 64,
            "oos_return_count": 6,
            "oos_return_series_sha256": "f" * 64,
            "in_sample_return_series_sha256": "0" * 64,
            "canonical_data_hashes": ("d" * 64,),
            "pit_attestation": _attestation(),
            "created_at_utc": "2026-09-09T00:00:00+00:00",
        }

    def test_content_digest_deterministic_and_ignores_created_at(self) -> None:
        src = self._record_src()
        a = OosEvidenceRecord(**src)
        src["created_at_utc"] = "2026-09-09T23:59:00+00:00"
        b = OosEvidenceRecord(**src)
        assert a.content_digest() == b.content_digest()
        assert len(a.content_digest()) == 64

    def test_content_digest_changes_with_content(self) -> None:
        src = self._record_src()
        a = OosEvidenceRecord(**src)
        src["oos_manifest_id"] = "9" * 64
        b = OosEvidenceRecord(**src)
        assert a.content_digest() != b.content_digest()

    def test_identical_sha256_series_fails_closed(self) -> None:
        src = self._record_src()
        src["in_sample_return_series_sha256"] = src["oos_return_series_sha256"]
        record = OosEvidenceRecord(**src)
        with pytest.raises(DataContractError, match="must not be reused as OOS"):
            record.assert_is_oos_distinct()