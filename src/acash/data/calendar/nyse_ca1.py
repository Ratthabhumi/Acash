"""NYSE Official US Equity Trading Calendar Engine (CA-1 Sovereign Authority).

This module implements the executable CA-1 calendar authority covering historical years
2013 through 2026, as ratified in Phase 14 governance records
(cand_free_macro_001_round4_specification.md, cand_free_macro_001_human_binding_worksheet.md).

CONTRACT INVARIANTS:
1. Sovereign authority: Official NYSE annual calendar artifacts pinned per-year (2013-2026).
2. Timezone: Strictly America/New_York via ZoneInfo (DST handled automatically, zero fixed UTC offsets).
3. Core Session: [09:30:00, 16:00:00) America/New_York -> exactly 390 1-minute bars.
4. Early Close Session: [09:30:00, 13:00:00) America/New_York -> exactly 210 1-minute bars.
5. Out of Range: Dates with year < 2013 or year > 2026 fail closed with CalendarAuthorityOutOfRangeError.
6. Non-trading days: Weekends and official holidays fail closed (get_session raises NonTradingDayError).
7. Strict zero generic holiday inference: Holidays and early closes derive from official pinned dates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError

if TYPE_CHECKING:
    from acash.data.qualification.session import VerifiedSessionSchedule

NY_TZ = ZoneInfo("America/New_York")
RTH_OPEN_TIME: time = time(9, 30, 0)
RTH_REGULAR_CLOSE_TIME: time = time(16, 0, 0)
RTH_EARLY_CLOSE_TIME: time = time(13, 0, 0)

CA1_MIN_YEAR: int = 2013
CA1_MAX_YEAR: int = 2026


class CalendarAuthorityOutOfRangeError(DataContractError):
    """Raised when a requested date lies outside ratified CA-1 historical coverage [2013, 2026]."""


class NonTradingDayError(DataContractError):
    """Raised when session details are requested for a weekend or official market holiday."""


class SessionType(str, Enum):
    """Trading session classification."""

    REGULAR = "REGULAR"
    EARLY_CLOSE = "EARLY_CLOSE"


@dataclass(frozen=True)
class CalendarAuthorityMetadata:
    """Cryptographic and archival provenance for an annual CA-1 calendar artifact."""

    authority: str
    source_year: int
    artifact_identity: str
    official_url: str
    effective_version_date: str
    sha256: str


@dataclass(frozen=True)
class TradingSession:
    """Authoritative representation of a single US Equity trading session under CA-1."""

    session_date: date
    timezone_name: str
    open_local: time
    close_local: time
    open_utc: datetime
    close_utc: datetime
    session_type: SessionType
    expected_minute_count: int
    authority_metadata: CalendarAuthorityMetadata

    def expected_minute_grid(self) -> List[datetime]:
        """Generate the exact sequence of 1-minute bar timestamps for this session in UTC.

        Each timestamp represents the start of a 1-minute interval [t, t + 1m).
        """
        grid: List[datetime] = []
        curr = self.open_utc
        while curr < self.close_utc:
            grid.append(curr)
            curr += timedelta(minutes=1)
        if len(grid) != self.expected_minute_count:
            raise DataContractError(
                f"Generated grid length {len(grid)} does not match expected count {self.expected_minute_count}"
            )
        return grid

    def to_verified_schedule(self) -> VerifiedSessionSchedule:
        """Convert to VerifiedSessionSchedule for historical bar qualification validation."""
        from acash.data.qualification.session import VerifiedSessionSchedule

        return VerifiedSessionSchedule(
            trading_date=self.session_date,
            session_open_utc=self.open_utc,
            session_close_utc=self.close_utc,
            is_early_close=(self.session_type == SessionType.EARLY_CLOSE),
            expected_bar_count=self.expected_minute_count,
        )


# =============================================================================
# CA-1 Pinned Artifact Provenance Table (2013–2026)
# =============================================================================

CA1_ARTIFACTS: Dict[int, CalendarAuthorityMetadata] = {
    2013: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2013,
        artifact_identity="BusinessWire 20110107005513 + nyx.com capture 20130708145321",
        official_url="https://www.businesswire.com/news/home/20110107005513/en/NYSE-Euronext-NYX-Announces-2012-2013-Holiday",
        effective_version_date="2011-01-07 / 2013-07-08",
        sha256="220999AF6B99547DE394017C46401662589ED7BCB4D1B9DC732F5BFBD8426256",
    ),
    2014: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2014,
        artifact_identity="b97d77df-0ecb-4db0-9ced-75bdb9b218ba.pdf",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/b97d77df-0ecb-4db0-9ced-75bdb9b218ba.pdf",
        effective_version_date="Dec. 20 2013",
        sha256="6628B0387532A69FD2517865B8881A2D2D794FBDCB618A1D391A9570FE344FEE",
    ),
    2015: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2015,
        artifact_identity="442a7c75-b606-4b5d-9853-2efa7d6634c3.pdf",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/442a7c75-b606-4b5d-9853-2efa7d6634c3.pdf",
        effective_version_date="Dec. 08 2014",
        sha256="27C9870E886D48C110C99E0F38E6A5623B6B9FE0A3BF85E5A8E51478CA3EE357",
    ),
    2016: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2016,
        artifact_identity="b273f2b1-f4f0-46ae-b6ec-a64e35cd6b7e.pdf",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/b273f2b1-f4f0-46ae-b6ec-a64e35cd6b7e.pdf",
        effective_version_date="Feb. 02 2016",
        sha256="AAC47989C8F6EBDD56C19F0D90E6D873EBC03AE66FBD11210877995A2B59152B",
    ),
    2017: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2017,
        artifact_identity="313c9417-c6e3-46d3-b820-dbc7d9961ebd.pdf",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/313c9417-c6e3-46d3-b820-dbc7d9961ebd.pdf",
        effective_version_date="Dec. 12 2016",
        sha256="B76374B168C2237F02FDF140131DECF851BECEBFA047F7B06FF516A7CE8D305F",
    ),
    2018: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2018,
        artifact_identity="27aaa58b-ebcb-4f53-b505-aee992f54968.pdf",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/27aaa58b-ebcb-4f53-b505-aee992f54968.pdf",
        effective_version_date="Nov. 27 2017",
        sha256="B13C018159E56B6D19ED370BBE879C56A04B6D83CC9B316C29158019FDF29812",
    ),
    2019: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2019,
        artifact_identity="15638cee-2935-4422-bcb4-a3733587eb8b.pdf",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/15638cee-2935-4422-bcb4-a3733587eb8b.pdf",
        effective_version_date="Dec. 04 2018",
        sha256="BFC91FF0CEE6B68C1C881F786C103F6471E2CA49ED38BA62BDC65D65C991B58A",
    ),
    2020: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2020,
        artifact_identity="91a5230f-7233-4a93-b30a-79c9411ebdbe.pdf",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/91a5230f-7233-4a93-b30a-79c9411ebdbe.pdf",
        effective_version_date="Dec. 09 2019",
        sha256="685A189EC0F46A92E8C78B931168B5009DE7189F821464BD7A53D2A78CBAC9C2",
    ),
    2021: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2021,
        artifact_identity="NYSE Group Holiday Calendar 2021-2023 press PDF",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/2020-12-28.pdf",
        effective_version_date="Dec. 28 2020",
        sha256="4419CB788F6D606E5EB69DFB757CDAC41C488F110620EBB6DE6A7FCE71AEEB49",
    ),
    2022: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2022,
        artifact_identity="NYSE Group Holiday Calendar 2022-2024 press PDF",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/2021-12-27.pdf",
        effective_version_date="Dec. 27 2021",
        sha256="B8537E4515E1D31FFBD0F482BF7BC01DC97E1E745DFDF8C536CD7C89BA049E90",
    ),
    2023: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2023,
        artifact_identity="NYSE Group Holiday Calendar 2023-2025 press PDF",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/2022-12-21.pdf",
        effective_version_date="Dec. 21 2022",
        sha256="8092099C06325983A897368BD730E7B27C17513C30FF39893BD36E67DBC67186",
    ),
    2024: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2024,
        artifact_identity="NYSE Group Holiday Calendar 2024-2026 press PDF",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/2023-11-10.pdf",
        effective_version_date="Nov. 10 2023",
        sha256="A379433B31713BF548D1589178BCF28FBC9B04DDAEE02462EE848EF7D65BD64F",
    ),
    2025: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2025,
        artifact_identity="NYSE Group Holiday Calendar 2025-2027 press PDF",
        official_url="https://s2.q4cdn.com/154085107/files/doc_news/archive/2024-11-08.pdf",
        effective_version_date="Nov. 08 2024",
        sha256="6D719AAA4B83049F3EC17C43AC26DA905D6D19523C6923CD0161A4E9E6FE3355",
    ),
    2026: CalendarAuthorityMetadata(
        authority="NYSE Official (CA-1)",
        source_year=2026,
        artifact_identity="ICE_NYSE_2026_Yearly_Trading_Calendar.pdf",
        official_url="https://www.nyse.com/publicdocs/nyse/ICE_NYSE_2026_Yearly_Trading_Calendar.pdf",
        effective_version_date="Dec. 10 2025",
        sha256="70F5577EB43E60A9DBBECAAE3CEC23D0F02028C05C7F175013BB3E97816D394F",
    ),
}

# =============================================================================
# Authoritative Pinned Official Holidays (2013–2026)
# =============================================================================

NYSE_OFFICIAL_HOLIDAYS: Dict[date, str] = {
    # 2013
    date(2013, 1, 1): "New Year's Day",
    date(2013, 1, 21): "Martin Luther King, Jr. Day",
    date(2013, 2, 18): "Washington's Birthday",
    date(2013, 3, 29): "Good Friday",
    date(2013, 5, 27): "Memorial Day",
    date(2013, 7, 4): "Independence Day",
    date(2013, 9, 2): "Labor Day",
    date(2013, 11, 28): "Thanksgiving Day",
    date(2013, 12, 25): "Christmas Day",
    # 2014
    date(2014, 1, 1): "New Year's Day",
    date(2014, 1, 20): "Martin Luther King, Jr. Day",
    date(2014, 2, 17): "Washington's Birthday",
    date(2014, 4, 18): "Good Friday",
    date(2014, 5, 26): "Memorial Day",
    date(2014, 7, 4): "Independence Day",
    date(2014, 9, 1): "Labor Day",
    date(2014, 11, 27): "Thanksgiving Day",
    date(2014, 12, 25): "Christmas Day",
    # 2015
    date(2015, 1, 1): "New Year's Day",
    date(2015, 1, 19): "Martin Luther King, Jr. Day",
    date(2015, 2, 16): "Washington's Birthday",
    date(2015, 4, 3): "Good Friday",
    date(2015, 5, 25): "Memorial Day",
    date(2015, 7, 3): "Independence Day (Observed)",
    date(2015, 9, 7): "Labor Day",
    date(2015, 11, 26): "Thanksgiving Day",
    date(2015, 12, 25): "Christmas Day",
    # 2016
    date(2016, 1, 1): "New Year's Day",
    date(2016, 1, 18): "Martin Luther King, Jr. Day",
    date(2016, 2, 15): "Washington's Birthday",
    date(2016, 3, 25): "Good Friday",
    date(2016, 5, 30): "Memorial Day",
    date(2016, 7, 4): "Independence Day",
    date(2016, 9, 5): "Labor Day",
    date(2016, 11, 24): "Thanksgiving Day",
    date(2016, 12, 26): "Christmas Day (Observed)",
    # 2017
    date(2017, 1, 2): "New Year's Day (Observed)",
    date(2017, 1, 16): "Martin Luther King, Jr. Day",
    date(2017, 2, 20): "Washington's Birthday",
    date(2017, 4, 14): "Good Friday",
    date(2017, 5, 29): "Memorial Day",
    date(2017, 7, 4): "Independence Day",
    date(2017, 9, 4): "Labor Day",
    date(2017, 11, 23): "Thanksgiving Day",
    date(2017, 12, 25): "Christmas Day",
    # 2018
    date(2018, 1, 1): "New Year's Day",
    date(2018, 1, 15): "Martin Luther King, Jr. Day",
    date(2018, 2, 19): "Washington's Birthday",
    date(2018, 3, 30): "Good Friday",
    date(2018, 5, 28): "Memorial Day",
    date(2018, 7, 4): "Independence Day",
    date(2018, 9, 3): "Labor Day",
    date(2018, 11, 22): "Thanksgiving Day",
    date(2018, 12, 5): "National Day of Mourning for President George H.W. Bush",
    date(2018, 12, 25): "Christmas Day",
    # 2019
    date(2019, 1, 1): "New Year's Day",
    date(2019, 1, 21): "Martin Luther King, Jr. Day",
    date(2019, 2, 18): "Washington's Birthday",
    date(2019, 4, 19): "Good Friday",
    date(2019, 5, 27): "Memorial Day",
    date(2019, 7, 4): "Independence Day",
    date(2019, 9, 2): "Labor Day",
    date(2019, 11, 28): "Thanksgiving Day",
    date(2019, 12, 25): "Christmas Day",
    # 2020
    date(2020, 1, 1): "New Year's Day",
    date(2020, 1, 20): "Martin Luther King, Jr. Day",
    date(2020, 2, 17): "Washington's Birthday",
    date(2020, 4, 10): "Good Friday",
    date(2020, 5, 25): "Memorial Day",
    date(2020, 7, 3): "Independence Day (Observed)",
    date(2020, 9, 7): "Labor Day",
    date(2020, 11, 26): "Thanksgiving Day",
    date(2020, 12, 25): "Christmas Day",
    # 2021
    date(2021, 1, 1): "New Year's Day",
    date(2021, 1, 18): "Martin Luther King, Jr. Day",
    date(2021, 2, 15): "Washington's Birthday",
    date(2021, 4, 2): "Good Friday",
    date(2021, 5, 31): "Memorial Day",
    date(2021, 7, 5): "Independence Day (Observed)",
    date(2021, 9, 6): "Labor Day",
    date(2021, 11, 25): "Thanksgiving Day",
    date(2021, 12, 24): "Christmas Day (Observed)",
    # 2022
    date(2022, 1, 17): "Martin Luther King, Jr. Day",
    date(2022, 2, 21): "Washington's Birthday",
    date(2022, 4, 15): "Good Friday",
    date(2022, 5, 30): "Memorial Day",
    date(2022, 6, 20): "Juneteenth National Independence Day (Observed)",
    date(2022, 7, 4): "Independence Day",
    date(2022, 9, 5): "Labor Day",
    date(2022, 11, 24): "Thanksgiving Day",
    date(2022, 12, 26): "Christmas Day (Observed)",
    # 2023
    date(2023, 1, 2): "New Year's Day (Observed)",
    date(2023, 1, 16): "Martin Luther King, Jr. Day",
    date(2023, 2, 20): "Washington's Birthday",
    date(2023, 4, 7): "Good Friday",
    date(2023, 5, 29): "Memorial Day",
    date(2023, 6, 19): "Juneteenth National Independence Day",
    date(2023, 7, 4): "Independence Day",
    date(2023, 9, 4): "Labor Day",
    date(2023, 11, 23): "Thanksgiving Day",
    date(2023, 12, 25): "Christmas Day",
    # 2024
    date(2024, 1, 1): "New Year's Day",
    date(2024, 1, 15): "Martin Luther King, Jr. Day",
    date(2024, 2, 19): "Washington's Birthday",
    date(2024, 3, 29): "Good Friday",
    date(2024, 5, 27): "Memorial Day",
    date(2024, 6, 19): "Juneteenth National Independence Day",
    date(2024, 7, 4): "Independence Day",
    date(2024, 9, 2): "Labor Day",
    date(2024, 11, 28): "Thanksgiving Day",
    date(2024, 12, 25): "Christmas Day",
    # 2025
    date(2025, 1, 1): "New Year's Day",
    date(2025, 1, 20): "Martin Luther King, Jr. Day",
    date(2025, 2, 17): "Washington's Birthday",
    date(2025, 4, 18): "Good Friday",
    date(2025, 5, 26): "Memorial Day",
    date(2025, 6, 19): "Juneteenth National Independence Day",
    date(2025, 7, 4): "Independence Day",
    date(2025, 9, 1): "Labor Day",
    date(2025, 11, 27): "Thanksgiving Day",
    date(2025, 12, 25): "Christmas Day",
    # 2026
    date(2026, 1, 1): "New Year's Day",
    date(2026, 1, 19): "Martin Luther King, Jr. Day",
    date(2026, 2, 16): "Washington's Birthday",
    date(2026, 4, 3): "Good Friday",
    date(2026, 5, 25): "Memorial Day",
    date(2026, 6, 19): "Juneteenth National Independence Day",
    date(2026, 7, 3): "Independence Day (Observed)",
    date(2026, 9, 7): "Labor Day",
    date(2026, 11, 26): "Thanksgiving Day",
    date(2026, 12, 25): "Christmas Day",
}

# =============================================================================
# Authoritative Pinned Official Early Closes (13:00 ET) (2013–2026)
# =============================================================================

NYSE_OFFICIAL_EARLY_CLOSES: Set[date] = {
    # 2013
    date(2013, 7, 3),   # Day before Independence Day
    date(2013, 11, 29),  # Day after Thanksgiving
    date(2013, 12, 24),  # Christmas Eve
    # 2014
    date(2014, 7, 3),   # Day before Independence Day
    date(2014, 11, 28),  # Day after Thanksgiving
    date(2014, 12, 24),  # Christmas Eve
    # 2015
    date(2015, 11, 27),  # Day after Thanksgiving
    date(2015, 12, 24),  # Christmas Eve
    # 2016
    date(2016, 11, 25),  # Day after Thanksgiving
    # 2017
    date(2017, 7, 3),   # Day before Independence Day
    date(2017, 11, 24),  # Day after Thanksgiving
    # 2018
    date(2018, 7, 3),   # Day before Independence Day
    date(2018, 11, 23),  # Day after Thanksgiving
    date(2018, 12, 24),  # Christmas Eve
    # 2019
    date(2019, 7, 3),   # Day before Independence Day
    date(2019, 11, 29),  # Day after Thanksgiving
    date(2019, 12, 24),  # Christmas Eve
    # 2020
    date(2020, 11, 27),  # Day after Thanksgiving
    date(2020, 12, 24),  # Christmas Eve
    # 2021
    date(2021, 11, 26),  # Day after Thanksgiving
    # 2022
    date(2022, 11, 25),  # Day after Thanksgiving
    # 2023
    date(2023, 7, 3),   # Day before Independence Day
    date(2023, 11, 24),  # Day after Thanksgiving
    # 2024
    date(2024, 7, 3),   # Day before Independence Day
    date(2024, 11, 29),  # Day after Thanksgiving
    date(2024, 12, 24),  # Christmas Eve
    # 2025
    date(2025, 7, 3),   # Day before Independence Day
    date(2025, 11, 28),  # Day after Thanksgiving
    date(2025, 12, 24),  # Christmas Eve
    # 2026
    date(2026, 11, 27),  # Day after Thanksgiving
    date(2026, 12, 24),  # Christmas Eve
}


class NyseCa1Calendar:
    """Executable CA-1 sovereign calendar authority for US Equity trading sessions.

    Coverage: 2013-01-01 through 2026-12-31.
    Fail-closed: Any query outside [2013, 2026] raises CalendarAuthorityOutOfRangeError.
    """

    def __init__(self) -> None:
        self._holidays = NYSE_OFFICIAL_HOLIDAYS
        self._early_closes = NYSE_OFFICIAL_EARLY_CLOSES
        self._artifacts = CA1_ARTIFACTS

    def _check_year_range(self, d: date) -> None:
        """Enforce strict fail-closed boundary on historical year coverage [2013, 2026]."""
        if d.year < CA1_MIN_YEAR or d.year > CA1_MAX_YEAR:
            raise CalendarAuthorityOutOfRangeError(
                f"Date {d.isoformat()} (year {d.year}) lies outside ratified CA-1 "
                f"historical coverage [{CA1_MIN_YEAR}, {CA1_MAX_YEAR}]."
            )

    def is_trading_session(self, session_date: date) -> bool:
        """Return True if session_date is an official NYSE trading session.

        Fails closed with CalendarAuthorityOutOfRangeError if year is outside [2013, 2026].
        Returns False for weekends and official holidays.
        """
        self._check_year_range(session_date)
        # Weekends are not trading days (Monday=0, Sunday=6)
        if session_date.weekday() >= 5:
            return False
        # Official market holidays
        if session_date in self._holidays:
            return False
        return True

    def is_holiday(self, session_date: date) -> bool:
        """Return True if session_date is an official NYSE market holiday."""
        self._check_year_range(session_date)
        return session_date in self._holidays

    def is_early_close(self, session_date: date) -> bool:
        """Return True if session_date is an official NYSE 13:00 ET early close."""
        self._check_year_range(session_date)
        return session_date in self._early_closes

    def get_holiday_reason(self, session_date: date) -> Optional[str]:
        """Return official holiday description if session_date is a market holiday, else None."""
        self._check_year_range(session_date)
        return self._holidays.get(session_date)

    def authority_metadata(self, session_date: date) -> CalendarAuthorityMetadata:
        """Retrieve CA-1 source artifact authority metadata for session_date's year."""
        self._check_year_range(session_date)
        meta = self._artifacts.get(session_date.year)
        if meta is None:
            raise CalendarAuthorityOutOfRangeError(
                f"Missing CA-1 artifact metadata for year {session_date.year}"
            )
        return meta

    def get_session(self, session_date: date) -> TradingSession:
        """Retrieve authoritative TradingSession details for session_date.

        Raises:
            CalendarAuthorityOutOfRangeError: if year is outside [2013, 2026].
            NonTradingDayError: if session_date is a weekend or official market holiday.
        """
        self._check_year_range(session_date)
        if session_date.weekday() >= 5:
            raise NonTradingDayError(f"{session_date.isoformat()} is a weekend (non-trading day).")
        if session_date in self._holidays:
            reason = self._holidays[session_date]
            raise NonTradingDayError(f"{session_date.isoformat()} is an official NYSE holiday: {reason}.")

        is_early = session_date in self._early_closes
        session_type = SessionType.EARLY_CLOSE if is_early else SessionType.REGULAR
        close_local = RTH_EARLY_CLOSE_TIME if is_early else RTH_REGULAR_CLOSE_TIME
        expected_minutes = 210 if is_early else 390

        # Construct local timezone-aware datetimes with ZoneInfo
        open_dt_local = datetime.combine(session_date, RTH_OPEN_TIME, tzinfo=NY_TZ)
        close_dt_local = datetime.combine(session_date, close_local, tzinfo=NY_TZ)

        # Convert to UTC explicitly
        open_utc = open_dt_local.astimezone(timezone.utc)
        close_utc = close_dt_local.astimezone(timezone.utc)

        meta = self.authority_metadata(session_date)

        return TradingSession(
            session_date=session_date,
            timezone_name="America/New_York",
            open_local=RTH_OPEN_TIME,
            close_local=close_local,
            open_utc=open_utc,
            close_utc=close_utc,
            session_type=session_type,
            expected_minute_count=expected_minutes,
            authority_metadata=meta,
        )

    def get_session_or_none(self, session_date: date) -> Optional[TradingSession]:
        """Return TradingSession if session_date is an official trading day, else None.

        If session_date is outside [2013, 2026], returns None (fail-closed authority unverified).
        """
        try:
            if not self.is_trading_session(session_date):
                return None
            return self.get_session(session_date)
        except CalendarAuthorityOutOfRangeError:
            return None

    def get_verified_schedule(self, session_date: date) -> Optional[VerifiedSessionSchedule]:
        """Return VerifiedSessionSchedule for historical qualification validation, or None if not covered."""
        session = self.get_session_or_none(session_date)
        if session is None:
            return None
        return session.to_verified_schedule()

    def expected_minute_grid(self, session_date: date) -> List[datetime]:
        """Return the exact sequence of 1-minute UTC bar timestamps for session_date."""
        session = self.get_session(session_date)
        return session.expected_minute_grid()

    def expected_minute_count(self, session_date: date) -> int:
        """Return expected bar count: 390 for regular session, 210 for early close."""
        session = self.get_session(session_date)
        return session.expected_minute_count
