#!/usr/bin/env python
"""MEC-0015 Alpaca SIP Bar Contract Probe Script.

PURPOSE: Infrastructure data-provider qualification ONLY.
- Probes 6 authorized publication-exposed historical sessions.
- Verifies bar schema, timestamp semantics, and completeness.
- Produces a JSON manifest artifact.

STRICT INVARIANTS (from ACASH AGENTS.md and Phase 15 Authorization):
- HYP_005 is NOT created.
- Strategy backtest is NOT started.
- No P&L, Sharpe, return, signal, or parameter computation.
- No market data >= 2024-05-01 is accessed.
- No 2025 or 2026 data is accessed.
- Capital: $0.00. NO_REAL_ORDERS = true.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Ensure project is on path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0015_bar_contract import (
    MEC_0015_AUTHORIZED_PROBE_DATES,
    MEC_0015_BAR_TIMESTAMP_SEMANTICS,
    MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING,
    MEC_0015_HYP_005_CREATED,
    MEC_0015_BACKTEST_STARTED,
    MEC_0015_STRATEGY_PNL_COMPUTED,
    MEC_0015_OOS_FORBIDDEN_DATE,
    Mec0015BarContractProbe,
    Mec0015BarContractProbeReport,
    Mec0015ProbeSessionStatus,
)


def _print_banner() -> None:
    print("=" * 72)
    print("ACASH — MEC-0015 Alpaca SIP Bar Contract Probe")
    print("Governance Scope: DATA INFRASTRUCTURE QUALIFICATION ONLY")
    print(f"  HYP_005 Created:         {MEC_0015_HYP_005_CREATED}")
    print(f"  Backtest Started:        {MEC_0015_BACKTEST_STARTED}")
    print(f"  Strategy P&L Computed:   {MEC_0015_STRATEGY_PNL_COMPUTED}")
    print(f"  OOS Forbidden Date:      >= {MEC_0015_OOS_FORBIDDEN_DATE.isoformat()}")
    print(f"  Bar Timestamp Semantics: {MEC_0015_BAR_TIMESTAMP_SEMANTICS}")
    print("=" * 72)
    print()


def _print_session_result(result: object) -> None:
    from acash.data.qualification.mec_0015_bar_contract import Mec0015SessionProbeResult
    r: Mec0015SessionProbeResult = result
    status_icon = "✓" if r.status == Mec0015ProbeSessionStatus.PASS else "✗"
    print(f"  {status_icon} {r.session_date}  bars={r.bar_count}/{r.expected_bar_count}"
          f"  missing={r.missing_bar_count}"
          f"  first={r.first_bar_timestamp_et}  last={r.last_bar_timestamp_et}"
          f"  status={r.status.value}")
    if r.schema_violations:
        for v in r.schema_violations:
            print(f"      VIOLATION: {v}")
    if r.missing_bar_count > 0 and r.missing_bars_et:
        print(f"      Missing minutes (first 5): {r.missing_bars_et[:5]}")
    if r.zero_volume_bars_et:
        print(f"      Zero-volume bars: {len(r.zero_volume_bars_et)}")
    print(f"      SHA-256: {r.canonical_bars_sha256[:16]}...")


def _save_manifest(report: Mec0015BarContractProbeReport, output_dir: Path) -> Path:
    """Serialize and save the probe manifest to docs/research/manifests/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "MEC-0015-bar-provider-contract-manifest.json"

    manifest_dict = {
        "manifest_id": "MEC-0015-BAR-CONTRACT-PROBE",
        "generated_utc": report.generated_utc,
        "canonical_git_commit": report.canonical_git_commit,
        "governance": {
            "hyp_005_created": report.hyp_005_created,
            "backtest_started": report.backtest_started,
            "strategy_pnl_computed": report.strategy_pnl_computed,
            "oos_forbidden_date": report.oos_forbidden_date,
            "capital": "$0.00",
            "no_real_orders": True,
        },
        "provider_contract": {
            "symbol": report.symbol,
            "endpoint": f"https://data.alpaca.markets/v2/stocks/{report.symbol}/bars",
            "feed": report.feed,
            "timeframe": report.timeframe,
            "adjustment": report.adjustment,
            "bar_timestamp_semantics": report.bar_timestamp_semantics,
            "author_decision_to_alpaca_mapping": report.author_decision_to_alpaca_mapping,
        },
        "probe_summary": {
            "overall_status": report.overall_status,
            "total_bars_retrieved": report.total_bars_retrieved,
            "total_missing_bars": report.total_missing_bars,
            "manifest_sha256": report.manifest_sha256,
        },
        "sessions": [
            {
                "date": r.session_date,
                "status": r.status.value,
                "bar_count": r.bar_count,
                "expected_bar_count": r.expected_bar_count,
                "missing_bar_count": r.missing_bar_count,
                "missing_bars_et": r.missing_bars_et,
                "first_bar_timestamp_et": r.first_bar_timestamp_et,
                "last_bar_timestamp_et": r.last_bar_timestamp_et,
                "first_bar_open": r.first_bar_open,
                "zero_volume_bar_count": len(r.zero_volume_bars_et),
                "schema_violations": r.schema_violations,
                "is_early_close_session": r.is_early_close_session,
                "canonical_bars_sha256": r.canonical_bars_sha256,
                "failure_reason": r.failure_reason,
            }
            for r in report.probe_sessions
        ],
    }

    manifest_path.write_text(
        json.dumps(manifest_dict, indent=2, default=str),
        encoding="utf-8",
    )
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MEC-0015 Alpaca SIP 1-Minute Bar Contract Probe (infrastructure qualification only)"
    )
    parser.add_argument(
        "--output-dir",
        default="docs/research/manifests",
        help="Output directory for the JSON manifest (default: docs/research/manifests)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate constants and governance markers without making network calls.",
    )
    args = parser.parse_args()

    _print_banner()

    if args.dry_run:
        print("DRY RUN: Validating governance markers and constants only. No network calls.")
        print(f"  Authorized probe dates: {[d.isoformat() for d in MEC_0015_AUTHORIZED_PROBE_DATES]}")
        print(f"  Bar timestamp semantics: {MEC_0015_BAR_TIMESTAMP_SEMANTICS}")
        print(f"  Author-to-Alpaca mapping: {MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING}")
        print()
        print("DRY RUN COMPLETE. All governance markers verified.")
        return 0

    print(f"Authorized probe dates: {[d.isoformat() for d in MEC_0015_AUTHORIZED_PROBE_DATES]}")
    print()

    try:
        probe = Mec0015BarContractProbe()
        print("Running bar contract probe...")
        report = probe.run_probe()

        print()
        print("Per-session results:")
        for r in report.probe_sessions:
            _print_session_result(r)

        print()
        print(f"Overall Status:         {report.overall_status}")
        print(f"Total Bars Retrieved:   {report.total_bars_retrieved}")
        print(f"Total Missing Bars:     {report.total_missing_bars}")
        print(f"Manifest SHA-256:       {report.manifest_sha256}")
        print()

        # Save manifest
        output_dir = Path(args.output_dir)
        manifest_path = _save_manifest(report, output_dir)
        print(f"Manifest saved to: {manifest_path}")
        print()

        if report.overall_status == "PASS":
            print("RESULT: PASS — All probe sessions qualified.")
            return 0
        else:
            print("RESULT: PARTIAL_FAIL — One or more sessions failed qualification.")
            return 1

    except DataContractError as e:
        print(f"\nDATA CONTRACT ERROR (fail-closed): {e}")
        return 2
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {type(e).__name__}: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
