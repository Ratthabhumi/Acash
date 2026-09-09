"""Canonical Out-of-Sample (OOS) provenance for held-out Phase 5 runs (Phase 14, D5-A ratified).

Ratified D5-A contract (see ``docs/phase14/phase14_d5_d6_ratification_record.md``):

- OOS is the canonical ``SplitPolicy`` partition (train / validation / OOS inclusive index ranges
  plus embargo buffers; single authority: ``research.outcomes.partition_dataset_with_embargo``).
- OOS events are sliced DETERMINISTICALLY from the canonical sorted event stream; boundary
  inclusivity/exclusivity is explicit (inclusive OOS index range + inclusive timestamp window;
  embargo buffers are unallocated and belong to neither IS nor OOS).
- OOS is produced by a SEPARATE HELD-OUT Phase 5 execution: a fresh ``EventBacktestRunner`` with a
  fresh ``ShadowAccountingLedger``; the OOS equity curve and OOS ``BacktestManifest`` come from that
  run alone. IS equity is NEVER reused as OOS evidence.
- OOS identity is bound to its own run at the OOS-evidence-record layer (``OosEvidenceRecord``),
  because ``BacktestManifest`` digest redesign is NOT authorized.
- PIT lineage is IN D5 SCOPE: OOS evidence requires a verified ``PitLineageAttestation``;
  missing / unverifiable PIT provenance FAILS CLOSED. Corporate-action or data-availability lineage
  is never silently treated as PIT; verified-adjustment claims require proof.
- No synthetic OOS evidence; no post-hoc OOS construction from observed results.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field, field_validator

from acash.backtest.adapter import (
    BacktestMarketEvent,
    extract_nanoseconds_from_scalar,
)
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.equity_returns import derive_canonical_equity_returns
from acash.backtest.schema import BacktestEngineConfig, BacktestManifest
from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.outcomes import partition_dataset_with_embargo
from acash.research.schema import SplitPolicy
from acash.validation.gate import _compute_canonical_series_sha256

OOS_MIN_RETURNS = 4  # Phase 6 gate minimum OOS observations (gate.py:238).
OOS_MIN_OBSERVATIONS = OOS_MIN_RETURNS + 1  # equity rows = events; returns = rows - 1.

_HEX64 = r"^[0-9a-f]{64}$"


class PriceAdjustmentPolicy(str, Enum):
    """Truthful corporate-action / price-adjustment disclosure for the OOS dataset provenance."""

    NONE_APPLICABLE_RECORDED = "NONE_APPLICABLE_RECORDED"
    ADJUSTED_VERIFIED = "ADJUSTED_VERIFIED"


# Canonical anchor column per source kind used to verify knowledge-time ordering at data level.
_PIT_ROW_TIME_ANCHOR: Mapping[str, str] = {
    "BARS": "timestamp_utc",
    "TRADES": "exchange_time_utc",
    "ORDERBOOK": "exchange_time_utc",
}


class PitLineageAttestation(BaseModel):
    """Declarative, truthful point-in-time lineage attestation required for OOS evidence.

    OOS evidence FAILS CLOSED unless: ``pit_verified`` is True with non-empty verification
    provenance; knowledge-time ordering is provable on the dataset rows; and any verified
    corporate-action adjustment claim carries non-empty provenance. Data-availability lineage is
    never implicitly treated as PIT.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str = Field(min_length=1, description="Canonical dataset identifier.")
    dataset_version: str = Field(min_length=1, description="Canonical dataset version.")
    source_kind: str = Field(min_length=1, description="BARS | TRADES | ORDERBOOK dataset kind.")
    pit_verified: bool = Field(description="True only if the underlying source can prove PIT access.")
    pit_verification_provenance: str = Field(
        min_length=1, description="Proof of how the source establishes point-in-time access."
    )
    knowledge_time_utc_available: bool = Field(
        description="True if the dataset rows carry knowledge_time_utc that can be order-verified."
    )
    price_adjustment_policy: PriceAdjustmentPolicy = Field(
        description="Explicit corporate-action / price adjustment disclosure."
    )
    corporate_action_provenance: str = Field(
        default="", description="Proof of adjustment when price_adjustment_policy is ADJUSTED_VERIFIED."
    )
    canonical_data_hashes: Tuple[str, ...] = Field(
        min_length=1, description="Canonical dataset content hashes (manifest lineage semantics)."
    )

    @field_validator("canonical_data_hashes")
    @classmethod
    def _validate_hex64_hashes(cls, v: Tuple[str, ...]) -> Tuple[str, ...]:
        import re as _re

        for h in v:
            if not _re.fullmatch(_HEX64, h):
                raise ValueError(f"Invalid canonical data hash: '{h}'. Must be 64 lowercase hex characters.")
        return v


def verify_pit_lineage(attestation: PitLineageAttestation) -> PitLineageAttestation:
    """Enforce the ratified fail-closed PIT lineage contract for OOS evidence.

    Raises:
        DataContractError: If PIT is not verified, verification provenance is missing, verified
            corporate-action adjustment is claimed without proof, or knowledge-time availability is
            unproven. No synthetic or implicit PIT admission is possible.
    """
    if not attestation.pit_verified:
        raise DataContractError(
            f"OOS evidence requires verified point-in-time (PIT) lineage for dataset "
            f"'{attestation.dataset_id}' version '{attestation.dataset_version}'; "
            f"missing/unverifiable PIT provenance FAILS CLOSED."
        )
    if not attestation.pit_verification_provenance.strip():
        raise DataContractError(
            f"PitLineageAttestation claims pit_verified=True for dataset '{attestation.dataset_id}' "
            f"but provides no pit_verification_provenance; a bare claim cannot establish PIT lineage."
        )
    if (
        attestation.price_adjustment_policy == PriceAdjustmentPolicy.ADJUSTED_VERIFIED
        and not attestation.corporate_action_provenance.strip()
    ):
        raise DataContractError(
            f"Dataset '{attestation.dataset_id}' claims verified corporate-action adjustment "
            f"(ADJUSTED_VERIFIED) without adjustment provenance; data-availability lineage must not "
            f"be silently treated as PIT."
        )
    if not attestation.knowledge_time_utc_available:
        raise DataContractError(
            f"Dataset '{attestation.dataset_id}' cannot prove knowledge_time_utc availability; "
            f"missing PIT provenance FAILS CLOSED for OOS evidence."
        )
    return attestation


def verify_pit_knowledge_ordering(
    rows_table: pa.Table,
    source_kind: str,
    attestation: PitLineageAttestation,
) -> bool:
    """Verify on the dataset rows that ``knowledge_time_utc >= <event time anchor>`` per row.

    ``knowledge_time_utc`` and the source-appropriate event-time anchor must exist; any row whose
    knowledge time precedes its event time is a lookahead violation and FAILS CLOSED.

    Raises:
        DataContractError: On unsupported source kind, missing columns, or ordering violations.
    """
    if not attestation.knowledge_time_utc_available:
        raise DataContractError(
            f"PitLineageAttestation for dataset '{attestation.dataset_id}' declares knowledge-time "
            f"proof unavailable; OOS evidence cannot proceed without it."
        )
    anchor_col = _PIT_ROW_TIME_ANCHOR.get(source_kind)
    if anchor_col is None:
        raise DataContractError(
            f"Unsupported source_kind '{source_kind}' in PitLineageAttestation; "
            f"PIT ordering anchor undefined."
        )
    if "knowledge_time_utc" not in rows_table.column_names:
        raise DataContractError(
            f"Cannot verify PIT knowledge-time ordering for dataset '{attestation.dataset_id}': "
            f"required column 'knowledge_time_utc' missing from dataset rows (source_kind={source_kind})."
        )
    if anchor_col not in rows_table.column_names:
        raise DataContractError(
            f"Cannot verify PIT knowledge-time ordering for dataset '{attestation.dataset_id}': "
            f"required event-time anchor column '{anchor_col}' missing from dataset rows "
            f"(source_kind={source_kind})."
        )

    known_col = rows_table.column("knowledge_time_utc")
    anchor_cols = rows_table.column(anchor_col)
    num_rows = rows_table.num_rows
    for i in range(num_rows):
        known_ns = extract_nanoseconds_from_scalar(known_col[i], known_col.type)
        anchor_ns = extract_nanoseconds_from_scalar(anchor_cols[i], anchor_cols.type)
        if known_ns < anchor_ns:
            raise DataContractError(
                f"PIT ordering violation at dataset row {i}: knowledge_time_utc ({known_ns} ns) "
                f"precedes event time ({anchor_ns} ns); lookahead across the temporal boundary "
                f"fails closed."
            )
    return True


def resolve_partition_ranges(
    num_bars: int,
    split_policy: Optional[SplitPolicy] = None,
) -> Dict[str, Tuple[int, int]]:
    """Resolve the canonical train/validation/OOS inclusive index ranges (single SplitPolicy authority)."""
    if num_bars < 1:
        raise DataContractError(f"Cannot resolve partition ranges for num_bars={num_bars} < 1.")
    return partition_dataset_with_embargo(num_bars, split_policy or SplitPolicy())


def resolve_oos_bar_window_ns(bars_table: pa.Table, oos_start: int, oos_end: int) -> Tuple[int, int]:
    """Resolve the inclusive OOS event-window bounds (ns) from the canonical bars table.

    The OOS window is ``[timestamp_utc[oos_start], timestamp_utc[oos_end]]`` inclusive. The embargo
    buffers before ``oos_start`` are unallocated and never part of the window.
    """
    if "timestamp_utc" not in bars_table.column_names:
        raise DataContractError(
            "Cannot resolve OOS window: canonical bars table lacks ordering column 'timestamp_utc'."
        )
    if oos_start < 0 or oos_end >= bars_table.num_rows:
        raise DataContractError(
            f"OOS range ({oos_start}, {oos_end}) outside canonical bars table bounds "
            f"(rows={bars_table.num_rows})."
        )
    ts_col = bars_table.column("timestamp_utc")
    start_ns = extract_nanoseconds_from_scalar(ts_col[oos_start], ts_col.type)
    end_ns = extract_nanoseconds_from_scalar(ts_col[oos_end], ts_col.type)
    return (start_ns, end_ns)


def extract_oos_event_segment(
    events: Sequence[BacktestMarketEvent],
    num_bars: int,
    split_policy: Optional[SplitPolicy] = None,
    bars_table: Optional[pa.Table] = None,
) -> Tuple[Tuple[BacktestMarketEvent, ...], Tuple[int, int], Optional[Tuple[int, int]]]:
    """Deterministically slice the OOS-only event segment from the canonical sorted event stream.

    - Bar-indexed events (``payload["bar_index"]``) are members iff ``oos_start <= bar_index <= oos_end``.
    - Non-bar events are members iff ``event_timestamp_ns`` lies within the inclusive OOS timestamp
      window (requires ``bars_table``; otherwise FAILS CLOSED).
    - A bar-indexed event claiming an OOS index whose timestamp falls outside the OOS window is a
      contradiction and FAILS CLOSED.

    Returns:
        ``(segment, oos_inclusive_range, oos_window_ns)`` where ``oos_window_ns`` is the inclusive
        ``(start_ns, end_ns)`` window or ``None`` when not resolvable without a bars table.

    Raises:
        DataContractError: On out-of-order input, index/timestamp contradictions, bar indices out of
            the canonical range, ``num_bars`` vs ``bars_table`` inconsistency, or undeterminable
            non-bar membership.
    """
    if num_bars < 1:
        raise DataContractError(f"Cannot extract OOS segment for num_bars={num_bars} < 1.")
    if bars_table is not None and bars_table.num_rows != num_bars:
        raise DataContractError(
            f"num_bars={num_bars} must equal bars_table row count ({bars_table.num_rows}) for "
            f"canonical OOS segment extraction."
        )

    partitions = resolve_partition_ranges(num_bars, split_policy)
    oos_start, oos_end = partitions["OOS"]

    prev: Optional[Tuple[Any, ...]] = None
    for ev in events:
        order_key = ev.order_tuple
        if prev is not None and order_key < prev:
            raise DataContractError(
                "Out-of-order event stream at OOS segment extraction; canonical 5-tuple ordering violated."
            )
        prev = order_key

    window: Optional[Tuple[int, int]] = None
    if bars_table is not None:
        window = resolve_oos_bar_window_ns(bars_table, oos_start, oos_end)

    segment: List[BacktestMarketEvent] = []
    for ev in events:
        idx_val = ev.payload.get("bar_index")
        if idx_val is not None:
            idx = int(idx_val)
            if not (0 <= idx < num_bars):
                raise DataContractError(
                    f"Event '{ev.source_order_key}' carries bar_index {idx} outside canonical range "
                    f"[0, {num_bars - 1}]; index identity inconsistent with the dataset."
                )
            if oos_start <= idx <= oos_end:
                if window is not None and not (window[0] <= ev.event_timestamp_ns <= window[1]):
                    raise DataContractError(
                        f"Event '{ev.source_order_key}' claims OOS bar_index {idx} but its "
                        f"timestamp ({ev.event_timestamp_ns} ns) falls outside the inclusive OOS "
                        f"window {window}; index/timestamp identity contradiction fails closed."
                    )
                segment.append(ev)
        else:
            if window is None:
                raise DataContractError(
                    "Cannot resolve OOS membership for non-bar events without a canonical bars_table; "
                    "temporal window undefined."
                )
            if window[0] <= ev.event_timestamp_ns <= window[1]:
                segment.append(ev)

    return tuple(segment), (oos_start, oos_end), window


def run_separate_oos_backtest(
    *,
    oos_events: Sequence[BacktestMarketEvent],
    engine_config: BacktestEngineConfig,
    strategy_actor: Any,
    hypothesis_id: str,
    hypothesis_spec_sha256: str,
    strategy_config_hash: str,
    pyproject_toml_sha256: str,
    git_commit_hash: str,
    periods_per_year: Decimal,
    canonical_data_hashes: Optional[List[str]] = None,
) -> Tuple[BacktestManifest, pa.Table, pa.Table]:
    """Execute the OOS segment through a FRESH Phase 5 runner (separate held-out execution).

    A new ``EventBacktestRunner`` is constructed here with a fresh ``ShadowAccountingLedger``
    (``initial_cash`` from ``engine_config``), so the OOS equity curve and OOS ``BacktestManifest``
    derive exclusively from the OOS segment. IS ledger/equity state is never carried into this run —
    IS equity cannot be reused as OOS evidence by construction.
    """
    runner = EventBacktestRunner(config=engine_config, strategy_actor=strategy_actor)
    manifest, fills_table, equity_table = runner.run_backtest(
        events=list(oos_events),
        hypothesis_id=hypothesis_id,
        hypothesis_spec_sha256=hypothesis_spec_sha256,
        strategy_config_hash=strategy_config_hash,
        pyproject_toml_sha256=pyproject_toml_sha256,
        git_commit_hash=git_commit_hash,
        periods_per_year=periods_per_year,
        canonical_data_hashes=canonical_data_hashes,
    )
    return manifest, fills_table, equity_table


class OosEvidenceRecord(BaseModel):
    """Immutable record binding OOS identity to its own held-out run/provenance.

    The record binds the canonical OOS window, inclusive index range, OOS event segment, OOS
    ``BacktestManifest`` id, OOS return-series canonical hash, IS return-series hash (for the
    no-reuse invariant), the dataset identity/version and its canonical data hashes, and the verified
    PIT attestation. ``content_digest()`` is the deterministic content identity excluding the volatile
    ``created_at_utc`` timestamp.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    split_policy_train_pct: str
    split_policy_val_pct: str
    split_policy_oos_pct: str
    split_policy_embargo_bars: int
    num_bars: int
    oos_range_start: int
    oos_range_end: int
    oos_window_start_ns: int
    oos_window_end_ns: int
    oos_event_count: int
    oos_manifest_id: str = Field(min_length=1)
    oos_return_count: int
    oos_return_series_sha256: str = Field(pattern=_HEX64)
    in_sample_return_series_sha256: str = Field(pattern=_HEX64)
    canonical_data_hashes: Tuple[str, ...] = Field(min_length=1)
    pit_attestation: PitLineageAttestation
    created_at_utc: str = Field(min_length=1)

    @field_validator("canonical_data_hashes")
    @classmethod
    def _validate_canonical_hashes(cls, v: Tuple[str, ...]) -> Tuple[str, ...]:
        import re as _re

        for h in v:
            if not _re.fullmatch(_HEX64, h):
                raise ValueError(f"Invalid canonical data hash: '{h}'. Must be 64 lowercase hex characters.")
        return v

    def assert_is_oos_distinct(self) -> None:
        """Fail closed if the recorded OOS return series is identical to the IS return series."""
        if self.oos_return_series_sha256 == self.in_sample_return_series_sha256:
            raise DataContractError(
                f"OosEvidenceRecord for hypothesis '{self.hypothesis_id}' binds an OOS return series "
                f"identical to the IS return series ({self.oos_return_series_sha256}); IS equity must "
                f"not be reused as OOS evidence."
            )

    def content_digest(self) -> str:
        """Deterministic content identity of the OOS evidence record (volatile timestamp excluded)."""
        pit_payload: Dict[str, Any] = {
            "dataset_id": self.pit_attestation.dataset_id,
            "dataset_version": self.pit_attestation.dataset_version,
            "source_kind": self.pit_attestation.source_kind,
            "pit_verified": self.pit_attestation.pit_verified,
            "pit_verification_provenance": self.pit_attestation.pit_verification_provenance,
            "knowledge_time_utc_available": self.pit_attestation.knowledge_time_utc_available,
            "price_adjustment_policy": self.pit_attestation.price_adjustment_policy.value,
            "corporate_action_provenance": self.pit_attestation.corporate_action_provenance,
            "canonical_data_hashes": sorted(self.pit_attestation.canonical_data_hashes),
        }
        payload: Dict[str, Any] = {
            "strategy_id": self.strategy_id,
            "hypothesis_id": self.hypothesis_id,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "split_policy": {
                "train_pct": self.split_policy_train_pct,
                "val_pct": self.split_policy_val_pct,
                "oos_pct": self.split_policy_oos_pct,
                "embargo_bars": self.split_policy_embargo_bars,
            },
            "num_bars": self.num_bars,
            "oos_range": [self.oos_range_start, self.oos_range_end],
            "oos_window_ns": [self.oos_window_start_ns, self.oos_window_end_ns],
            "oos_event_count": self.oos_event_count,
            "oos_manifest_id": self.oos_manifest_id,
            "oos_return_count": self.oos_return_count,
            "oos_return_series_sha256": self.oos_return_series_sha256,
            "in_sample_return_series_sha256": self.in_sample_return_series_sha256,
            "canonical_data_hashes": sorted(self.canonical_data_hashes),
            "pit_attestation": pit_payload,
        }
        return CanonicalConfigSerializer.compute_sha256(payload)


def build_oos_backtest_evidence(
    *,
    rows_table: pa.Table,
    source_kind: str,
    events: Sequence[BacktestMarketEvent],
    strategy_id: str,
    hypothesis_id: str,
    split_policy: SplitPolicy,
    engine_config: BacktestEngineConfig,
    strategy_actor: Any,
    periods_per_year: Decimal,
    hypothesis_spec_sha256: str,
    strategy_config_hash: str,
    pyproject_toml_sha256: str,
    git_commit_hash: str,
    in_sample_returns: Sequence[Union[Decimal, float]],
    pit_attestation: PitLineageAttestation,
    dataset_id: str,
    dataset_version: str,
) -> Tuple[OosEvidenceRecord, BacktestManifest, pa.Table, pa.Table, List[Decimal]]:
    """Build the canonical OOS evidence for a hypothesis from a separate held-out Phase 5 run.

    Pure-deterministic assembly: (1) PIT attestation + knowledge-time ordering fail closed; (2) OOS
    segment is sliced with the canonical ``SplitPolicy`` before any evaluation; (3) a FRESH Phase 5
    runner executes the OOS segment only; (4) OOS returns derive exclusively from the OOS equity;
    (5) OOS evidence record binds segment/window/manifest/series/all dataset and PIT provenance and
    the no-IS-equity-reuse invariant.

    Returns:
        ``(record, oos_manifest, oos_fills, oos_equity, oos_return_series)``.

    Raises:
        DataContractError: On any fail-closed violation (PIT, ordering, segment, reuse, insufficient
            observations, identity mismatch).
    """
    if pit_attestation.dataset_id != dataset_id or pit_attestation.dataset_version != dataset_version:
        raise DataContractError(
            f"PitLineageAttestation dataset identity ({pit_attestation.dataset_id} v"
            f"{pit_attestation.dataset_version}) does not match declared OOS dataset identity "
            f"({dataset_id} v{dataset_version}); dataset provenance binding fails closed."
        )

    verify_pit_lineage(pit_attestation)
    verify_pit_knowledge_ordering(rows_table, source_kind, pit_attestation)

    num_bars = rows_table.num_rows
    segment, oos_range, window = extract_oos_event_segment(
        events, num_bars, split_policy=split_policy, bars_table=rows_table
    )
    if window is None:
        raise DataContractError(
            "OOS window unresolved during evidence build; canonical bars_table ordering required."
        )
    if len(segment) < OOS_MIN_OBSERVATIONS:
        raise DataContractError(
            f"OOS segment has {len(segment)} event(s); at least {OOS_MIN_OBSERVATIONS} observations "
            f"are required for a gate-consumable held-out OOS run (>= {OOS_MIN_RETURNS} returns). "
            f"No synthetic OOS is ever constructed."
        )

    oos_manifest, oos_fills, oos_equity = run_separate_oos_backtest(
        oos_events=segment,
        engine_config=engine_config,
        strategy_actor=strategy_actor,
        hypothesis_id=hypothesis_id,
        hypothesis_spec_sha256=hypothesis_spec_sha256,
        strategy_config_hash=strategy_config_hash,
        pyproject_toml_sha256=pyproject_toml_sha256,
        git_commit_hash=git_commit_hash,
        periods_per_year=periods_per_year,
        canonical_data_hashes=list(pit_attestation.canonical_data_hashes),
    )

    oos_returns: List[Decimal] = derive_canonical_equity_returns(oos_equity)
    if len(oos_returns) < OOS_MIN_RETURNS:
        raise DataContractError(
            f"OOS run produced {len(oos_returns)} return(s); phase 6 gate requires at least "
            f"{OOS_MIN_RETURNS} OOS observations. Run artifacts rejected, no evidence emitted."
        )

    oos_hash = _compute_canonical_series_sha256(oos_returns)
    is_hash = _compute_canonical_series_sha256(in_sample_returns)
    if is_hash == "NONE":
        raise DataContractError(
            "In-sample return series required to establish the OOS no-reuse invariant; empty IS "
            "evidence fails closed."
        )
    if oos_hash == is_hash:
        raise DataContractError(
            f"OOS return series for hypothesis '{hypothesis_id}' is byte-identical to the IS return "
            f"series ({oos_hash}); IS equity must not be reused as OOS evidence."
        )

    record = OosEvidenceRecord(
        strategy_id=strategy_id,
        hypothesis_id=hypothesis_id,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        split_policy_train_pct=str(split_policy.train_pct),
        split_policy_val_pct=str(split_policy.val_pct),
        split_policy_oos_pct=str(split_policy.oos_pct),
        split_policy_embargo_bars=split_policy.embargo_bars,
        num_bars=num_bars,
        oos_range_start=oos_range[0],
        oos_range_end=oos_range[1],
        oos_window_start_ns=window[0],
        oos_window_end_ns=window[1],
        oos_event_count=len(segment),
        oos_manifest_id=oos_manifest.manifest_id,
        oos_return_count=len(oos_returns),
        oos_return_series_sha256=oos_hash,
        in_sample_return_series_sha256=is_hash,
        canonical_data_hashes=pit_attestation.canonical_data_hashes,
        pit_attestation=pit_attestation,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    record.assert_is_oos_distinct()
    return record, oos_manifest, oos_fills, oos_equity, oos_returns