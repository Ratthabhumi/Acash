#!/usr/bin/env python
"""Tiny SIP probe for HYP_009 Stage‑1 provider qualification.
Per user request, performs two authenticated requests to Alpaca Historical SIP
endpoint for SPY covering 2016‑11‑01 to 2016‑11‑04 inclusive.
Only prints summary information, never prints credential values.
"""
import sys
from datetime import datetime, timezone
from acash.data.qualification.client import AlpacaHistoricalSipClient
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider

def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def run_probe():
    client = AlpacaHistoricalSipClient(
        credential_provider=EnvAlpacaCredentialProvider(),
    )
    symbol = "SPY"
    start = datetime(2016, 11, 1, tzinfo=timezone.utc)
    end = datetime(2016, 11, 4, tzinfo=timezone.utc)
    # Request A: adjustment=split
    res_split = client.fetch_historical_bars(
        symbol=symbol,
        start_utc=start,
        end_utc=end,
        feed="sip",
        adjustment="split",
        timeframe="1Min",
        limit=10000,
    )
    # Request B: adjustment=raw
    res_raw = client.fetch_historical_bars(
        symbol=symbol,
        start_utc=start,
        end_utc=end,
        feed="sip",
        adjustment="raw",
        timeframe="1Min",
        limit=10000,
    )
    def summarize(r):
        dates = [b.timestamp for b in r.bars]
        if dates:
            min_d = min(dates)
            max_d = max(dates)
        else:
            min_d = max_d = None
        return len(r.bars), iso(min_d) if min_d else "N/A", iso(max_d) if max_d else "N/A"
    split_cnt, split_min, split_max = summarize(res_split)
    raw_cnt, raw_min, raw_max = summarize(res_raw)
    print(f"SPLIT_REQUEST_ROWS = {split_cnt}")
    print(f"SPLIT_MIN_DATE = {split_min}")
    print(f"SPLIT_MAX_DATE = {split_max}")
    print(f"RAW_REQUEST_ROWS = {raw_cnt}")
    print(f"RAW_MIN_DATE = {raw_min}")
    print(f"RAW_MAX_DATE = {raw_max}")
    def within_bounds(min_str, max_str):
        if min_str == "N/A" or max_str == "N/A":
            return False
        min_dt = datetime.fromisoformat(min_str.replace('Z','+00:00'))
        max_dt = datetime.fromisoformat(max_str.replace('Z','+00:00'))
        return start <= min_dt <= end and start <= max_dt <= end
    print(f"SPLIT_WITHIN_BOUNDS = {within_bounds(split_min, split_max)}")
    print(f"RAW_WITHIN_BOUNDS = {within_bounds(raw_min, raw_max)}")

if __name__ == "__main__":
    try:
        run_probe()
    except Exception as e:
        print(f"PROBE_ERROR = {e}")
        sys.exit(1)
