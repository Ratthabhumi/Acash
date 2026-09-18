"""Read-only / dry-run qualification probe command for historical SIP data.

SEMANTICS:
- Narrow data-source qualification probe only.
- NOT a backtest.
- NOT a strategy run.
- NOT a data ingestion pipeline activation.
- Default behavior: DRY-RUN with network access DISABLED.
- Real outbound network calls require the explicit operator flag: --execute-network.
"""

from __future__ import annotations

import argparse
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
from typing import List, Optional

from acash.data.qualification.client import AlpacaHistoricalSipClient
from acash.data.qualification.engine import HistoricalSipQualificationEngine
from acash.data.qualification.guard import FifteenMinuteAccessGuard
from acash.data.qualification.models import (
    HistoricalSipBar,
    QualificationCheckStatus,
    SourceQualificationReport,
    SourceQualificationStatus,
    VwapAuthorityStatus,
)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m acash.data.qualification.cli",
        description="ACASH Historical SIP Data Source Qualification Probe (Read-Only / Dry-Run).",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="SPY",
        help="Target symbol for the qualification probe (default: SPY; probe example only, not candidate selection).",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Historical trading date to probe in YYYY-MM-DD format (defaults to 2 business days ago).",
    )
    parser.add_argument(
        "--start-utc",
        type=str,
        default=None,
        help="Explicit start UTC timestamp (ISO-8601, e.g. 2024-01-02T14:30:00Z).",
    )
    parser.add_argument(
        "--end-utc",
        type=str,
        default=None,
        help="Explicit end UTC timestamp (ISO-8601, e.g. 2024-01-02T21:00:00Z). Must be >= 15m old.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("var/data/qualification"),
        help="Directory to save local provenance manifest outside git (default: var/data/qualification).",
    )
    parser.add_argument(
        "--execute-network",
        action="store_true",
        default=False,
        help="Explicit human operator flag required to execute live network requests. Default is FALSE (dry-run).",
    )
    return parser.parse_args(args)


def run_probe(args: argparse.Namespace) -> int:
    """Execute the qualification probe command."""
    symbol = args.symbol.strip().upper()
    print("=" * 70)
    print("ACASH HISTORICAL SIP SOURCE QUALIFICATION PROBE")
    print("=" * 70)
    print(f"Target Symbol:            {symbol}")
    print(f"Network Execution Flag:   {args.execute_network}")
    print(f"Output Directory:         {args.output_dir}")

    # Determine start/end UTC
    if args.start_utc and args.end_utc:
        start_utc = datetime.fromisoformat(args.start_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        end_utc = datetime.fromisoformat(args.end_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
    elif args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d").date()
        # Nominal regular hours: 09:30 - 16:00 ET -> UTC 14:30 - 21:00 (EDT) or 13:30 - 20:00 (EST)
        # Using America/New_York zoneinfo for exact conversion
        from zoneinfo import ZoneInfo
        ny_tz = ZoneInfo("America/New_York")
        start_dt = datetime.combine(d, time(9, 30, 0), tzinfo=ny_tz)
        end_dt = datetime.combine(d, time(16, 0, 0), tzinfo=ny_tz)
        start_utc = start_dt.astimezone(timezone.utc)
        end_utc = end_dt.astimezone(timezone.utc)
    else:
        # Default: 2 business days ago
        now = datetime.now(timezone.utc)
        target_day = now - timedelta(days=2)
        while target_day.weekday() >= 5:  # Saturday or Sunday
            target_day -= timedelta(days=1)
        d = target_day.date()
        from zoneinfo import ZoneInfo
        ny_tz = ZoneInfo("America/New_York")
        start_dt = datetime.combine(d, time(9, 30, 0), tzinfo=ny_tz)
        end_dt = datetime.combine(d, time(16, 0, 0), tzinfo=ny_tz)
        start_utc = start_dt.astimezone(timezone.utc)
        end_utc = end_dt.astimezone(timezone.utc)

    print(f"Requested Start UTC:      {start_utc.isoformat()}")
    print(f"Requested End UTC:        {end_utc.isoformat()}")

    # 15-minute guard check
    guard = FifteenMinuteAccessGuard()
    try:
        guard.validate_requested_end(end_utc)
        print("15-Minute Access Guard:   PASS (requested end is safely historical)")
    except Exception as e:
        print(f"15-Minute Access Guard:   FAIL ({e})")
        return 2

    if not args.execute_network:
        print("\n[DRY-RUN MODE] Network execution was NOT requested (--execute-network not supplied).")
        print("Dry-run probe validated arguments, temporal boundaries, and fail-closed contracts successfully.")
        print("Zero network sockets opened. Zero data requested.")
        return 0

    print("\n[LIVE PROBE MODE] Executing live network qualification probe...")
    engine = HistoricalSipQualificationEngine(guard=guard)
    report: SourceQualificationReport = engine.run_qualification(
        symbol=symbol,
        start_utc=start_utc,
        end_utc=end_utc,
        output_dir=args.output_dir,
    )

    print("-" * 70)
    print(f"Request Contract:         {report.request_contract_status.value}")
    print(f"Network Access:           {report.network_access_status.value}")
    print(f"Data Integrity:           {report.data_integrity_status.value}")
    print(f"Provider Provenance:      {report.provider_provenance_status.value}")
    print(f"Overall Source Status:    {report.overall_status.value}")
    print(f"VWAP Authority Status:    {report.vwap_authority_status.value}")
    print(f"Bars Retrieved:           {report.bars_count}")
    print(f"Manifest ID:              {report.manifest.manifest_id}")
    print(f"Manifest Payload Digest:  {report.manifest.composite_raw_payload_sha256}")
    print("-" * 70)

    if report.findings:
        print("Quality Findings / Anomalies:")
        for f in report.findings:
            print(f"  [{f.severity.value}] {f.rule.value}: {f.message}")

    return 0 if report.overall_status in (
        SourceQualificationStatus.CONTRACT_VERIFIED,
        SourceQualificationStatus.ACCESS_VERIFIED,
        SourceQualificationStatus.DATA_SOURCE_TECHNICALLY_QUALIFIED,
    ) else 1


def main() -> None:
    args = parse_args()
    sys.exit(run_probe(args))


if __name__ == "__main__":
    main()
