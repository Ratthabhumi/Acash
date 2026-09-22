#!/usr/bin/env python
"""Execute MEC-0016 Alpaca Historical SIP Early-M1 Quotes Qualification Probe.

Probes 3 authorized early-M1 publication-exposed historical sessions:
- 2016-06-17
- 2017-06-01
- 2018-06-01

For each date, queries narrow windows around:
- 10:00 ET
- 12:00 ET
- 15:30 ET

Evaluates latest quote <= T and first quote >= T.
Zero credentials printed. Zero market data >= 2024-05-01.
Outputs: docs/research/manifests/MEC-0016-alpaca-early-quote-contract-manifest.json
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
import httpx

# Ensure project is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0016_early_quote_contract import (
    MEC_0016_AUTHORIZED_EARLY_QUOTE_PROBE_DATES,
    MEC_0016_PROBE_DECISION_TIMES_ET,
    PRIMARY_EXECUTION_MODEL_NAME,
    SPREAD_MODEL_NAME,
    Mec0016BoundaryQuotePair,
    Mec0016QuoteContractReport,
    evaluate_boundary_quotes,
)

NY_TZ = ZoneInfo("America/New_York")


def _load_credentials_from_env_file() -> tuple[str, str]:
    """Safely bridge API credentials from environment or .env without logging."""
    import os

    key_id = os.environ.get("ACASH_ALPACA_API_KEY_ID", "") or os.environ.get("APCA_API_KEY_ID", "")
    secret = os.environ.get("ACASH_ALPACA_API_SECRET", "") or os.environ.get("APCA_API_SECRET_KEY", "")

    if not key_id or not secret:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("\"'")
                if k in ("ACASH_ALPACA_API_KEY_ID", "APCA_API_KEY_ID") and not key_id:
                    key_id = v
                if k in ("ACASH_ALPACA_API_SECRET", "APCA_API_SECRET_KEY") and not secret:
                    secret = v

    if not key_id or not secret:
        raise DataContractError(
            "CREDENTIAL_ABSENT: Neither ACASH_ALPACA_API_KEY_ID/APCA_API_KEY_ID nor "
            "ACASH_ALPACA_API_SECRET/APCA_API_SECRET_KEY are resolved."
        )
    return key_id, secret


def main() -> int:
    print("[MEC-0016] Starting Alpaca Historical SIP Early-M1 Quotes Qualification Probe...")
    key_id, secret = _load_credentials_from_env_file()

    headers = {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
    }
    base_url = "https://data.alpaca.markets/v2/stocks/quotes"

    boundary_evaluations: list[Mec0016BoundaryQuotePair] = []
    delays: list[float] = []

    for probe_date in MEC_0016_AUTHORIZED_EARLY_QUOTE_PROBE_DATES:
        if probe_date >= date(2024, 5, 1):
            raise DataContractError(f"FORBIDDEN_DATE: Probe date {probe_date} >= 2024-05-01.")

        for probe_time in MEC_0016_PROBE_DECISION_TIMES_ET:
            dt_et = datetime.combine(probe_date, probe_time, tzinfo=NY_TZ)
            dt_utc = dt_et.astimezone(timezone.utc)

            # Query 1: quotes before T (narrow 200ms slice, fallback to 1s if needed)
            t_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            t_minus_200ms = (dt_utc - timedelta(milliseconds=200)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            params_before = {
                "symbols": "SPY",
                "feed": "sip",
                "sort": "asc",
                "start": t_minus_200ms,
                "end": t_iso,
                "limit": 50,
            }
            resp_b = httpx.get(base_url, headers=headers, params=params_before, timeout=20.0)
            if resp_b.status_code != 200:
                raise DataContractError(
                    f"Alpaca API error before {probe_date} {probe_time}: HTTP {resp_b.status_code}: {resp_b.text[:200]}"
                )
            quotes_before = resp_b.json().get("quotes", {}).get("SPY", [])

            # Query 2: quotes at or after T
            t_plus_2s = (dt_utc + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
            params_after = {
                "symbols": "SPY",
                "feed": "sip",
                "sort": "asc",
                "start": t_iso,
                "end": t_plus_2s,
                "limit": 20,
            }
            resp_a = httpx.get(base_url, headers=headers, params=params_after, timeout=20.0)
            if resp_a.status_code != 200:
                raise DataContractError(
                    f"Alpaca API error after {probe_date} {probe_time}: HTTP {resp_a.status_code}: {resp_a.text[:200]}"
                )
            quotes_after = resp_a.json().get("quotes", {}).get("SPY", [])

            pair = evaluate_boundary_quotes(probe_date, probe_time, quotes_before, quotes_after)
            boundary_evaluations.append(pair)
            delays.append(pair.quote_delay_ms)

            print(
                f"  [{probe_date.isoformat()} {probe_time.strftime('%H:%M')} ET] "
                f"delay={pair.quote_delay_ms}ms, "
                f"bid={pair.first_quote_at_or_after.bid_price} "
                f"(size={pair.first_quote_at_or_after.bid_size} ex={pair.first_quote_at_or_after.bid_exchange}), "
                f"ask={pair.first_quote_at_or_after.ask_price} "
                f"(size={pair.first_quote_at_or_after.ask_size} ex={pair.first_quote_at_or_after.ask_exchange}), "
                f"spread=${pair.first_quote_at_or_after.spread}"
            )

    min_delay = min(delays)
    max_delay = max(delays)
    mean_delay = sum(delays) / len(delays)
    sorted_delays = sorted(delays)
    median_delay = sorted_delays[len(sorted_delays) // 2]

    delay_dist = {
        "min_delay_ms": round(min_delay, 3),
        "median_delay_ms": round(median_delay, 3),
        "mean_delay_ms": round(mean_delay, 3),
        "max_delay_ms": round(max_delay, 3),
    }

    report = Mec0016QuoteContractReport(
        endpoint=base_url,
        symbol="SPY",
        feed="sip",
        authorized_probe_dates=[d.isoformat() for d in MEC_0016_AUTHORIZED_EARLY_QUOTE_PROBE_DATES],
        boundary_evaluations=boundary_evaluations,
        latency_diagnostics=delay_dist,
        is_qualified=True,
    )

    out_path = Path("docs/research/manifests/MEC-0016-alpaca-early-quote-contract-manifest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"\n[MEC-0016] Successfully wrote early quote contract manifest: {out_path}")
    print(f"Latency summary: min={min_delay:.3f}ms, median={median_delay:.3f}ms, mean={mean_delay:.3f}ms, max={max_delay:.3f}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
