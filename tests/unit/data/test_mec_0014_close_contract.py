"""Unit tests for MEC-0014 Previous-Close / Auction Data Contract Qualification."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.mec_0014_close_contract import (
    IS_END_DATE,
    IS_START_DATE,
    OOS_FORBIDDEN_DATE,
    AuctionRecord,
    CloseAuthorityClassification,
    ClosingTradeRecord,
    DailyBarRecord,
    MinuteBarRecord,
    assert_in_sample_probe_date,
    build_mec_0014_manifest,
    compare_session_close_contract,
    compute_pairwise_diagnostic,
    parse_auction_response,
    parse_daily_bar_response,
    parse_minute_bars_response,
    parse_trades_response,
    select_mec_0014_probe_dates,
)


def test_gate1_deterministic_six_date_ca1_selection() -> None:
    """Verify deterministic selection of first regular CA-1 session in June for 2017–2022."""
    cal = NyseCa1Calendar()
    selected = select_mec_0014_probe_dates(calendar=cal)

    expected = [
        date(2017, 6, 1),  # Thursday
        date(2018, 6, 1),  # Friday
        date(2019, 6, 3),  # Monday (June 1 was Saturday)
        date(2020, 6, 1),  # Monday
        date(2021, 6, 1),  # Tuesday
        date(2022, 6, 1),  # Wednesday
    ]
    assert selected == expected
    assert len(selected) == 6
    for d in selected:
        sess = cal.get_session(d)
        assert sess.expected_minute_count == 390
        assert sess.session_type.value == "REGULAR"


def test_gate2_hard_oos_rejection() -> None:
    """Verify that any date >= 2023-01-01 strictly fails closed."""
    with pytest.raises(DataContractError, match="violates OOS boundary"):
        assert_in_sample_probe_date(date(2023, 1, 1))

    with pytest.raises(DataContractError, match="violates OOS boundary"):
        assert_in_sample_probe_date(date(2024, 6, 3))

    with pytest.raises(DataContractError, match="outside authorized IS window"):
        assert_in_sample_probe_date(date(2016, 12, 31))

    # Selection function rejects OOS years (e.g. 2023)
    with pytest.raises(DataContractError, match="violates OOS boundary"):
        select_mec_0014_probe_dates(years=[2023])

    # Selection function rejects out-of-range years (< 2013 or > 2026)
    with pytest.raises(DataContractError, match="outside CA-1 calendar authority range"):
        select_mec_0014_probe_dates(years=[2012])


def test_gate3_secret_non_leakage() -> None:
    """Verify that manifest and diagnostics never serialize credentials or tokens."""
    manifest = build_mec_0014_manifest(
        source_git_sha="0992de360defaca2451214b882277b96a46bd612",
        selected_six_dates=["2017-06-01", "2018-06-01"],
        alpaca_endpoints=["/v2/stocks/{symbol}/auctions"],
        response_schemas={"auctions": ["t", "p", "s", "x", "c"]},
        raw_evidence_aggregate_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        comparison_result_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        previous_close_authority=CloseAuthorityClassification.RESOLVED_AUCTION_AUTHORITY,
        target_close_authority=CloseAuthorityClassification.RESOLVED_AUCTION_AUTHORITY,
        generated_at_utc="2026-09-19T00:00:00Z",
    )
    serialized = str(manifest).lower()
    for forbidden in ["api_key", "secret", "token", "password", "apca-api-key"]:
        assert forbidden not in serialized


def test_gate4_auction_response_parsing() -> None:
    """Verify parsing of closing ('c') and opening ('o') auctions with multi-venue records."""
    payload = {
        "auctions": [
            {
                "d": "2017-06-01",
                "c": [
                    {"c": "6", "p": 243.36, "s": 3929774, "t": "2017-06-01T20:00:00.104Z", "x": "P"},
                    {"c": "6", "p": 243.30, "s": 1695, "t": "2017-06-01T20:00:00.305Z", "x": "T"},
                ],
                "o": [
                    {"c": "O", "p": 241.97, "s": 158783, "t": "2017-06-01T13:30:00.182Z", "x": "P"},
                ],
            }
        ],
        "symbol": "SPY",
    }
    records = parse_auction_response(payload)
    assert len(records) == 3

    closing = [r for r in records if r.auction_type == "c"]
    assert len(closing) == 2
    assert closing[0].exchange == "P"
    assert closing[0].price == Decimal("243.36")
    assert closing[0].size == 3929774
    assert closing[0].condition == "6"

    assert closing[1].exchange == "T"
    assert closing[1].price == Decimal("243.30")
    assert closing[1].size == 1695


def test_gate5_daily_bar_parsing() -> None:
    """Verify parsing of SIP daily bar payload."""
    payload = {
        "bars": [
            {
                "t": "2017-06-01T04:00:00Z",
                "o": 241.96,
                "h": 243.38,
                "l": 241.64,
                "c": 243.30,
                "v": 72957360,
                "n": 230852,
                "vw": 242.589129,
            }
        ],
        "symbol": "SPY",
    }
    record = parse_daily_bar_response(payload, symbol="SPY")
    assert record.close == Decimal("243.30")
    assert record.open == Decimal("241.96")
    assert record.volume == 72957360
    assert record.trade_count == 230852
    assert record.vwap == Decimal("242.589129")


def test_gate6_raw_trade_condition_parsing() -> None:
    """Verify trade condition parsing for 6, M, 9, X."""
    payload = {
        "trades": [
            {"t": "2017-06-01T20:00:00.104Z", "p": 243.36, "s": 3929774, "x": "P", "c": [" ", "6"], "z": "B", "i": 1001},
            {"t": "2017-06-01T20:00:00.305Z", "p": 243.30, "s": 1695, "x": "T", "c": [" ", "6", "X"], "z": "B", "i": 1002},
            {"t": "2017-06-01T20:00:01.000Z", "p": 243.35, "s": 500, "x": "P", "c": ["M"], "z": "B", "i": 1003},
            {"t": "2017-06-01T20:05:00.000Z", "p": 243.36, "s": 100, "x": "P", "c": ["9"], "z": "B", "i": 1004},
        ],
        "symbol": "SPY",
    }
    trades = parse_trades_response(payload, symbol="SPY")
    assert len(trades) == 4
    assert trades[0].conditions == ["6"]
    assert trades[1].conditions == ["6", "X"]
    assert trades[2].conditions == ["M"]
    assert trades[3].conditions == ["9"]


def test_gate7_multiple_closing_candidates_preserved() -> None:
    """Verify that multiple closing candidates are preserved and unique NYSE Arca x=P, c=6 is selected."""
    session_d = date(2017, 6, 1)
    daily_b = DailyBarRecord(
        timestamp_utc="2017-06-01T04:00:00Z",
        open=Decimal("241.96"),
        high=Decimal("243.38"),
        low=Decimal("241.64"),
        close=Decimal("243.30"),
        volume=72957360,
        trade_count=230852,
        vwap=Decimal("242.589"),
    )
    minute_bars = [
        MinuteBarRecord(
            timestamp_utc="2017-06-01T19:59:00Z",  # 15:59 ET
            open=Decimal("243.15"),
            high=Decimal("243.34"),
            low=Decimal("243.15"),
            close=Decimal("243.32"),
            volume=2143147,
            trade_count=5689,
            vwap=Decimal("243.21"),
        ),
        MinuteBarRecord(
            timestamp_utc="2017-06-01T20:00:00Z",  # 16:00 ET
            open=Decimal("243.33"),
            high=Decimal("243.43"),
            low=Decimal("243.22"),
            close=Decimal("243.23"),
            volume=9461783,
            trade_count=1363,
            vwap=Decimal("243.35"),
        ),
    ]
    auctions = [
        AuctionRecord("2017-06-01T20:00:00.104Z", Decimal("243.36"), 3929774, "P", "6", "c"),
        AuctionRecord("2017-06-01T20:00:00.305Z", Decimal("243.30"), 1695, "T", "6", "c"),
    ]
    trades = [
        ClosingTradeRecord("2017-06-01T20:00:00.104Z", Decimal("243.36"), 3929774, "P", ["6"], "B", 101),
        ClosingTradeRecord("2017-06-01T20:00:00.305Z", Decimal("243.30"), 1695, "T", ["6", "X"], "B", 102),
    ]

    res = compare_session_close_contract(session_d, daily_b, minute_bars, auctions, trades)

    # Verify both venues are preserved in candidate diagnostics
    assert len(res.auction_closing_candidates) == 2
    venues = {c["exchange"] for c in res.auction_closing_candidates}
    assert venues == {"P", "T"}

    # Verify primary auction selection strictly selected NYSE Arca x=P, c=6 price
    assert res.comparisons["daily_vs_auction"]["price_b"] == "243.36"

    # Verify 15:59 and 16:00 are preserved
    assert res.p_1559_close == Decimal("243.32")
    assert res.p_1600_minute_close == Decimal("243.23")
    assert res.p_daily_close == Decimal("243.30")


def test_gate8_no_silent_1559_substitution() -> None:
    """Verify that when 15:59 differs from daily close or auction, exact equality is False."""
    diag = compute_pairwise_diagnostic("daily", Decimal("243.30"), "1559", Decimal("243.32"))
    assert diag["exact_equality"] is False
    assert diag["abs_difference"] == "0.02"
    assert Decimal(diag["difference_bps"]) > Decimal("0.8")


def test_gate9_basis_point_diagnostic_correctness() -> None:
    """Verify exact basis points formula: abs(p1 - p2) / p1 * 10000."""
    p1 = Decimal("100.00")
    p2 = Decimal("100.05")
    diag = compute_pairwise_diagnostic("A", p1, "B", p2)
    assert diag["exact_equality"] is False
    assert diag["abs_difference"] == "0.05"
    assert diag["difference_bps"] == "5.0000"

    # Exact equality
    diag_eq = compute_pairwise_diagnostic("A", p1, "B", Decimal("100.00"))
    assert diag_eq["exact_equality"] is True
    assert diag_eq["difference_bps"] == "0.0000"


def test_gate10_deterministic_manifest_structure() -> None:
    """Verify manifest serialization format and required keys."""
    manifest = build_mec_0014_manifest(
        source_git_sha="0992de3",
        selected_six_dates=["2017-06-01"],
        alpaca_endpoints=["/v2/stocks/{symbol}/auctions", "/v2/stocks/{symbol}/bars"],
        response_schemas={"auctions": ["p", "s"]},
        raw_evidence_aggregate_hash="hash_raw",
        comparison_result_hash="hash_comp",
        previous_close_authority=CloseAuthorityClassification.RESOLVED_FOR_SPY_TO_PRIMARY_LISTING_OFFICIAL_CLOSE,
        target_close_authority=CloseAuthorityClassification.RESOLVED_AUCTION_AUTHORITY,
        generated_at_utc="2026-09-19T07:00:00Z",
    )
    assert manifest["manifest_type"] == "MEC_0014_CLOSE_AUCTION_CONTRACT_MANIFEST"
    assert manifest["previous_close_authority"] == "RESOLVED_FOR_SPY_TO_PRIMARY_LISTING_OFFICIAL_CLOSE"
    assert manifest["feed"] == "sip"
    assert manifest["adjustment"] == "raw"
    assert manifest["governance_invariants"]["OOS_accessed"] is False
    assert manifest["governance_invariants"]["capital_authority_usd"] == "0.00"


def test_gate11_missing_primary_arca_auction_fails_closed() -> None:
    """Verify that absence of qualifying NYSE Arca x=P, c=6 auction raises DataContractError."""
    session_d = date(2017, 6, 1)
    daily_b = DailyBarRecord(
        "2017-06-01T04:00:00Z",
        Decimal("241.96"),
        Decimal("243.38"),
        Decimal("241.64"),
        Decimal("243.30"),
        72957360,
        230852,
        Decimal("242.589"),
    )
    minute_bars = [
        MinuteBarRecord(
            "2017-06-01T19:59:00Z",
            Decimal("243.15"),
            Decimal("243.34"),
            Decimal("243.15"),
            Decimal("243.32"),
            2143147,
            5689,
            Decimal("243.21"),
        )
    ]
    trades: list[ClosingTradeRecord] = []

    # Completely empty auctions
    with pytest.raises(DataContractError, match="Zero qualifying NYSE Arca \\(x=P, c=6\\)"):
        compare_session_close_contract(session_d, daily_b, minute_bars, [], trades)


def test_gate12_nasdaq_only_closing_auction_fails_closed() -> None:
    """Verify that secondary venue closing auction (NASDAQ T, c=6) cannot be substituted for Arca."""
    session_d = date(2017, 6, 1)
    daily_b = DailyBarRecord(
        "2017-06-01T04:00:00Z",
        Decimal("241.96"),
        Decimal("243.38"),
        Decimal("241.64"),
        Decimal("243.30"),
        72957360,
        230852,
        Decimal("242.589"),
    )
    minute_bars = [
        MinuteBarRecord(
            "2017-06-01T19:59:00Z",
            Decimal("243.15"),
            Decimal("243.34"),
            Decimal("243.15"),
            Decimal("243.32"),
            2143147,
            5689,
            Decimal("243.21"),
        )
    ]
    trades: list[ClosingTradeRecord] = []

    # Only NASDAQ auction present
    nasdaq_only = [
        AuctionRecord("2017-06-01T20:00:00.305Z", Decimal("243.30"), 1695, "T", "6", "c")
    ]
    with pytest.raises(DataContractError, match="Zero qualifying NYSE Arca \\(x=P, c=6\\)"):
        compare_session_close_contract(session_d, daily_b, minute_bars, nasdaq_only, trades)


def test_gate13_ambiguous_multiple_arca_auctions_fails_closed() -> None:
    """Verify that ambiguous multiple qualifying x=P, c=6 records strictly fail closed."""
    session_d = date(2017, 6, 1)
    daily_b = DailyBarRecord(
        "2017-06-01T04:00:00Z",
        Decimal("241.96"),
        Decimal("243.38"),
        Decimal("241.64"),
        Decimal("243.30"),
        72957360,
        230852,
        Decimal("242.589"),
    )
    minute_bars = [
        MinuteBarRecord(
            "2017-06-01T19:59:00Z",
            Decimal("243.15"),
            Decimal("243.34"),
            Decimal("243.15"),
            Decimal("243.32"),
            2143147,
            5689,
            Decimal("243.21"),
        )
    ]
    trades: list[ClosingTradeRecord] = []

    # Two competing Arca c=6 records
    multiple_arca = [
        AuctionRecord("2017-06-01T20:00:00.100Z", Decimal("243.36"), 2000000, "P", "6", "c"),
        AuctionRecord("2017-06-01T20:00:00.104Z", Decimal("243.38"), 1929774, "P", "6", "c"),
    ]
    with pytest.raises(DataContractError, match="Ambiguous multiple \\(2\\) qualifying NYSE Arca"):
        compare_session_close_contract(session_d, daily_b, minute_bars, multiple_arca, trades)


def test_gate14_no_silent_daily_or_1559_substitution_when_auction_missing() -> None:
    """Verify that neither Daily Bar Close nor 15:59 close is ever substituted when auction is absent."""
    session_d = date(2017, 6, 1)
    daily_b = DailyBarRecord(
        "2017-06-01T04:00:00Z",
        Decimal("241.96"),
        Decimal("243.38"),
        Decimal("241.64"),
        Decimal("243.30"),
        72957360,
        230852,
        Decimal("242.589"),
    )
    minute_bars = [
        MinuteBarRecord(
            "2017-06-01T19:59:00Z",
            Decimal("243.15"),
            Decimal("243.34"),
            Decimal("243.15"),
            Decimal("243.32"),
            2143147,
            5689,
            Decimal("243.21"),
        ),
        MinuteBarRecord(
            "2017-06-01T20:00:00Z",
            Decimal("243.33"),
            Decimal("243.43"),
            Decimal("243.22"),
            Decimal("243.23"),
            9461783,
            1363,
            Decimal("243.35"),
        ),
    ]
    # In an invalid configuration where auction is missing, it must raise DataContractError,
    # proving it NEVER silently substitutes daily_b.close ($243.30) or p_1559 ($243.32)
    with pytest.raises(DataContractError):
        compare_session_close_contract(session_d, daily_b, minute_bars, [], [])


def test_gate15_rejected_legacy_classification_absent() -> None:
    """Verify that PARTIALLY_RESOLVED_MULTIPLE_EQUIVALENT_AUTHORITIES is removed from active code."""
    assert not hasattr(
        CloseAuthorityClassification, "PARTIALLY_RESOLVED_MULTIPLE_EQUIVALENT_AUTHORITIES"
    )
    all_enum_values = [e.value for e in CloseAuthorityClassification]
    assert "PARTIALLY_RESOLVED_MULTIPLE_EQUIVALENT_AUTHORITIES" not in all_enum_values
