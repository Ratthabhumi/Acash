"""Execution Script: MEC-0014 SPY Primary Close Coverage Census (2017–2022).

Executes a full-sample primary closing auction coverage census for SPY across all
1498 regular sessions (2017–2022) to determine whether historical fallback AOCP
logic is required for the observed MEC-0014 research sample.

STRICT INVARIANTS:
1. In-Sample Scope: 2017-01-01 through 2022-12-31 ONLY.
2. Hard OOS Block: >= 2023-01-01 aborts immediately.
3. Pure Data-Contract Coverage: Zero returns, zero r1/r13, zero regressions, zero signals.
4. Secret Non-Leakage: Never prints or logs API keys/secrets.
5. Sovereign Calendar: NyseCa1Calendar regular sessions only.
6. Provenance: Cryptographically tracks raw payloads and census manifest.

Usage:
    uv run python scripts/execute_mec_0014_coverage_census.py
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.mec_0014_close_contract import AuctionRecord
from acash.data.qualification.mec_0014_coverage_census import (
    AuctionCoverageClassification,
    CoverageCensusResult,
    CoverageDecisionClassification,
    SessionAuctionCoverage,
    classify_session_auctions,
    enumerate_qualified_regular_sessions,
    evaluate_census_results,
)
from acash.research.step_r2_hyp_003 import resolve_alpaca_credentials

BASE_URL = "https://data.alpaca.markets"
RAW_CENSUS_DIR = Path("data/raw/research/MEC_0014/coverage_census")
TRACKED_MANIFEST_PATH = Path("docs/research/manifests/MEC-0014-spy-close-coverage-manifest.json")
TRACKED_REPORT_PATH = Path("docs/research/MEC-0014-spy-close-coverage-report.md")


def get_git_head_sha() -> str:
    """Retrieve current Git HEAD SHA."""
    res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return res.stdout.strip()


def run_coverage_census() -> int:
    print("================================================================================")
    print("ACASH MEC-0014: SPY PRIMARY CLOSE COVERAGE CENSUS (2017–2022)")
    print("Scope: 2017-01-01 through 2022-12-31 | NyseCa1Calendar Regular Sessions (390m)")
    print("Rule: Data-Contract Coverage Qualification ONLY — Zero Return/Alpha Calculations")
    print("================================================================================")

    # 1. Resolve credentials safely
    print("\n[Step 1] Resolving Alpaca API Credentials...")
    creds = resolve_alpaca_credentials()
    if creds is None or not creds.resolved or not creds.api_key_id:
        print("ERROR: Alpaca credentials could not be resolved from environment or .env.")
        return 1
    print("Credentials resolved successfully. (Values redacted)")

    headers = {
        "APCA-API-KEY-ID": creds.api_key_id,
        "APCA-API-SECRET-KEY": creds.api_secret_ref,
        "Accept": "application/json",
    }

    # 2. Enumerate sovereign calendar sessions
    print("\n[Step 2] Enumerating Sovereign NyseCa1Calendar Regular Sessions...")
    cal = NyseCa1Calendar()
    regular_sessions = enumerate_qualified_regular_sessions(
        calendar=cal,
        start_date=date(2017, 1, 1),
        end_date=date(2022, 12, 31),
    )
    total_sessions = len(regular_sessions)
    print(f"Total Qualified Regular 390m Sessions: {total_sessions}")
    if total_sessions != 1498:
        print(f"ERROR: Expected 1498 regular sessions for 2017–2022, found {total_sessions}.")
        return 1

    RAW_CENSUS_DIR.mkdir(parents=True, exist_ok=True)
    TRACKED_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 3. Retrieve Historical Auctions year-by-year with pagination
    print("\n[Step 3] Querying Historical Auctions Endpoint (feed=sip, symbol=SPY)...")
    symbol = "SPY"
    years = [2017, 2018, 2019, 2020, 2021, 2022]
    raw_payload_hashes: Dict[str, str] = {}
    all_auctions_by_date: Dict[str, List[AuctionRecord]] = {}

    with httpx.Client(timeout=60.0) as client:
        for yr in years:
            yr_start = f"{yr}-01-01"
            yr_end = f"{yr}-12-31"
            page_idx = 1
            next_token: Optional[str] = None
            yr_payload_files: List[Path] = []

            while True:
                cache_file = RAW_CENSUS_DIR / f"auctions_{symbol}_{yr}_p{page_idx}.json"
                if cache_file.is_file():
                    raw_bytes = cache_file.read_bytes()
                    print(f"  [{yr}] Page {page_idx}: Loaded from local cache.")
                    payload = json.loads(raw_bytes)
                else:
                    url = f"{BASE_URL}/v2/stocks/{symbol}/auctions"
                    params: Dict[str, str] = {
                        "start": yr_start,
                        "end": yr_end,
                        "feed": "sip",
                    }
                    if next_token:
                        params["page_token"] = next_token

                    r = client.get(url, headers=headers, params=params)
                    if r.status_code != 200:
                        print(f"ERROR: Failed fetching auctions for {yr} p{page_idx}: HTTP {r.status_code} - {r.text}")
                        return 1
                    raw_bytes = r.content
                    cache_file.write_bytes(raw_bytes)
                    print(f"  [{yr}] Page {page_idx}: Fetched {len(raw_bytes)} bytes from Alpaca.")
                    payload = r.json()

                file_hash = hashlib.sha256(raw_bytes).hexdigest()
                raw_payload_hashes[cache_file.name] = file_hash

                # Parse auction records into date buckets
                auctions_list = payload.get("auctions", [])
                if isinstance(auctions_list, dict):
                    # Multi-symbol map fallback
                    auctions_list = auctions_list.get(symbol, [])

                for entry in auctions_list:
                    if not isinstance(entry, dict):
                        continue
                    d_str = str(entry.get("d", ""))
                    if not d_str:
                        continue
                    if d_str not in all_auctions_by_date:
                        all_auctions_by_date[d_str] = []

                    # Closing auctions
                    for c_auc in entry.get("c") or []:
                        all_auctions_by_date[d_str].append(
                            AuctionRecord(
                                timestamp_utc=str(c_auc["t"]),
                                price=Decimal(str(c_auc["p"])),
                                size=int(c_auc["s"]),
                                exchange=str(c_auc["x"]),
                                condition=str(c_auc.get("c", "")),
                                auction_type="c",
                            )
                        )
                    # Opening auctions
                    for o_auc in entry.get("o") or []:
                        all_auctions_by_date[d_str].append(
                            AuctionRecord(
                                timestamp_utc=str(o_auc["t"]),
                                price=Decimal(str(o_auc["p"])),
                                size=int(o_auc["s"]),
                                exchange=str(o_auc["x"]),
                                condition=str(o_auc.get("c", "")),
                                auction_type="o",
                            )
                        )

                next_token = payload.get("next_page_token")
                if not next_token:
                    print(f"  [{yr}] Completed. Pagination closed (next_page_token=None).")
                    break
                page_idx += 1

    # 4. Classify each regular session strictly
    print("\n[Step 4] Classifying All 1498 Regular Sessions...")
    session_coverages: List[SessionAuctionCoverage] = []
    for s_date in regular_sessions:
        d_iso = s_date.isoformat()
        records = all_auctions_by_date.get(d_iso, [])
        cov = classify_session_auctions(session_date=s_date, auctions=records, target_symbol=symbol)
        session_coverages.append(cov)

    # 5. Evaluate overall census results
    print("\n[Step 5] Synthesizing Sample Coverage Decision...")
    census_result = evaluate_census_results(session_coverages, expected_session_count=total_sessions)

    print(f"  Total Qualified Sessions: {census_result.total_qualified_sessions}")
    print(f"  Total Queried Sessions:   {census_result.total_queried_sessions}")
    print(f"  UNIQUE_PRIMARY_AUCTION:   {census_result.unique_count}")
    print(f"  MISSING_PRIMARY_AUCTION:  {census_result.missing_count}")
    print(f"  AMBIGUOUS_PRIMARY_AUCTION:{census_result.ambiguous_count}")
    print(f"  Coverage Percentage:      {census_result.coverage_percentage}")
    print(f"  Decision Classification:  {census_result.decision.value}")
    print(f"  Historical Fallback:      {census_result.historical_fallback_requirement}")

    if census_result.missing_count > 0:
        print(f"\n[ALERT] Missing Sessions: {census_result.missing_dates}")
    if census_result.ambiguous_count > 0:
        print(f"\n[ALERT] Ambiguous Sessions: {census_result.ambiguous_dates}")

    # 6. Generate deterministic manifest
    print("\n[Step 6] Generating Tracked Manifest...")
    git_head = get_git_head_sha()
    manifest_data = {
        "manifest_type": "MEC_0014_SPY_CLOSE_COVERAGE_CENSUS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "calendar_authority": "NyseCa1Calendar",
        "session_type": "REGULAR (390m)",
        "in_sample_window": {
            "start": "2017-01-01",
            "end": "2022-12-31",
            "oos_boundary_strictly_forbidden": ">= 2023-01-01",
        },
        "target_symbol": "SPY",
        "primary_venue_qualified": "x=P, c=6 (NYSE Arca Market Center Closing Trade)",
        "summary": census_result.to_dict(),
        "raw_payload_hashes": raw_payload_hashes,
    }

    manifest_json = json.dumps(manifest_data, indent=2, sort_keys=True)
    TRACKED_MANIFEST_PATH.write_text(manifest_json + "\n", encoding="utf-8")
    print(f"Manifest written to: {TRACKED_MANIFEST_PATH}")

    # 7. Generate research report
    print("\n[Step 7] Generating Research Report...")
    report_md = _generate_coverage_report(census_result, git_head, raw_payload_hashes)
    TRACKED_REPORT_PATH.write_text(report_md, encoding="utf-8")
    print(f"Report written to: {TRACKED_REPORT_PATH}")

    print("\n[Census Execution Complete]")
    if census_result.decision == CoverageDecisionClassification.COMPLETE_NORMAL_PATH:
        print("RESULT: 100% Complete Normal-Path Coverage Verified. No fallback required for 2017-2022 SPY.")
        return 0
    else:
        print("RESULT: INCOMPLETE COVERAGE DETECTED. Human audit required before commit.")
        return 2


def _generate_coverage_report(
    result: CoverageCensusResult,
    git_head: str,
    raw_hashes: Dict[str, str],
) -> str:
    lines = [
        "# MEC-0014: SPY Primary Closing Auction Coverage Census (2017–2022)",
        "",
        f"**Audit Timestamp (UTC):** `{datetime.now(timezone.utc).isoformat()}`<br>",
        f"**Source Git Commit SHA:** `{git_head}`<br>",
        "**Governing Calendar:** `NyseCa1Calendar` (Sovereign Authority)<br>",
        "**Target Symbol:** `SPY` (Primary Listing: NYSE Arca, Exchange `P`)<br>",
        "**Qualified Normal Candidate Semantic:** Closing Auction `c=6` on Exchange `P` (`x=P, c=6`)<br>",
        "**Data Source:** Alpaca Market Data API v2 (`/v2/stocks/SPY/auctions`, `feed=sip`)",
        "",
        "---",
        "",
        "## 1. Executive Summary & Decision Ruling",
        "",
    ]

    if result.decision == CoverageDecisionClassification.COMPLETE_NORMAL_PATH:
        lines.extend([
            "> [!IMPORTANT]",
            "> **CENSUS VERDICT: COMPLETE NORMAL PATH (100% COVERAGE)**",
            f"> Every single qualified regular trading session from 2017-01-01 through 2022-12-31 ({result.total_qualified_sessions}/{result.total_qualified_sessions} sessions) contains **exactly one qualifying NYSE Arca primary closing auction cross** (`x=P, c=6`).",
            "> ",
            f"> - **`SPY_PRIMARY_CLOSE_COVERAGE_2017_2022`**: `COMPLETE_NORMAL_PATH`",
            f"> - **`HISTORICAL_EXCEPTIONAL_CLOSE_FALLBACK`**: `NOT_REQUIRED_FOR_OBSERVED_2017_2022_SPY_SESSIONS`",
            "> - **`PREVIOUS_CLOSE_FALLBACK_POLICY`**: Preserved as `OPEN_REGIME_DEPENDENT` for unobserved/future exceptional sessions, but **not required for the 2017–2022 SPY research partition**.",
            "> ",
            "> **Architectural Consequence:** Reconstruction and implementation of the complex NYSE Arca AOCP fallback engine (NBBO midpoint TWAP + consolidated last sale weighting) is **strictly bypassed for observed MEC-0014A dataset preparation**, eliminating historical regime emulation risk.",
        ])
    else:
        lines.extend([
            "> [!CAUTION]",
            "> **CENSUS VERDICT: INCOMPLETE COVERAGE DETECTED**",
            f"> Anomalous sessions detected ({result.missing_count} missing, {result.ambiguous_count} ambiguous).",
            f"> - **`SPY_PRIMARY_CLOSE_COVERAGE_2017_2022`**: `INCOMPLETE_REQUIRES_EXCEPTIONAL_PATH_AUDIT`",
            f"> - **`HISTORICAL_EXCEPTIONAL_CLOSE_FALLBACK`**: `REQUIRED_FOR_UNCOVERED_SESSIONS`",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## 2. Census Metrics & Coverage Breakdown",
        "",
        "| Metric | Value | Compliance Status |",
        "| :--- | :---: | :--- |",
        f"| **Total Qualified Regular Sessions (NyseCa1Calendar)** | `{result.total_qualified_sessions}` | Regular 390m sessions only (excluding early closes) |",
        f"| **Total Sessions Queried & Matched** | `{result.total_queried_sessions}` | Exact match with calendar authority |",
        f"| **Unique Primary Auction Crosses (`x=P, c=6`)** | `{result.unique_count}` | Primary candidate identified |",
        f"| **Missing Primary Auction Sessions** | `{result.missing_count}` | {'CLEAN (0)' if result.missing_count == 0 else 'ANOMALY DETECTED'} |",
        f"| **Ambiguous Primary Auction Sessions (>1 print)** | `{result.ambiguous_count}` | {'CLEAN (0)' if result.ambiguous_count == 0 else 'ANOMALY DETECTED'} |",
        f"| **Effective Sample Coverage Percentage** | `{result.coverage_percentage}` | {'100.0000% COMPLETE' if result.coverage_percentage == '100.0000%' else 'INCOMPLETE'} |",
        "",
        "---",
        "",
        "## 3. Anomalous Sessions Enumeration",
        "",
    ])

    if result.missing_count == 0 and result.ambiguous_count == 0:
        lines.extend([
            "**Zero Anomalous Sessions Detected.**",
            "- Missing Sessions: `[]`",
            "- Ambiguous Sessions: `[]`",
            "",
            "Every regular session in 2017–2022 resolved to a unique, deterministic NYSE Arca closing cross.",
        ])
    else:
        lines.append("### Anomalous Session Details")
        for anom in result.anomalous_sessions:
            lines.append(f"- **Date:** `{anom['session_date']}` | **Classification:** `{anom['classification']}` | **Candidates:** `{anom['candidate_count']}`")
            lines.append(f"  ```json\n  {json.dumps(anom, indent=2)}\n  ```")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Cryptographic Provenance & Evidence Manifest",
        "",
        f"- **Tracked Manifest:** [`docs/research/manifests/MEC-0014-spy-close-coverage-manifest.json`](file:///{TRACKED_MANIFEST_PATH.as_posix()})",
        "- **Raw Payload SHA-256 Hashes:**",
    ])
    for fname, h in sorted(raw_hashes.items()):
        lines.append(f"  - `{fname}`: `{h}`")

    lines.extend([
        "",
        "> [!NOTE]",
        "> **Governance Invariants:**",
        "> - Zero Out-of-Sample (OOS 2023–2026) data was accessed.",
        "> - Zero returns ($r_1, r_{13}$), regressions, correlations, Sharpe, or signals were computed.",
        "> - `HYP_004` remains strictly ABSENT; `ResearchReInceptionGate` NOT invoked.",
        "> - Sovereign capital remains `$0.00`; `NO_REAL_ORDERS = true`.",
    ])

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(run_coverage_census())
