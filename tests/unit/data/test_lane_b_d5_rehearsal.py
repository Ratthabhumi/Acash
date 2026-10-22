"""Adversarial tests for the D5 offline dataset-sealing rehearsal (synthetic)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Sequence, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.daily_models import DailyBar
from acash.data.qualification.lane_b_d5_rehearsal import (
    D5DividendRecord,
    D5OfflineVerdict,
    D5RehearsalSpec,
    DatasetOrigin,
    evaluate_d5_offline_rehearsal,
    verify_sealed_dataset,
)

SESSIONS: Tuple[date, ...] = tuple(
    date(2026, 9, 28) + timedelta(days=i) for i in range(5)
)


def _bar(day: date, close: str = "100") -> DailyBar:
    px = Decimal(close)
    return DailyBar(
        timestamp_utc=datetime(day.year, day.month, day.day, 14, 30, tzinfo=timezone.utc),
        open=px,
        high=px,
        low=px,
        close=px,
        volume=Decimal("1000"),
    )


def _bars(sessions: Sequence[date] = SESSIONS, close: str = "100") -> List[DailyBar]:
    return [_bar(day, close) for day in sessions]


def _dividends() -> List[D5DividendRecord]:
    return [
        D5DividendRecord(
            symbol="BIL",
            ex_date=date(2026, 10, 1),
            record_date=date(2026, 10, 1),
            payable_date=date(2026, 10, 5),
            amount_per_share=Decimal("0.228000"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:bli:2026-10-01",
            pit_vintage_known=True,
        ),
        D5DividendRecord(
            symbol="BND",
            ex_date=date(2026, 10, 1),
            record_date=date(2026, 10, 1),
            payable_date=date(2026, 10, 5),
            amount_per_share=Decimal("0.237328"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:bnd:2026-10-01",
            pit_vintage_known=True,
        ),
        D5DividendRecord(
            symbol="VOO",
            ex_date=date(2026, 9, 30),
            record_date=date(2026, 9, 30),
            payable_date=date(2026, 10, 2),
            amount_per_share=Decimal("1.740000"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:voo:2026-09-30",
            pit_vintage_known=True,
        ),
    ]


def _spec(**overrides: object) -> D5RehearsalSpec:
    base: Dict[str, object] = {
        "origin": DatasetOrigin.SYNTHETIC_FIXTURE,
        "universe": ("BIL", "BND", "GLD", "VOO"),
        "scope_start": SESSIONS[0],
        "scope_end": SESSIONS[-1],
        "feed": "iex",
        "timeframe": "1Day",
        "adjustment": "raw",
        "authority_ref": "SYNTHETIC_REHEARSAL_AUTHORITY:test",
        "expected_sessions": SESSIONS,
        "split_bars": {s: _bars() for s in ("BND", "BIL", "GLD", "VOO")},
        "raw_bars": {s: _bars() for s in ("BND", "BIL", "GLD", "VOO")},
        "dividends": _dividends(),
        "expected_ex_dates": {
            "BND": (date(2026, 10, 1),),
            "BIL": (date(2026, 10, 1),),
            "VOO": (date(2026, 9, 30),),
        },
    }
    base.update(overrides)
    return D5RehearsalSpec(**base)  # type: ignore[arg-type]


def test_synthetic_rehearsal_seals_and_verifies() -> None:
    result = evaluate_d5_offline_rehearsal(_spec())
    assert result.verdict is D5OfflineVerdict.READY
    assert result.dataset_bytes is not None
    assert result.dataset_sha256 and result.composite_sha256
    assert result.manifest["real_data_admitted"] is False
    verify_sealed_dataset(
        result.dataset_bytes, result.dataset_sha256, result.composite_sha256
    )


def test_deterministic_across_permuted_inputs() -> None:
    first = evaluate_d5_offline_rehearsal(_spec())
    permuted = _spec(
        dividends=list(reversed(_dividends())),
        split_bars={s: list(reversed(_bars())) for s in ("BND", "BIL", "GLD", "VOO")},
        raw_bars={s: list(reversed(_bars())) for s in ("BND", "BIL", "GLD", "VOO")},
    )
    second = evaluate_d5_offline_rehearsal(permuted)
    assert first.dataset_sha256 == second.dataset_sha256
    assert first.dataset_bytes == second.dataset_bytes


def test_tamper_detection() -> None:
    result = evaluate_d5_offline_rehearsal(_spec())
    assert result.dataset_bytes is not None and result.dataset_sha256
    tampered = bytes([result.dataset_bytes[0] ^ 1]) + result.dataset_bytes[1:]
    with pytest.raises(DataContractError, match="D5_TAMPER_DETECTED_DATASET_SHA"):
        verify_sealed_dataset(tampered, result.dataset_sha256, result.composite_sha256 or "")


def test_missing_expected_session_rejected() -> None:
    result = evaluate_d5_offline_rehearsal(_spec(expected_sessions=SESSIONS[:-1]))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "QUALIFY" in result.blockers[0]


def test_duplicate_session_rejected() -> None:
    bars = _bars() + [_bar(SESSIONS[0])]
    result = evaluate_d5_offline_rehearsal(
        _spec(split_bars={"BND": bars, "BIL": _bars(), "GLD": _bars(), "VOO": _bars()})
    )
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "COUNT_MISMATCH" in result.blockers[0]


def test_partial_source_contamination_partial() -> None:
    records = _dividends()
    records[0] = D5DividendRecord(
        symbol="BIL",
        ex_date=date(2026, 10, 1),
        record_date=date(2026, 10, 1),
        payable_date=date(2026, 10, 5),
        amount_per_share=Decimal("0.228000"),
        confirmation_status="SOURCE_PARTIAL",
        source_row_ref="",
        pit_vintage_known=True,
    )
    result = evaluate_d5_offline_rehearsal(_spec(dividends=records))
    assert result.verdict is D5OfflineVerdict.PARTIAL
    assert result.dataset_bytes is None
    assert any("PARTIAL_SOURCE_CONTAMINATION" in b for b in result.blockers)
    assert any("MISSING_SOURCE_ROW_REF" in b for b in result.blockers)


def test_unknown_pit_vintage_partial() -> None:
    records = _dividends()
    records[1] = D5DividendRecord(
        symbol="BND",
        ex_date=date(2026, 10, 1),
        record_date=date(2026, 10, 1),
        payable_date=date(2026, 10, 5),
        amount_per_share=Decimal("0.237328"),
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
        source_row_ref="synthetic:bnd:2026-10-01",
        pit_vintage_known=False,
    )
    result = evaluate_d5_offline_rehearsal(_spec(dividends=records))
    assert result.verdict is D5OfflineVerdict.PARTIAL
    assert any("PIT_VINTAGE_UNKNOWN" in b for b in result.blockers)


def test_gld_cash_dividend_rejected() -> None:
    records = _dividends() + [
        D5DividendRecord(
            symbol="GLD",
            ex_date=date(2026, 10, 1),
            record_date=date(2026, 10, 1),
            payable_date=date(2026, 10, 5),
            amount_per_share=Decimal("0.10"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:gld",
            pit_vintage_known=True,
        )
    ]
    result = evaluate_d5_offline_rehearsal(_spec(dividends=records))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "GLD_CASH_DIVIDEND_FORBIDDEN" in result.blockers[0]


def test_contradictory_amount_rejected() -> None:
    conflicting = D5DividendRecord(
        symbol="BIL",
        ex_date=date(2026, 10, 1),
        record_date=date(2026, 10, 1),
        payable_date=date(2026, 10, 5),
        amount_per_share=Decimal("0.229000"),
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
        source_row_ref="synthetic:bli:alt",
        pit_vintage_known=True,
    )
    result = evaluate_d5_offline_rehearsal(_spec(dividends=_dividends() + [conflicting]))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "DIVIDEND_CONTRADICTORY_EX_DATE" in result.blockers[0]


def test_duplicate_identical_event_rejected() -> None:
    result = evaluate_d5_offline_rehearsal(_spec(dividends=_dividends() + [_dividends()[0]]))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_DUPLICATE_EVENT" in result.blockers[0]


def test_date_order_violation_rejected() -> None:
    bad = D5DividendRecord(
        symbol="BIL",
        ex_date=date(2026, 10, 1),
        record_date=date(2026, 9, 30),
        payable_date=date(2026, 10, 5),
        amount_per_share=Decimal("0.228000"),
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
        source_row_ref="synthetic:bli",
        pit_vintage_known=True,
    )
    result = evaluate_d5_offline_rehearsal(
        _spec(dividends=[bad] + [r for r in _dividends() if r.symbol != "BIL"])
    )
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_DATE_ORDER_VIOLATION" in result.blockers[0]


def test_missing_event_coverage_partial() -> None:
    result = evaluate_d5_offline_rehearsal(
        _spec(
            expected_ex_dates={
                "BND": (date(2026, 9, 1), date(2026, 10, 1)),
                "BIL": (date(2026, 10, 1),),
                "VOO": (date(2026, 9, 30),),
            }
        )
    )
    assert result.verdict is D5OfflineVerdict.PARTIAL
    assert any("MISSING_EVENT_COVERAGE" in b for b in result.blockers)


def test_cross_symbol_dividend_swap_changes_digest() -> None:
    """Moving an amount from one symbol to another must change the seal."""
    base = _dividends()
    bil_amount = next(r for r in base if r.symbol == "BIL").amount_per_share
    bnd_amount = next(r for r in base if r.symbol == "BND").amount_per_share
    other = {"BIL": bnd_amount, "BND": bil_amount}
    swapped = [
        replace(record, amount_per_share=other[record.symbol])
        if record.symbol in other
        else record
        for record in base
    ]
    original = evaluate_d5_offline_rehearsal(_spec())
    moved = evaluate_d5_offline_rehearsal(_spec(dividends=swapped))
    assert original.verdict is D5OfflineVerdict.READY
    assert moved.verdict is D5OfflineVerdict.READY, moved.blockers
    assert original.dataset_sha256 != moved.dataset_sha256


def test_ohlc_fields_bound_in_digest() -> None:
    """Open/high/low are economically material and must move the seal."""
    raw = {s: _bars() for s in ("BIL", "BND", "GLD", "VOO")}
    altered = list(raw["BND"])
    altered[0] = DailyBar(
        timestamp_utc=altered[0].timestamp_utc,
        open=Decimal("99"),
        high=Decimal("101"),
        low=Decimal("98"),
        close=Decimal("100"),
        volume=Decimal("1000"),
    )
    raw["BND"] = altered
    original = evaluate_d5_offline_rehearsal(_spec())
    changed = evaluate_d5_offline_rehearsal(_spec(raw_bars=raw))
    assert changed.verdict is D5OfflineVerdict.READY
    assert original.dataset_sha256 != changed.dataset_sha256


def test_undeclared_event_coverage_rejected() -> None:
    result = evaluate_d5_offline_rehearsal(
        _spec(expected_ex_dates={"BND": (date(2026, 10, 1),)})
    )
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "UNDECLARED_EVENT_COVERAGE" in result.blockers[0]


def test_payload_binds_semantic_fields() -> None:
    result = evaluate_d5_offline_rehearsal(_spec())
    assert result.dataset_bytes is not None
    payload = json.loads(result.dataset_bytes)
    assert payload["share_basis"] == "PER_SHARE"
    assert payload["price_semantics"] == "RAW_UNADJUSTED_OHLCV"
    assert payload["time_basis"] == "UTC_DAILY_BAR"
    assert payload["sessions_authority"] == "CALLER_SUPPLIED_SYNTHETIC"
    assert {
        "symbol",
        "ex_date",
        "record_date",
        "payable_date",
        "cash_distribution",
    } <= set(payload["dividends"][0])
    row = payload["series"]["BND"]["raw"][0]
    assert {"session", "open", "high", "low", "close", "volume"} <= set(row)


def test_real_candidate_cannot_seal_without_admission() -> None:
    result = evaluate_d5_offline_rehearsal(_spec(origin=DatasetOrigin.REAL_CANDIDATE))
    assert result.verdict is D5OfflineVerdict.PARTIAL
    assert result.dataset_bytes is None
    assert result.dataset_sha256 is None
    assert "REAL_CANDIDATE_SEALING_REQUIRES_AUTHORIZED_ADMISSION" in result.blockers


def test_unapproved_and_excluded_universe_rejected() -> None:
    spy = evaluate_d5_offline_rehearsal(
        _spec(universe=("BIL", "BND", "GLD", "SPY", "VOO"))
    )
    assert spy.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_UNAPPROVED_UNIVERSE" in spy.blockers[0]

    gldm = evaluate_d5_offline_rehearsal(
        _spec(universe=("BIL", "BND", "GLD", "GLDM", "VOO"))
    )
    assert gldm.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_EXCLUDED_SYMBOL_PRESENT" in gldm.blockers[0]


def test_wrong_request_identity_rejected() -> None:
    result = evaluate_d5_offline_rehearsal(_spec(feed="polygon"))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_UNAPPROVED_FEED" in result.blockers[0]


def test_missing_approval_lineage_rejected() -> None:
    result = evaluate_d5_offline_rehearsal(_spec(authority_ref="  "))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_MISSING_APPROVAL_LINEAGE" in result.blockers[0]


def test_payable_outside_window_allowed_and_recorded() -> None:
    result = evaluate_d5_offline_rehearsal(_spec())
    assert result.verdict is D5OfflineVerdict.READY
    assert result.manifest["payable_outside_scope"] == [
        "BIL:2026-10-01",
        "BND:2026-10-01",
    ]


def test_nonpositive_amount_rejected() -> None:
    records = _dividends()
    records[0] = D5DividendRecord(
        symbol="BIL",
        ex_date=date(2026, 10, 1),
        record_date=date(2026, 10, 1),
        payable_date=date(2026, 10, 5),
        amount_per_share=Decimal("0"),
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
        source_row_ref="synthetic:bli",
        pit_vintage_known=True,
    )
    result = evaluate_d5_offline_rehearsal(_spec(dividends=records))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "NONPOSITIVE" in result.blockers[0]


def test_event_outside_scope_rejected() -> None:
    records = _dividends()
    records[0] = D5DividendRecord(
        symbol="BIL",
        ex_date=date(2026, 9, 1),
        record_date=date(2026, 9, 1),
        payable_date=date(2026, 9, 5),
        amount_per_share=Decimal("0.228000"),
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
        source_row_ref="synthetic:bli",
        pit_vintage_known=True,
    )
    result = evaluate_d5_offline_rehearsal(_spec(dividends=records))
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_EVENT_OUTSIDE_SCOPE" in result.blockers[0]


def test_missing_series_rejected() -> None:
    result = evaluate_d5_offline_rehearsal(
        _spec(split_bars={"BND": _bars(), "BIL": _bars(), "GLD": _bars()})
    )
    assert result.verdict is D5OfflineVerdict.BLOCKED
    assert "D5_MISSING_SERIES" in result.blockers[0]


def test_synthetic_label_is_embedded() -> None:
    result = evaluate_d5_offline_rehearsal(_spec())
    assert result.dataset_bytes is not None
    assert b"SYNTHETIC_FIXTURE_NOT_MARKET_HISTORY" in result.dataset_bytes
