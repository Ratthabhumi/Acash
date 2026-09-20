"""MEC-0015 Alpaca Corporate Actions (Cash Dividend) Qualification Contract.

Strict Invariants:
1. Endpoint: GET https://data.alpaca.markets/v1/corporate-actions
2. Scope: SPY cash dividends, data_quality=complete, 2007-01-01 through 2024-04-30.
3. Strict Date Boundary: Any record with ex_date or access >= 2024-05-01 triggers immediate DataContractError.
4. Classifications:
   - DIVIDEND_PROVIDER_MAPPING = QUALIFIED_HISTORICAL_COMPLETE_SNAPSHOT
   - DIVIDEND_POINT_IN_TIME_VINTAGE = NOT_GUARANTEED_BY_PROVIDER
5. Fail-Closed Rule: If an ex-date dividend required by strategy is absent or ambiguous:
   DATA_CONTRACT_EXCLUSION. Never assume dividend = zero when a record is uncertain.
6. Zero Strategy Execution: No strategy P&L, returns, or backtest.
7. Credential Hygiene: Credentials and headers are never serialized or logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

MEC_0015_DIVIDEND_START_DATE: date = date(2007, 1, 1)
MEC_0015_DIVIDEND_MAX_ALLOWED_DATE: date = date(2024, 4, 30)
MEC_0015_DIVIDEND_FORBIDDEN_OOS_DATE: date = date(2024, 5, 1)

DIVIDEND_PROVIDER_MAPPING_QUALIFIED: str = "QUALIFIED_HISTORICAL_COMPLETE_SNAPSHOT"
DIVIDEND_POINT_IN_TIME_VINTAGE_NOT_GUARANTEED: str = "NOT_GUARANTEED_BY_PROVIDER"


@dataclass(frozen=True)
class Mec0015CashDividendRecord:
    """Individual SPY cash dividend record validated from Alpaca corporate actions."""

    symbol: str
    action_type: str
    ex_date: str
    rate: Decimal
    process_date: Optional[str]
    record_id: str
    special: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action_type": self.action_type,
            "ex_date": self.ex_date,
            "rate": str(self.rate),
            "process_date": self.process_date,
            "record_id": self.record_id,
            "special": self.special,
        }


@dataclass(frozen=True)
class Mec0015DividendQualificationReport:
    """Canonical report of Alpaca corporate actions dividend qualification."""

    endpoint: str
    symbol: str
    action_type: str
    data_quality: str
    query_start: str
    query_end: str
    pagination_completed: bool
    record_count: int
    records: List[Mec0015CashDividendRecord]
    raw_payload_sha256: str
    max_accessed_date: str
    provider_mapping_status: str
    pit_vintage_status: str
    is_qualified: bool
    fail_closed_rule: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_schema": "acash.research.mec_0015_dividend_manifest.v1",
            "endpoint": self.endpoint,
            "symbol": self.symbol,
            "action_type": self.action_type,
            "data_quality": self.data_quality,
            "query_range": {
                "start": self.query_start,
                "end": self.query_end,
                "maximum_allowed_date": MEC_0015_DIVIDEND_MAX_ALLOWED_DATE.isoformat(),
                "forbidden_oos_boundary": MEC_0015_DIVIDEND_FORBIDDEN_OOS_DATE.isoformat(),
            },
            "pagination": {
                "completed": self.pagination_completed,
                "next_page_token": None,
            },
            "qualification": {
                "record_count": self.record_count,
                "provider_mapping": self.provider_mapping_status,
                "point_in_time_vintage": self.pit_vintage_status,
                "is_qualified": self.is_qualified,
                "fail_closed_rule": self.fail_closed_rule,
            },
            "payload_hashes": {
                "raw_payload_sha256": self.raw_payload_sha256,
            },
            "cash_dividends": [r.to_dict() for r in self.records],
        }


def validate_and_parse_dividend_records(
    payload_bytes: bytes,
) -> Mec0015DividendQualificationReport:
    """Parse, validate, and compute deterministic hash for Alpaca corporate-actions response.

    Fails closed on:
    - Missing required fields
    - Invalid types / negative dividend rates
    - Any ex-date >= 2024-05-01 (forbidden post-publication boundary)
    """
    raw_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    try:
        data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise DataContractError(f"MALFORMED_JSON_PAYLOAD: {exc}") from exc

    if not isinstance(data, dict):
        raise DataContractError("PAYLOAD_NOT_DICT: Expected top-level dict in corporate actions.")

    ca = data.get("corporate_actions")
    if not isinstance(ca, dict):
        raise DataContractError("MISSING_CORPORATE_ACTIONS_DICT: Expected 'corporate_actions' dict.")

    div_list = ca.get("cash_dividends")
    if not isinstance(div_list, list):
        raise DataContractError("MISSING_CASH_DIVIDENDS_LIST: Expected 'cash_dividends' list.")

    next_page_token = data.get("next_page_token")
    if next_page_token is not None:
        raise DataContractError(
            f"PAGINATION_INCOMPLETE: next_page_token is present ({next_page_token})."
        )

    records: List[Mec0015CashDividendRecord] = []
    max_ex_date = "0000-00-00"

    for idx, item in enumerate(div_list):
        if not isinstance(item, dict):
            raise DataContractError(f"INVALID_RECORD_{idx}: Expected dict, got {type(item)}.")

        symbol = item.get("symbol")
        if symbol != "SPY":
            raise DataContractError(f"UNAUTHORIZED_SYMBOL_{idx}: Expected SPY, got {symbol}.")

        ex_date_str = item.get("ex_date")
        if not ex_date_str or not isinstance(ex_date_str, str):
            raise DataContractError(f"MISSING_EX_DATE_{idx}: Record has no valid ex_date.")

        ex_d = date.fromisoformat(ex_date_str)
        if ex_d >= MEC_0015_DIVIDEND_FORBIDDEN_OOS_DATE:
            raise DataContractError(
                f"FORBIDDEN_OOS_EX_DATE_{idx}: ex_date {ex_date_str} >= {MEC_0015_DIVIDEND_FORBIDDEN_OOS_DATE}."
            )
        if ex_d < MEC_0015_DIVIDEND_START_DATE:
            raise DataContractError(
                f"EX_DATE_BEFORE_START_{idx}: ex_date {ex_date_str} < {MEC_0015_DIVIDEND_START_DATE}."
            )

        if ex_date_str > max_ex_date:
            max_ex_date = ex_date_str

        rate_raw = item.get("rate")
        if rate_raw is None:
            raise DataContractError(f"MISSING_RATE_{idx}: Record has no dividend rate.")
        try:
            rate_dec = Decimal(str(rate_raw))
        except Exception as exc:
            raise DataContractError(f"INVALID_RATE_{idx}: {rate_raw}") from exc

        if rate_dec <= Decimal("0"):
            raise DataContractError(f"NON_POSITIVE_RATE_{idx}: rate must be > 0, got {rate_dec}.")

        process_date = item.get("process_date")
        rec_id = item.get("id", "")
        special = bool(item.get("special", False))

        records.append(
            Mec0015CashDividendRecord(
                symbol=symbol,
                action_type="cash_dividend",
                ex_date=ex_date_str,
                rate=rate_dec,
                process_date=str(process_date) if process_date else None,
                record_id=str(rec_id),
                special=special,
            )
        )

    # Sort records chronologically by ex_date
    records.sort(key=lambda r: r.ex_date)

    return Mec0015DividendQualificationReport(
        endpoint="https://data.alpaca.markets/v1/corporate-actions",
        symbol="SPY",
        action_type="cash_dividend",
        data_quality="complete",
        query_start=MEC_0015_DIVIDEND_START_DATE.isoformat(),
        query_end=MEC_0015_DIVIDEND_MAX_ALLOWED_DATE.isoformat(),
        pagination_completed=(next_page_token is None),
        record_count=len(records),
        records=records,
        raw_payload_sha256=raw_sha256,
        max_accessed_date=max_ex_date,
        provider_mapping_status=DIVIDEND_PROVIDER_MAPPING_QUALIFIED,
        pit_vintage_status=DIVIDEND_POINT_IN_TIME_VINTAGE_NOT_GUARANTEED,
        is_qualified=(len(records) > 0),
        fail_closed_rule=(
            "If an ex-date dividend required by strategy is absent or ambiguous: "
            "DATA_CONTRACT_EXCLUSION. Never assume dividend = zero when uncertain."
        ),
    )
