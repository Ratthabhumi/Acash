"""Historical US Regulatory Transaction Fee Models (SEC Section 31 & FINRA TAF).

Strict Invariants:
- Pure deterministic functions using Decimal arithmetic only (no floating-point).
- Effective-date lookup covering 2007-05-01 through 2024-04-30 (M1 replication period).
- Fail closed (raises DataContractError) outside authorized schedule or on malformed inputs.
- Sell-side only: returns Decimal("0.00") for buy orders.
- Zero credential access, zero market data access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_CEILING
from typing import Sequence

from acash.core.domain.exceptions import DataContractError

MEC_0015_REGULATORY_SCHEDULE_START: date = date(2007, 5, 1)
MEC_0015_REGULATORY_SCHEDULE_END: date = date(2024, 4, 30)


@dataclass(frozen=True)
class Sec31ScheduleSegment:
    """Historical SEC Section 31 transaction fee rate segment."""

    effective_start: date
    effective_end: date
    rate_per_million: Decimal
    rate_per_dollar: Decimal
    official_source: str
    source_reference: str


@dataclass(frozen=True)
class FinraTafScheduleSegment:
    """Historical FINRA Trading Activity Fee (TAF) schedule segment."""

    effective_start: date
    effective_end: date
    rate_per_share: Decimal
    max_fee_per_trade: Decimal
    official_source: str
    source_reference: str


# ---------------------------------------------------------------------------
# Authoritative SEC Section 31 Fee Schedule (2007-05-01 to 2024-04-30)
# Sources: Official SEC Fee Rate Advisories published pursuant to Section 31
# of the Securities Exchange Act of 1934.
# ---------------------------------------------------------------------------
SEC_SECTION_31_SCHEDULE: Sequence[Sec31ScheduleSegment] = (
    Sec31ScheduleSegment(
        effective_start=date(2007, 3, 17),
        effective_end=date(2008, 1, 24),
        rate_per_million=Decimal("15.30"),
        rate_per_dollar=Decimal("0.00001530"),
        official_source="SEC Fee Rate Advisory #4 for Fiscal Year 2007",
        source_reference="SEC Release No. 34-55365 / Effective March 17, 2007",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2008, 1, 25),
        effective_end=date(2008, 3, 31),
        rate_per_million=Decimal("11.00"),
        rate_per_dollar=Decimal("0.00001100"),
        official_source="SEC Fee Rate Advisory #3 for Fiscal Year 2008",
        source_reference="SEC Release No. 34-57142 / Effective January 25, 2008",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2008, 4, 1),
        effective_end=date(2009, 4, 9),
        rate_per_million=Decimal("5.60"),
        rate_per_dollar=Decimal("0.00000560"),
        official_source="SEC Fee Rate Advisory #4 for Fiscal Year 2008 (Mid-Year)",
        source_reference="SEC Release No. 34-57419 / Effective April 1, 2008",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2009, 4, 10),
        effective_end=date(2010, 1, 14),
        rate_per_million=Decimal("25.70"),
        rate_per_dollar=Decimal("0.00002570"),
        official_source="SEC Fee Rate Advisory #4 for Fiscal Year 2009 (Mid-Year)",
        source_reference="SEC Release No. 34-59543 / Effective April 10, 2009",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2010, 1, 15),
        effective_end=date(2010, 3, 31),
        rate_per_million=Decimal("12.70"),
        rate_per_dollar=Decimal("0.00001270"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2010",
        source_reference="SEC Release No. 34-61268 / Effective January 15, 2010",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2010, 4, 1),
        effective_end=date(2011, 1, 20),
        rate_per_million=Decimal("16.90"),
        rate_per_dollar=Decimal("0.00001690"),
        official_source="SEC Fee Rate Advisory #4 for Fiscal Year 2010 (Mid-Year)",
        source_reference="SEC Release No. 34-61614 / Effective April 1, 2010",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2011, 1, 21),
        effective_end=date(2012, 2, 20),
        rate_per_million=Decimal("19.20"),
        rate_per_dollar=Decimal("0.00001920"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2011",
        source_reference="SEC Release No. 34-63595 / Effective January 21, 2011",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2012, 2, 21),
        effective_end=date(2012, 3, 31),
        rate_per_million=Decimal("18.00"),
        rate_per_dollar=Decimal("0.00001800"),
        official_source="SEC Fee Rate Advisory #5 for Fiscal Year 2012",
        source_reference="SEC Release No. 34-66205 / Effective February 21, 2012",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2012, 4, 1),
        effective_end=date(2013, 5, 24),
        rate_per_million=Decimal("22.40"),
        rate_per_dollar=Decimal("0.00002240"),
        official_source="SEC Fee Rate Advisory #6 for Fiscal Year 2012 (Mid-Year)",
        source_reference="SEC Release No. 34-66490 / Effective April 1, 2012",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2013, 5, 25),
        effective_end=date(2014, 3, 17),
        rate_per_million=Decimal("17.40"),
        rate_per_dollar=Decimal("0.00001740"),
        official_source="SEC Fee Rate Advisory #3 for Fiscal Year 2013",
        source_reference="SEC Release No. 34-69446 / Effective May 25, 2013",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2014, 3, 18),
        effective_end=date(2015, 2, 13),
        rate_per_million=Decimal("22.10"),
        rate_per_dollar=Decimal("0.00002210"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2014",
        source_reference="SEC Release No. 34-71556 / Effective March 18, 2014",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2015, 2, 14),
        effective_end=date(2016, 2, 15),
        rate_per_million=Decimal("18.40"),
        rate_per_dollar=Decimal("0.00001840"),
        official_source="SEC Fee Rate Advisory #3 for Fiscal Year 2015",
        source_reference="SEC Release No. 34-74070 / Effective February 14, 2015",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2016, 2, 16),
        effective_end=date(2017, 7, 3),
        rate_per_million=Decimal("21.80"),
        rate_per_dollar=Decimal("0.00002180"),
        official_source="SEC Fee Rate Advisory #3 for Fiscal Year 2016",
        source_reference="SEC Release No. 34-76852 / Effective February 16, 2016",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2017, 7, 4),
        effective_end=date(2018, 5, 21),
        rate_per_million=Decimal("23.10"),
        rate_per_dollar=Decimal("0.00002310"),
        official_source="SEC Fee Rate Advisory #3 for Fiscal Year 2017",
        source_reference="SEC Release No. 34-80830 / Effective July 4, 2017",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2018, 5, 22),
        effective_end=date(2019, 4, 15),
        rate_per_million=Decimal("13.00"),
        rate_per_dollar=Decimal("0.00001300"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2018",
        source_reference="SEC Release No. 34-83083 / Effective May 22, 2018",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2019, 4, 16),
        effective_end=date(2020, 2, 17),
        rate_per_million=Decimal("20.70"),
        rate_per_dollar=Decimal("0.00002070"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2019",
        source_reference="SEC Release No. 34-85377 / Effective April 16, 2019",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2020, 2, 18),
        effective_end=date(2021, 2, 24),
        rate_per_million=Decimal("22.10"),
        rate_per_dollar=Decimal("0.00002210"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2020",
        source_reference="SEC Release No. 34-88062 / Effective February 18, 2020",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2021, 2, 25),
        effective_end=date(2022, 5, 13),
        rate_per_million=Decimal("5.10"),
        rate_per_dollar=Decimal("0.00000510"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2021",
        source_reference="SEC Release No. 34-90924 / Effective February 25, 2021",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2022, 5, 14),
        effective_end=date(2023, 2, 26),
        rate_per_million=Decimal("22.90"),
        rate_per_dollar=Decimal("0.00002290"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2022",
        source_reference="SEC Release No. 34-94420 / Effective May 14, 2022",
    ),
    Sec31ScheduleSegment(
        effective_start=date(2023, 2, 27),
        effective_end=date(2024, 5, 21),
        rate_per_million=Decimal("8.00"),
        rate_per_dollar=Decimal("0.00000800"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2023",
        source_reference="SEC Release No. 34-96791 / Effective February 27, 2023",
    ),
)


# ---------------------------------------------------------------------------
# Authoritative FINRA Trading Activity Fee (TAF) Schedule (2007-05-01 to 2024-04-30)
# Sources: Section 1 of Schedule A to the FINRA By-Laws;
# FINRA Notice to Members 04-70, Regulatory Notices 11-27, 12-06, 12-31;
# SR-FINRA-2020-032 (SEC Release No. 34-90176, phased implementation 2022-2024).
# ---------------------------------------------------------------------------
FINRA_TAF_SCHEDULE: Sequence[FinraTafScheduleSegment] = (
    FinraTafScheduleSegment(
        effective_start=date(2004, 11, 1),
        effective_end=date(2011, 6, 30),
        rate_per_share=Decimal("0.000075"),
        max_fee_per_trade=Decimal("3.75"),
        official_source="FINRA Notice to Members 04-70 / Schedule A",
        source_reference="SEC Release No. 34-50485 / Effective November 1, 2004",
    ),
    FinraTafScheduleSegment(
        effective_start=date(2011, 7, 1),
        effective_end=date(2012, 2, 29),
        rate_per_share=Decimal("0.000090"),
        max_fee_per_trade=Decimal("4.50"),
        official_source="FINRA Regulatory Notice 11-27",
        source_reference="SEC Release No. 34-64590 / Effective July 1, 2011",
    ),
    FinraTafScheduleSegment(
        effective_start=date(2012, 3, 1),
        effective_end=date(2012, 6, 30),
        rate_per_share=Decimal("0.000095"),
        max_fee_per_trade=Decimal("4.75"),
        official_source="FINRA Regulatory Notice 12-06",
        source_reference="SEC Release No. 34-66099 / Effective March 1, 2012",
    ),
    FinraTafScheduleSegment(
        effective_start=date(2012, 7, 1),
        effective_end=date(2021, 12, 31),
        rate_per_share=Decimal("0.000119"),
        max_fee_per_trade=Decimal("5.95"),
        official_source="FINRA Regulatory Notice 12-31",
        source_reference="SEC Release No. 34-67242 / Effective July 1, 2012",
    ),
    FinraTafScheduleSegment(
        effective_start=date(2022, 1, 1),
        effective_end=date(2022, 12, 31),
        rate_per_share=Decimal("0.000130"),
        max_fee_per_trade=Decimal("6.49"),
        official_source="FINRA SR-FINRA-2020-032 (Phase 1)",
        source_reference="SEC Release No. 34-90176 / Effective January 1, 2022",
    ),
    FinraTafScheduleSegment(
        effective_start=date(2023, 1, 1),
        effective_end=date(2023, 12, 31),
        rate_per_share=Decimal("0.000145"),
        max_fee_per_trade=Decimal("7.27"),
        official_source="FINRA SR-FINRA-2020-032 (Phase 2)",
        source_reference="SEC Release No. 34-90176 / Effective January 1, 2023",
    ),
    FinraTafScheduleSegment(
        effective_start=date(2024, 1, 1),
        effective_end=date(2024, 12, 31),
        rate_per_share=Decimal("0.000166"),
        max_fee_per_trade=Decimal("8.30"),
        official_source="FINRA SR-FINRA-2020-032 (Phase 3 Full Implementation)",
        source_reference="SEC Release No. 34-90176 / Effective January 1, 2024",
    ),
)


def get_sec31_segment(trade_date: date) -> Sec31ScheduleSegment:
    """Find the applicable SEC Section 31 rate segment for trade_date.

    Raises DataContractError if trade_date is outside the authorized schedule.
    """
    if trade_date < MEC_0015_REGULATORY_SCHEDULE_START or trade_date > MEC_0015_REGULATORY_SCHEDULE_END:
        raise DataContractError(
            f"DATE_OUTSIDE_SCHEDULE: Trade date {trade_date} is outside the authoritative "
            f"MEC-0015 SEC Section 31 schedule ({MEC_0015_REGULATORY_SCHEDULE_START} "
            f"to {MEC_0015_REGULATORY_SCHEDULE_END})."
        )
    for seg in SEC_SECTION_31_SCHEDULE:
        if seg.effective_start <= trade_date <= seg.effective_end:
            return seg
    raise DataContractError(
        f"SEC31_SCHEDULE_GAP: No matching SEC Section 31 schedule segment for date {trade_date}."
    )


def get_finra_taf_segment(trade_date: date) -> FinraTafScheduleSegment:
    """Find the applicable FINRA TAF rate segment for trade_date.

    Raises DataContractError if trade_date is outside the authorized schedule.
    """
    if trade_date < MEC_0015_REGULATORY_SCHEDULE_START or trade_date > MEC_0015_REGULATORY_SCHEDULE_END:
        raise DataContractError(
            f"DATE_OUTSIDE_SCHEDULE: Trade date {trade_date} is outside the authoritative "
            f"MEC-0015 FINRA TAF schedule ({MEC_0015_REGULATORY_SCHEDULE_START} "
            f"to {MEC_0015_REGULATORY_SCHEDULE_END})."
        )
    for seg in FINRA_TAF_SCHEDULE:
        if seg.effective_start <= trade_date <= seg.effective_end:
            return seg
    raise DataContractError(
        f"FINRA_TAF_SCHEDULE_GAP: No matching FINRA TAF schedule segment for date {trade_date}."
    )


def compute_sec31_fee(
    trade_date: date,
    sale_principal: Decimal,
    is_sell: bool = True,
) -> Decimal:
    """Compute SEC Section 31 customer pass-through transaction fee.

    Requirements:
    - Pure function with Decimal arithmetic.
    - Buy side fee is exactly Decimal("0.00").
    - Sell side calculates sale_principal * rate_per_dollar.
    - Fails closed on negative principal or date outside [2007-05-01, 2024-04-30].
    - Rounding: ACASH conservative broker pass-through operationalization uses
      ROUND_CEILING to the next full cent (ROUND_CEILING_TO_CENT), consistent with
      standard broker-dealer pass-through practice noted in SEC rulemaking (Release No. 34-49928).
      SEC Section 31 governs SRO statutory obligations; the SEC does not directly
      prescribe customer rounding rules.
    - Classification: ACASH_CONSERVATIVE_BROKER_PASS_THROUGH_OPERATIONALIZATION (not SEC statutory mandate).
    - Note: ROUND_CEILING naturally yields Decimal("0.01") for any positive sub-cent
      raw fee without requiring a separate artificial minimum-cent special case.
    """
    if not is_sell:
        return Decimal("0.00")
    if not isinstance(sale_principal, Decimal):
        raise DataContractError(
            f"INVALID_TYPE: sale_principal must be Decimal, got {type(sale_principal)}."
        )
    if sale_principal < Decimal("0.00"):
        raise DataContractError(
            f"NEGATIVE_PRINCIPAL: sale_principal cannot be negative, got {sale_principal}."
        )
    if sale_principal == Decimal("0.00"):
        return Decimal("0.00")

    segment = get_sec31_segment(trade_date)
    raw_fee = sale_principal * segment.rate_per_dollar
    return raw_fee.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def compute_finra_taf(
    trade_date: date,
    shares_sold: Decimal | int,
    is_sell: bool = True,
) -> Decimal:
    """Compute FINRA Trading Activity Fee (TAF) for covered equity securities.

    Requirements:
    - Pure function with Decimal arithmetic.
    - Buy side fee is exactly Decimal("0.00").
    - Sell side calculates min(shares_sold * rate_per_share, max_fee_per_trade).
    - FINRA By-Laws Schedule A Section 1(b)(1) mandates rounding UP to nearest cent (ROUND_CEILING).
    - Low-price exemption: FINRA Schedule A Section 1(b)(2) exempts transactions where
      execution price < per-share TAF rate. This MEC-0015 SPY-scoped function intentionally
      omits execution price because SPY prices ($100-$500+) are orders of magnitude above
      the sub-cent TAF rate, and this function is not a generic statutory penny-stock engine.
    - Fails closed on negative shares or date outside [2007-05-01, 2024-04-30].
    """
    if not is_sell:
        return Decimal("0.00")
    if isinstance(shares_sold, int):
        shares_dec = Decimal(shares_sold)
    elif isinstance(shares_sold, Decimal):
        shares_dec = shares_sold
    else:
        raise DataContractError(
            f"INVALID_TYPE: shares_sold must be Decimal or int, got {type(shares_sold)}."
        )
    if shares_dec < Decimal("0"):
        raise DataContractError(
            f"NEGATIVE_SHARES: shares_sold cannot be negative, got {shares_dec}."
        )
    if shares_dec == Decimal("0"):
        return Decimal("0.00")

    segment = get_finra_taf_segment(trade_date)
    raw_fee = shares_dec * segment.rate_per_share
    capped_fee = min(raw_fee, segment.max_fee_per_trade)
    fee = capped_fee.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    return fee
