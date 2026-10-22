"""D5 offline dataset-sealing rehearsal (SYNTHETIC FIXTURE, unissued).

This module does NOT issue Lane A/B authority, does NOT acquire market data and
does NOT substitute for real-data admission. It composes the canonical HYP_009
qualification/accounting checks with the canonical manifest hashing helpers to
prove that the deterministic dataset-sealing contract is fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.qualification.daily_models import DailyBar
from acash.data.qualification.manifest import (
    compute_framed_composite_sha256,
    compute_page_sha256,
)
from acash.research.hyp_009.qualification import (
    qualify_bar_series,
    qualify_dividends,
    require_no_unbound_splits,
)

ALLOWED_D5_SYMBOLS: tuple[str, ...] = ("BND", "BIL", "GLD", "VOO")
EXCLUDED_D5_SYMBOLS: frozenset[str] = frozenset({"GLDM"})
ALLOWED_D5_FEEDS: frozenset[str] = frozenset({"iex", "sip"})
ALLOWED_D5_TIMEFRAMES: frozenset[str] = frozenset({"1Day"})
ALLOWED_D5_ADJUSTMENTS: frozenset[str] = frozenset({"raw"})
ALLOWED_D5_CURRENCIES: frozenset[str] = frozenset({"USD"})
CONFIRMED_CANDIDATE: str = "SOURCE_CONFIRMED_CANDIDATE"
DATASET_SCHEMA: str = "ACASH_D5_SEALED_DATASET_V1"
SYNTHETIC_LABEL: str = "SYNTHETIC_FIXTURE_NOT_MARKET_HISTORY"


class D5OfflineVerdict(str, Enum):
    READY = "D5_OFFLINE_PIPELINE_READY"
    PARTIAL = "D5_OFFLINE_PIPELINE_PARTIAL"
    BLOCKED = "D5_OFFLINE_PIPELINE_BLOCKED"


class DatasetOrigin(str, Enum):
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    REAL_CANDIDATE = "REAL_CANDIDATE"


@dataclass(frozen=True)
class D5DividendRecord:
    symbol: str
    ex_date: date
    record_date: date
    payable_date: date
    amount_per_share: Decimal
    confirmation_status: str
    source_row_ref: str = ""
    pit_vintage_known: bool = False
    currency: str = "USD"


@dataclass(frozen=True)
class D5RehearsalSpec:
    origin: DatasetOrigin
    universe: tuple[str, ...]
    scope_start: date
    scope_end: date
    feed: str
    timeframe: str
    adjustment: str
    authority_ref: str
    expected_sessions: tuple[date, ...]
    split_bars: Mapping[str, Sequence[DailyBar]]
    raw_bars: Mapping[str, Sequence[DailyBar]]
    dividends: Sequence[D5DividendRecord] = ()
    expected_ex_dates: Mapping[str, tuple[date, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class D5RehearsalResult:
    verdict: D5OfflineVerdict
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    manifest: Mapping[str, Any]
    dataset_bytes: bytes | None = None
    dataset_sha256: str | None = None
    composite_sha256: str | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DataContractError(message)


def _identity(spec: D5RehearsalSpec) -> dict[str, Any]:
    return {
        "symbols": list(spec.universe),
        "timeframe": spec.timeframe,
        "scope_start": spec.scope_start.isoformat(),
        "scope_end": spec.scope_end.isoformat(),
        "adjustment": spec.adjustment,
        "feed": spec.feed,
        "sort": "asc",
        "limit": 1000,
        "currency": "USD",
    }


def _validate_identity(spec: D5RehearsalSpec) -> None:
    universe = tuple(spec.universe)
    _require(len(universe) > 0, "D5_UNIVERSE_EMPTY.")
    _require(universe == tuple(sorted(universe)), "D5_UNIVERSE_NOT_SORTED.")
    _require(len(set(universe)) == len(universe), "D5_UNIVERSE_DUPLICATE.")
    _require(
        not (set(universe) & EXCLUDED_D5_SYMBOLS),
        f"D5_EXCLUDED_SYMBOL_PRESENT: {sorted(set(universe) & EXCLUDED_D5_SYMBOLS)}.",
    )
    _require(
        set(universe) <= set(ALLOWED_D5_SYMBOLS),
        f"D5_UNAPPROVED_UNIVERSE: {sorted(set(universe) - set(ALLOWED_D5_SYMBOLS))}.",
    )
    _require(spec.scope_start <= spec.scope_end, "D5_SCOPE_INVERTED.")
    _require(spec.feed in ALLOWED_D5_FEEDS, f"D5_UNAPPROVED_FEED: {spec.feed}.")
    _require(
        spec.timeframe in ALLOWED_D5_TIMEFRAMES,
        f"D5_UNAPPROVED_TIMEFRAME: {spec.timeframe}.",
    )
    _require(
        spec.adjustment in ALLOWED_D5_ADJUSTMENTS,
        f"D5_UNAPPROVED_ADJUSTMENT: {spec.adjustment}.",
    )
    _require(bool(spec.authority_ref.strip()), "D5_MISSING_APPROVAL_LINEAGE.")


def _validate_calendar(spec: D5RehearsalSpec) -> None:
    expected = tuple(spec.expected_sessions)
    _require(len(expected) > 0, "D5_EXPECTED_SESSIONS_EMPTY.")
    _require(list(expected) == sorted(set(expected)), "D5_EXPECTED_SESSIONS_CORRUPT.")
    for symbol in spec.universe:
        split = spec.split_bars.get(symbol)
        raw = spec.raw_bars.get(symbol)
        _require(
            split is not None and raw is not None,
            f"D5_MISSING_SERIES: {symbol}.",
        )
        qualify_bar_series(list(expected), list(split or ()), list(raw or ()))
        require_no_unbound_splits(
            list(expected),
            {bar.timestamp_utc.date(): bar.close for bar in (split or ())},
            {bar.timestamp_utc.date(): bar.close for bar in (raw or ())},
        )
    for symbol in spec.split_bars:
        _require(symbol in spec.universe, f"D5_UNDECLARED_SERIES_SYMBOL: {symbol}.")


def _validate_dividends(spec: D5RehearsalSpec) -> tuple[list[dict[str, Any]], list[str]]:
    seen_amounts: dict[tuple[str, date], Decimal] = {}
    events: list[dict[str, Any]] = []
    payable_outside: list[str] = []
    for record in spec.dividends:
        _require(
            record.symbol in spec.universe,
            f"D5_DIVIDEND_UNDECLARED_SYMBOL: {record.symbol}.",
        )
        _require(
            record.symbol != "GLD",
            "D5_GLD_CASH_DIVIDEND_FORBIDDEN: GLD has NO_CASH_DISTRIBUTION_ENTITLEMENT.",
        )
        _require(
            record.symbol not in EXCLUDED_D5_SYMBOLS,
            f"D5_EXCLUDED_SYMBOL_EVENT: {record.symbol}.",
        )
        _require(
            record.currency in ALLOWED_D5_CURRENCIES,
            f"D5_UNSUPPORTED_CURRENCY: {record.currency}.",
        )
        _require(
            record.amount_per_share.is_finite() and record.amount_per_share > Decimal("0"),
            f"D5_NONPOSITIVE_OR_NONFINITE_AMOUNT: {record.symbol} {record.ex_date}.",
        )
        _require(
            record.ex_date <= record.record_date <= record.payable_date,
            f"D5_DATE_ORDER_VIOLATION: {record.symbol} {record.ex_date}.",
        )
        key = (record.symbol, record.ex_date)
        if key in seen_amounts:
            _require(
                seen_amounts[key] != record.amount_per_share,
                f"D5_DUPLICATE_EVENT: {record.symbol} {record.ex_date}.",
            )
        seen_amounts[key] = record.amount_per_share
        _require(
            spec.scope_start <= record.ex_date <= spec.scope_end,
            f"D5_EVENT_OUTSIDE_SCOPE: {record.symbol} {record.ex_date}.",
        )
        if record.payable_date > spec.scope_end:
            payable_outside.append(f"{record.symbol}:{record.ex_date.isoformat()}")
        events.append(
            {
                "ex_date": record.ex_date.isoformat(),
                "payable_date": record.payable_date.isoformat(),
                "cash_distribution": format(record.amount_per_share, "f"),
            }
        )
    events.sort(key=lambda item: (str(item["ex_date"]), str(item["cash_distribution"])))
    return events, sorted(payable_outside)


def _qualify_dividend_authority(spec: D5RehearsalSpec) -> list[str]:
    blockers: list[str] = []
    for symbol in spec.universe:
        symbol_records = [r for r in spec.dividends if r.symbol == symbol]
        for record in symbol_records:
            if record.confirmation_status != CONFIRMED_CANDIDATE:
                blockers.append(
                    f"PARTIAL_SOURCE_CONTAMINATION: {symbol} {record.ex_date} "
                    f"{record.confirmation_status}."
                )
            if not record.source_row_ref.strip():
                blockers.append(f"MISSING_SOURCE_ROW_REF: {symbol} {record.ex_date}.")
            if not record.pit_vintage_known:
                blockers.append(f"PIT_VINTAGE_UNKNOWN: {symbol} {record.ex_date}.")
        if symbol == "GLD":
            continue
        expected = spec.expected_ex_dates.get(symbol)
        if expected is None:
            continue
        actual = {record.ex_date for record in symbol_records}
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        if missing:
            blockers.append(f"MISSING_EVENT_COVERAGE: {symbol} {missing}.")
        if extra:
            blockers.append(f"UNDECLARED_EVENT: {symbol} {extra}.")
    return blockers


def _validate_dividend_events(spec: D5RehearsalSpec) -> int:
    count = 0
    for symbol in spec.universe:
        records = [
            {
                "ex_date": r.ex_date.isoformat(),
                "payable_date": r.payable_date.isoformat(),
                "cash_distribution": format(r.amount_per_share, "f"),
            }
            for r in spec.dividends
            if r.symbol == symbol
        ]
        events = qualify_dividends(records, spec.scope_start, spec.scope_end)
        count += len(events)
    return count


def _dataset_payload(
    spec: D5RehearsalSpec, events: list[dict[str, Any]], payable_outside: list[str]
) -> dict[str, Any]:
    series: dict[str, Any] = {}
    for symbol in spec.universe:
        split = sorted(spec.split_bars.get(symbol, ()), key=lambda b: b.timestamp_utc)
        raw = sorted(spec.raw_bars.get(symbol, ()), key=lambda b: b.timestamp_utc)
        series[symbol] = {
            "split": [
                {
                    "session": bar.timestamp_utc.date().isoformat(),
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in split
            ],
            "raw": [
                {
                    "session": bar.timestamp_utc.date().isoformat(),
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in raw
            ],
        }
    return {
        "schema": DATASET_SCHEMA,
        "label": SYNTHETIC_LABEL if spec.origin is DatasetOrigin.SYNTHETIC_FIXTURE else "CANDIDATE",
        "origin": spec.origin.value,
        "identity": _identity(spec),
        "authority_ref": spec.authority_ref,
        "sessions": [day.isoformat() for day in spec.expected_sessions],
        "series": series,
        "dividends": events,
        "payable_outside_scope": payable_outside,
        "pit_vintage_known": all(r.pit_vintage_known for r in spec.dividends),
    }


def evaluate_d5_offline_rehearsal(spec: D5RehearsalSpec) -> D5RehearsalResult:
    """Run the fail-closed rehearsal and seal only synthetic/fully-qualified input."""
    checks: dict[str, bool] = {}
    try:
        _validate_identity(spec)
        checks["request_identity"] = True
        _validate_calendar(spec)
        checks["price_calendar_alignment"] = True
        checks["no_unbound_split"] = True
        _validate_dividend_events(spec)
        events, payable_outside = _validate_dividends(spec)
        checks["dividend_events"] = True
        blockers = _qualify_dividend_authority(spec)
        checks["source_authority"] = not blockers
    except DataContractError as exc:
        return D5RehearsalResult(
            verdict=D5OfflineVerdict.BLOCKED,
            checks=checks,
            blockers=(str(exc),),
            manifest={"schema": DATASET_SCHEMA, "blocked": True},
        )

    if checks["source_authority"] and not blockers:
        payload = _dataset_payload(spec, events, payable_outside)
        dataset_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        dataset_sha = CanonicalConfigSerializer.compute_sha256(payload)
        page_sha = compute_page_sha256(dataset_bytes)
        composite_sha = compute_framed_composite_sha256([dataset_bytes])
        _require(page_sha == dataset_sha, "D5_PAGE_SHA_MISMATCH.")
        manifest = {
            "schema": DATASET_SCHEMA,
            "dataset_sha256": dataset_sha,
            "composite_sha256": composite_sha,
            "page_shas": [page_sha],
            "identity": _identity(spec),
            "authority_ref": spec.authority_ref,
            "session_count": len(spec.expected_sessions),
            "dividend_count": len(events),
            "payable_outside_scope": payable_outside,
            "origin": spec.origin.value,
            "real_data_admitted": False,
            "blockers": [],
        }
        checks["dataset_sealed"] = True
        return D5RehearsalResult(
            verdict=D5OfflineVerdict.READY,
            checks=checks,
            blockers=(),
            manifest=manifest,
            dataset_bytes=dataset_bytes,
            dataset_sha256=dataset_sha,
            composite_sha256=composite_sha,
        )

    return D5RehearsalResult(
        verdict=D5OfflineVerdict.PARTIAL,
        checks=checks,
        blockers=tuple(blockers),
        manifest={"schema": DATASET_SCHEMA, "sealed": False, "blockers": list(blockers)},
    )


def verify_sealed_dataset(
    dataset_bytes: bytes,
    expected_sha256: str,
    expected_composite_sha256: str,
) -> None:
    """Fail closed on any byte-level or framing tamper."""
    actual_sha = compute_page_sha256(dataset_bytes)
    _require(actual_sha == expected_sha256, "D5_TAMPER_DETECTED_DATASET_SHA.")
    actual_composite = compute_framed_composite_sha256([dataset_bytes])
    _require(
        actual_composite == expected_composite_sha256,
        "D5_TAMPER_DETECTED_COMPOSITE_SHA.",
    )


__all__ = [
    "ALLOWED_D5_SYMBOLS",
    "EXCLUDED_D5_SYMBOLS",
    "D5DividendRecord",
    "D5OfflineVerdict",
    "D5RehearsalResult",
    "D5RehearsalSpec",
    "DatasetOrigin",
    "evaluate_d5_offline_rehearsal",
    "verify_sealed_dataset",
]
