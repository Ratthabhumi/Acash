"""Adversarial tests for D5 real-input admission (no network, no authority)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from acash.data.qualification.lane_b_d5_rehearsal import (
    D5AdmissionAuthority,
    D5AdmissionVerdict,
    D5AuthorityProvenance,
    D5AuthorityStatus,
    D5DividendRecord,
    D5EvidenceLevel,
    D5InputOrigin,
    D5RawPage,
    D5RealInputBundle,
    D5RehearsalSpec,
    DatasetOrigin,
    evaluate_d5_offline_rehearsal,
    evaluate_d5_real_admission,
    expected_d5_request_sha256,
    verify_sealed_dataset,
)
from acash.data.qualification.manifest import compute_page_sha256

SESSIONS = tuple(
    date(2026, 9, 28) + timedelta(days=index) for index in range(5)
)
SYMBOLS = ("BIL", "BND", "GLD", "VOO")
NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


def _authority(**overrides: object) -> D5AdmissionAuthority:
    base: dict[str, object] = {
        "status": D5AuthorityStatus.ISSUED,
        "provenance": D5AuthorityProvenance.OPERATOR_ISSUED,
        "authority_ref": "TEST_D5_REAL_INPUT_AUTHORITY",
        "provider": "ALPACA",
        "feed": "sip",
        "timeframe": "1Day",
        "symbols": SYMBOLS,
        "start_date": SESSIONS[0],
        "end_date": SESSIONS[-1],
        "adjustments": ("raw", "split"),
        "max_http_requests": 4,
        "max_observed_bytes": 100_000,
        "issued_at_utc": datetime(2026, 10, 20, tzinfo=timezone.utc),
        "expires_at_utc": datetime(2026, 12, 31, tzinfo=timezone.utc),
        "approval_reference": "TEST_APPROVAL_REFERENCE",
    }
    base.update(overrides)
    return D5AdmissionAuthority(**base)  # type: ignore[arg-type]


def _dividends(*, pit: bool) -> tuple[D5DividendRecord, ...]:
    return (
        D5DividendRecord(
            symbol="BIL",
            ex_date=date(2026, 10, 1),
            record_date=date(2026, 10, 1),
            payable_date=date(2026, 10, 5),
            amount_per_share=Decimal("0.228000"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:bli:2026-10-01",
            pit_vintage_known=pit,
        ),
        D5DividendRecord(
            symbol="BND",
            ex_date=date(2026, 10, 1),
            record_date=date(2026, 10, 1),
            payable_date=date(2026, 10, 5),
            amount_per_share=Decimal("0.237328"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:bnd:2026-10-01",
            pit_vintage_known=pit,
        ),
        D5DividendRecord(
            symbol="VOO",
            ex_date=date(2026, 9, 30),
            record_date=date(2026, 9, 30),
            payable_date=date(2026, 10, 2),
            amount_per_share=Decimal("1.740000"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:voo:2026-09-30",
            pit_vintage_known=pit,
        ),
    )


def _page(
    authority: D5AdmissionAuthority,
    adjustment: str,
    *,
    token: str | None = None,
    next_token: str | None = None,
    sessions: Sequence[date] = SESSIONS,
    symbols: Sequence[str] = SYMBOLS,
    close: str = "100",
    hour: int = 13,
    minute: int = 30,
) -> D5RawPage:
    bars = {
        symbol: [
            {
                "t": datetime(
                    day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc
                ).isoformat(),
                "o": close,
                "h": close,
                "l": close,
                "c": close,
                "v": 1000,
            }
            for day in sessions
        ]
        for symbol in symbols
    }
    raw = json.dumps(
        {"bars": bars, "next_page_token": next_token}, separators=(",", ":")
    ).encode("utf-8")
    return D5RawPage(
        adjustment=adjustment,
        page_index=0 if token is None else 1,
        page_token=token,
        next_page_token=next_token,
        request_sha256=expected_d5_request_sha256(authority, adjustment, token),
        content_sha256=compute_page_sha256(raw),
        raw_bytes=raw,
    )


def _pages(authority: D5AdmissionAuthority) -> tuple[D5RawPage, ...]:
    return (
        _page(authority, "raw"),
        _page(authority, "split"),
    )


def _bundle(
    *,
    claimed: D5EvidenceLevel = D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED,
    origin: D5InputOrigin = D5InputOrigin.OPERATOR_ACQUISITION,
    authority: D5AdmissionAuthority | None = None,
    pages: tuple[D5RawPage, ...] | None = None,
    dividends: tuple[D5DividendRecord, ...] | None = None,
    pit_vintage_known: bool = False,
    pit_evidence_ref: str = "",
    expected_dividends: tuple[D5DividendRecord, ...] | None = None,
) -> D5RealInputBundle:
    active_authority = authority or _authority()
    active_dividends = dividends if dividends is not None else _dividends(pit=False)
    return D5RealInputBundle(
        authority=active_authority,
        origin=origin,
        pages=pages if pages is not None else _pages(active_authority),
        dividends=active_dividends,
        expected_ex_dates={
            "BND": (date(2026, 10, 1),),
            "BIL": (date(2026, 10, 1),),
            "VOO": (date(2026, 9, 30),),
        },
        claimed_level=claimed,
        pit_vintage_known=pit_vintage_known,
        pit_evidence_ref=pit_evidence_ref,
        expected_dividends=expected_dividends,
    )


def test_retrospective_real_bundle_seals_but_is_not_admitted() -> None:
    result = evaluate_d5_real_admission(_bundle(), now_utc=NOW)
    assert result.verdict is D5AdmissionVerdict.RETROSPECTIVE_ONLY
    assert result.admitted_level is D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED
    assert result.manifest["admission"]["real_data_admitted"] is False
    assert result.dataset_bytes is not None
    verify_sealed_dataset(
        result.dataset_bytes,
        result.dataset_sha256 or "",
        result.composite_sha256 or "",
    )


def test_pit_claim_without_pit_evidence_blocks() -> None:
    result = evaluate_d5_real_admission(
        _bundle(claimed=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PIT_EVIDENCE_QUALIFIED_REQUIRES_PIT_VINTAGE" in result.blockers[0]


def test_pit_bundle_with_evidence_is_admitted() -> None:
    records = _dividends(pit=True)
    result = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED,
            dividends=records,
            pit_vintage_known=True,
            pit_evidence_ref="PIT_VINTAGE_ARCHIVE:test",
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.ADMITTED
    assert result.admitted_level is D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED
    assert result.manifest["admission"]["real_data_admitted"] is True


def test_synthetic_bundle_cannot_claim_real_evidence() -> None:
    authority = _authority(provenance=D5AuthorityProvenance.TEST_FIXTURE)
    result = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED,
            origin=D5InputOrigin.SYNTHETIC_FIXTURE,
            authority=authority,
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_SYNTHETIC_INPUT_CANNOT_CLAIM_REAL_EVIDENCE" in result.blockers[0]


def test_synthetic_bundle_can_only_seal_pipeline_proof() -> None:
    authority = _authority(provenance=D5AuthorityProvenance.TEST_FIXTURE)
    records = _dividends(pit=True)
    result = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF,
            origin=D5InputOrigin.SYNTHETIC_FIXTURE,
            authority=authority,
            dividends=records,
            pit_vintage_known=True,
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.SYNTHETIC_ONLY
    assert result.admitted_level is D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF
    assert result.manifest["admission"]["real_data_admitted"] is False


def test_synthetic_bundle_cannot_claim_retrospective_real_evidence() -> None:
    authority = _authority(provenance=D5AuthorityProvenance.TEST_FIXTURE)
    result = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED,
            origin=D5InputOrigin.SYNTHETIC_FIXTURE,
            authority=authority,
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_SYNTHETIC_INPUT_CANNOT_CLAIM_REAL_EVIDENCE" in result.blockers[0]


def test_full_dataset_claim_requires_separate_record() -> None:
    result = evaluate_d5_real_admission(
        _bundle(claimed=D5EvidenceLevel.FULL_DATASET_ADMITTED),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_FULL_DATASET_ADMITTED_REQUIRES_SEPARATE_ADMISSION_RECORD" in (
        result.blockers[0]
    )


def test_source_verified_claim_is_not_d5_sealable() -> None:
    result = evaluate_d5_real_admission(
        _bundle(claimed=D5EvidenceLevel.SOURCE_VERIFIED_CANDIDATE),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_CLAIMED_LEVEL_NOT_SEALABLE" in result.blockers[0]


def test_unissued_or_expired_authority_blocks() -> None:
    for authority in (
        _authority(status=D5AuthorityStatus.UNISSUED),
        _authority(status=D5AuthorityStatus.REVOKED),
        _authority(
            issued_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
            expires_at_utc=datetime(2026, 2, 1, tzinfo=timezone.utc),
        ),
    ):
        result = evaluate_d5_real_admission(
            _bundle(authority=authority), now_utc=NOW
        )
        assert result.verdict is D5AdmissionVerdict.BLOCKED


def test_request_digest_tamper_blocks() -> None:
    authority = _authority()
    pages = list(_pages(authority))
    pages[0] = replace(pages[0], request_sha256="0" * 64)
    result = evaluate_d5_real_admission(
        _bundle(authority=authority, pages=tuple(pages)), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_REQUEST_SHA_MISMATCH" in result.blockers[0]


def test_pages_cannot_be_reused_across_authorities() -> None:
    first = _authority()
    second = _authority(authority_ref="OTHER_D5_REAL_INPUT_AUTHORITY")
    result = evaluate_d5_real_admission(
        _bundle(authority=second, pages=_pages(first)), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_REQUEST_SHA_MISMATCH" in result.blockers[0]


def test_content_digest_tamper_blocks() -> None:
    authority = _authority()
    pages = list(_pages(authority))
    pages[0] = replace(pages[0], raw_bytes=pages[0].raw_bytes + b" ")
    result = evaluate_d5_real_admission(
        _bundle(authority=authority, pages=tuple(pages)), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_CONTENT_SHA_MISMATCH" in result.blockers[0]


def test_pagination_chain_and_replay_are_blocked() -> None:
    authority = _authority()
    first = _page(authority, "raw", sessions=SESSIONS[:2])
    second = _page(
        authority,
        "raw",
        token="next-1",
        sessions=SESSIONS[2:],
    )
    broken_first = replace(first, next_page_token="next-2")
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(broken_first, second, _page(authority, "split")),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE" in result.blockers[0]


def test_missing_session_blocks() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(authority, "raw", sessions=SESSIONS[:-1]),
                _page(authority, "split", sessions=SESSIONS[:-1]),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED


def test_mixed_symbol_page_blocks() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(authority, "raw", symbols=SYMBOLS + ("MSFT",)),
                _page(authority, "split"),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "UNEXPECTED_SYMBOL" in result.blockers[0]


def test_out_of_scope_bar_blocks() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(
                    authority,
                    "raw",
                    sessions=SESSIONS + (date(2026, 10, 5),),
                ),
                _page(authority, "split"),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_BAR_OUTSIDE_SCOPE" in result.blockers[0]


def test_utc_and_new_york_session_dates_must_agree() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(
                    authority,
                    "raw",
                    sessions=(SESSIONS[1],),
                    hour=0,
                    minute=30,
                ),
                _page(authority, "split"),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_BAR_UTC_NY_DATE_MISMATCH" in result.blockers[0]


def test_byte_and_page_budgets_block() -> None:
    authority = _authority(max_observed_bytes=10)
    result = evaluate_d5_real_admission(
        _bundle(authority=authority), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_BYTE_BUDGET_EXCEEDED" in result.blockers[0]

    authority = _authority(max_http_requests=1)
    result = evaluate_d5_real_admission(
        _bundle(authority=authority), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_BUDGET_EXCEEDED" in result.blockers[0]


def test_dividend_input_must_match_expected() -> None:
    result = evaluate_d5_real_admission(
        _bundle(expected_dividends=()), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_DIVIDEND_INPUT_DOES_NOT_MATCH_EXPECTED" in result.blockers[0]


def test_missing_adjustment_pages_block() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(authority=authority, pages=(_page(authority, "raw"),)),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_MISSING_ADJUSTMENT_PAGES" in result.blockers[0]


def test_offline_rehearsal_refuses_real_admitted_origin() -> None:
    authority = _authority()
    result = evaluate_d5_offline_rehearsal(
        D5RehearsalSpec(
            origin=DatasetOrigin.REAL_ADMITTED,
            universe=authority.symbols,
            scope_start=authority.start_date,
            scope_end=authority.end_date,
            feed=authority.feed,
            timeframe=authority.timeframe,
            adjustment="raw",
            authority_ref=authority.authority_ref,
            expected_sessions=SESSIONS,
            split_bars={},
            raw_bars={},
        )
    )
    assert result.verdict.name == "BLOCKED"
    assert "REAL_ADMITTED_REQUIRES_D5_REAL_ADMISSION_BRIDGE" in result.blockers[0]
