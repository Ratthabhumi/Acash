"""Phase 14 Step R2 Execution Script: Historical Data Qualification for HYP_003.

Target: SPY 1-Minute Consolidated SIP Historical Aggregates
Temporal Scope: 2017-01-01 through 2022-12-31 (In-Sample ONLY)
OOS Boundary: 2023-01-01 through 2026-12-31 (STRICTLY SEALED / FORBIDDEN)

Usage:
  uv run python scripts/execute_phase14_step_r2_hyp_003.py
"""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.provenance import (
    calculate_canonical_batch_sha256,
    calculate_raw_source_sha256,
)
from acash.data.qualification.client import AlpacaHistoricalSipClient
from acash.data.qualification.models import (
    HistoricalSipBar,
    MarketDataFeed,
    PriceAdjustment,
)
from acash.research.step_r2_hyp_003 import (
    IS_END_DATE,
    IS_START_DATE,
    NY_TZ,
    OOS_SEALED_BOUNDARY_DATE,
    REGULAR_SESSION_BAR_COUNT,
    REGULAR_SESSION_LAST_BAR_TIME,
    REGULAR_SESSION_OPEN_TIME,
    assert_is_boundary,
    build_ca1_session_universe,
    build_canonical_arrow_table,
    create_r2_manifest,
    resolve_alpaca_credentials,
    validate_r2_preconditions,
    validate_session_bars,
)


def run_step_r2() -> int:
    print("================================================================================")
    print("ACASH PHASE 14 STEP R2: HISTORICAL DATA QUALIFICATION & PREPARATION")
    print("Hypothesis: HYP_003 (Opening Range Breakout on SPY — MEC-0013 Price-Only)")
    print("In-Sample Scope: 2017-01-01 through 2022-12-31 | Feed: Consolidated SIP (Raw)")
    print("Out-of-Sample Scope: 2023-01-01 through 2026-12-31 (STRICTLY SEALED)")
    print("================================================================================")

    # 1. Precondition & Hash Verification
    print("\n[Gate 1] Upstream Governance & Lineage Preconditions:")
    preconditions = validate_r2_preconditions()
    print(f" -> HYP_003 Hash: {preconditions['hypothesis_sha256']} (VERIFIED)")
    print(f" -> Preregistration Hash: {preconditions['preregistration_sha256']} (VERIFIED)")
    print(f" -> R1 Manifest Hash: {preconditions['r1_manifest_sha256']} (VERIFIED)")
    print(f" -> Semantic Clarification: {preconditions['clarification_record']} (PRESENT)")

    # 2. CA-1 Calendar Session Universe Census
    print("\n[Gate 2] CA-1 Sovereign Calendar Session Census (2017-01-01 to 2022-12-31):")
    cal = NyseCa1Calendar()
    universe = build_ca1_session_universe(start_date=IS_START_DATE, end_date=IS_END_DATE, calendar=cal)
    print(f" -> Total Calendar Days: {universe.total_calendar_days}")
    print(f" -> Weekend Days Excluded: {len(universe.weekend_days)}")
    print(f" -> Official Holidays Excluded: {universe.total_holidays}")
    print(f" -> Official Early-Close Sessions Excluded: {universe.total_early_close_sessions}")
    print(f" -> Regular 390-Min Sessions Included: {universe.total_regular_sessions}")
    print(f" -> Total Expected 1-Minute Bars: {universe.total_expected_bars:,}")

    # 3. Credential Check & Stop Point A Handling
    print("\n[Gate 3] Alpaca Data Provider Credentials:")
    creds = resolve_alpaca_credentials()
    key_present = bool(creds and creds.api_key_id)
    sec_present = bool(creds and creds.api_secret_ref)
    print(f" -> Key Present: {key_present}")
    print(f" -> Secret Present: {sec_present}")

    if not key_present or not sec_present or creds is None:
        print("\n" + "=" * 80)
        print("[STOP POINT A] ALPACA API CREDENTIALS UNAVAILABLE IN ENVIRONMENT")
        print("=" * 80)
        print("Preconditions, governance lineage, and CA-1 session census are VERIFIED.")
        print("Network acquisition paused before market data loading (Zero Data Loaded).")
        print("Out-of-Sample window (2023-2026) remains STRICTLY SEALED / UNREAD.")
        print("\nTo execute data acquisition and qualification, either provide a local .env file:")
        print("  APCA_API_KEY_ID=<YOUR_ALPACA_KEY>")
        print("  APCA_API_SECRET_KEY=<YOUR_ALPACA_SECRET>")
        print("or set environment variables in your PowerShell session:")
        print("  $env:APCA_API_KEY_ID = \"<YOUR_ALPACA_KEY>\"")
        print("  $env:APCA_API_SECRET_KEY = \"<YOUR_ALPACA_SECRET>\"")
        print("and re-run:")
        print("  uv run python scripts/execute_phase14_step_r2_hyp_003.py")
        print("=" * 80 + "\n")
        return 0

    print(" -> Credentials: RESOLVED (REDACTED)")

    # 4. Safe Date-Bounded Historical Ingestion (Monthly Batch Optimization)
    print("\n[Gate 4] In-Sample Data Acquisition & Complete Grid Validation:")
    from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
    provider = EnvAlpacaCredentialProvider(
        api_key_id=creds.api_key_id,
        api_secret=creds.api_secret_ref,
    )
    client = AlpacaHistoricalSipClient(
        credential_provider=provider,
    )

    data_raw_dir = Path("data/raw/research/HYP_003/sip_1min")
    data_raw_dir.mkdir(parents=True, exist_ok=True)

    # Group regular sessions by (year, month)
    months_dict: Dict[tuple[int, int], List[date]] = defaultdict(list)
    for sess_date in universe.regular_sessions:
        months_dict[(sess_date.year, sess_date.month)].append(sess_date)

    sorted_months = sorted(months_dict.keys())
    print(f" -> Total Monthly Ingestion Batches: {len(sorted_months)} months")

    for m_idx, (year, month) in enumerate(sorted_months):
        month_sessions = months_dict[(year, month)]
        # Check if all sessions in this month already exist in raw cache
        all_exist = all((data_raw_dir / f"SPY_{d.isoformat()}.json").exists() for d in month_sessions)
        if all_exist:
            continue

        first_sess = cal.get_session(month_sessions[0])
        last_sess = cal.get_session(month_sessions[-1])
        # Regular trading hours: 09:30 through 15:59:00 (close - 1 min)
        start_utc = first_sess.open_utc
        end_utc = last_sess.close_utc - timedelta(minutes=1)

        print(f" -> Fetching {year:04d}-{month:02d} ({len(month_sessions)} sessions: {month_sessions[0]} to {month_sessions[-1]})...")
        retrieval = client.fetch_historical_bars(
            symbol="SPY",
            start_utc=start_utc,
            end_utc=end_utc,
            feed=MarketDataFeed.SIP,
            adjustment=PriceAdjustment.RAW,
            limit=10000,
        )

        # Group returned bars by regular session date
        bars_by_date: Dict[date, List[HistoricalSipBar]] = defaultdict(list)
        for b in retrieval.bars:
            ts_ny = b.timestamp_utc.astimezone(NY_TZ)
            d = ts_ny.date()
            t = ts_ny.time()
            if d in month_sessions and REGULAR_SESSION_OPEN_TIME <= t <= REGULAR_SESSION_LAST_BAR_TIME:
                bars_by_date[d].append(b)

        # Save raw private evidence per session
        for sess_date in month_sessions:
            s_bars = sorted(bars_by_date.get(sess_date, []), key=lambda x: x.timestamp_utc)
            sess_obj = cal.get_session(sess_date)
            raw_cache_file = data_raw_dir / f"SPY_{sess_date.isoformat()}.json"
            cache_payload: Dict[str, Any] = {
                "session_date": sess_date.isoformat(),
                "start_utc": sess_obj.open_utc.isoformat(),
                "close_utc": (sess_obj.close_utc - timedelta(minutes=1)).isoformat(),
                "bars": [b.model_dump(mode="json") for b in s_bars],
            }
            raw_bytes = json.dumps(cache_payload, indent=2, sort_keys=True).encode("utf-8")
            raw_hash = calculate_raw_source_sha256(raw_bytes)
            cache_payload["raw_source_sha256"] = raw_hash
            raw_cache_file.write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")

    # Load and validate all 1,498 regular sessions
    print("\n -> Validating all regular sessions against canonical 390-min invariant...")
    qualified_sessions: Dict[date, List[HistoricalSipBar]] = {}
    session_ledger_entries: List[Dict[str, Any]] = []
    excluded_counts: Dict[str, int] = {
        "EXCLUDED_WEEKEND": len(universe.weekend_days),
        "EXCLUDED_HOLIDAY": universe.total_holidays,
        "EXCLUDED_EARLY_CLOSE": universe.total_early_close_sessions,
        "EXCLUDED_INCOMPLETE_DATA": 0,
        "EXCLUDED_INVALID_DATA": 0,
    }
    raw_manifest_hashes: List[str] = []

    for idx, sess_date in enumerate(universe.regular_sessions):
        assert_is_boundary(sess_date)
        raw_cache_file = data_raw_dir / f"SPY_{sess_date.isoformat()}.json"
        if not raw_cache_file.exists():
            raise DataContractError(f"Missing expected raw cache file for session {sess_date.isoformat()}")

        with open(raw_cache_file, "r", encoding="utf-8") as f:
            raw_payload = json.load(f)

        bars = [HistoricalSipBar.model_validate(b) for b in raw_payload["bars"]]
        raw_hash = raw_payload.get("raw_source_sha256", "")
        raw_manifest_hashes.append(raw_hash)

        # Validate 390 bars
        val_result = validate_session_bars(sess_date, bars)
        if val_result.is_valid:
            qualified_sessions[sess_date] = list(bars)
            session_ledger_entries.append({
                "date": sess_date.isoformat(),
                "status": "INCLUDED_REGULAR_SESSION",
                "bars_expected": REGULAR_SESSION_BAR_COUNT,
                "bars_actual": len(bars),
                "raw_source_sha256": raw_hash,
            })
        else:
            reason = "; ".join(val_result.error_reasons)
            print(f" [!] Session {sess_date.isoformat()} EXCLUDED: {reason}")
            if val_result.bar_count != REGULAR_SESSION_BAR_COUNT:
                excluded_counts["EXCLUDED_INCOMPLETE_DATA"] += 1
                status = "EXCLUDED_INCOMPLETE_DATA"
            else:
                excluded_counts["EXCLUDED_INVALID_DATA"] += 1
                status = "EXCLUDED_INVALID_DATA"
            session_ledger_entries.append({
                "date": sess_date.isoformat(),
                "status": status,
                "bars_expected": REGULAR_SESSION_BAR_COUNT,
                "bars_actual": len(bars),
                "reason": reason,
                "raw_source_sha256": raw_hash,
            })

    print(f" -> Validation complete: {len(qualified_sessions)} / {universe.total_regular_sessions} sessions qualified.")

    # 5. Build Canonical Arrow & Parquet Dataset
    print("\n[Gate 5] Assembling Canonical PyArrow Table & Parquet Part:")
    table = build_canonical_arrow_table(qualified_sessions, symbol="SPY", timeframe="1Min")
    total_bars = table.num_rows
    print(f" -> Total Qualified Canonical Rows: {total_bars:,}")

    first_ts = table["event_start_utc"][0].as_py().isoformat()
    last_ts = table["event_start_utc"][-1].as_py().isoformat()
    print(f" -> First Bar UTC: {first_ts}")
    print(f" -> Last Bar UTC:  {last_ts}")

    parquet_dir = Path("data/parquet/research")
    parquet_dir.mkdir(parents=True, exist_ok=True)
    parquet_file = parquet_dir / "HYP_003_SPY_1Min_IS_canonical.parquet"
    pq.write_table(table, parquet_file, compression="zstd")
    print(f" -> Wrote Canonical Parquet: {parquet_file}")

    canonical_batch_sha256 = calculate_canonical_batch_sha256(table)
    print(f" -> Canonical Batch SHA-256: {canonical_batch_sha256}")

    aggregate_raw_hasher = hashlib.sha256()
    for h in sorted(raw_manifest_hashes):
        aggregate_raw_hasher.update(h.encode("utf-8"))
    raw_evidence_sha256 = aggregate_raw_hasher.hexdigest()

    # 6. Persist Ledger and Durable Manifest
    print("\n[Gate 6] Emitting R2 Manifest & Audit Ledger:")
    ledger_file = Path("data/manifests/research/HYP_003_session_ledger.json")
    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    ledger_file.write_text(json.dumps(session_ledger_entries, indent=2), encoding="utf-8")
    print(f" -> Persisted Session Ledger: {ledger_file}")

    manifest_data = create_r2_manifest(
        hypothesis_sha256=preconditions["hypothesis_sha256"],
        preregistration_sha256=preconditions["preregistration_sha256"],
        semantic_clarification_commit="9b12040e2d4654da32f737be5b4ba84123b23e58",
        source_git_sha="9b12040e2d4654da32f737be5b4ba84123b23e58",
        total_expected_regular_sessions=universe.total_regular_sessions,
        included_sessions_count=len(qualified_sessions),
        excluded_sessions_breakdown=excluded_counts,
        total_canonical_bars=total_bars,
        first_timestamp_utc=first_ts,
        last_timestamp_utc=last_ts,
        canonical_dataset_sha256=canonical_batch_sha256,
        raw_evidence_aggregate_sha256=raw_evidence_sha256,
        status="STEP_R2_HISTORICAL_DATA_QUALIFIED_PASS",
    )

    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest_data)
    manifest_p14_file = Path("docs/phase14/manifests/manifest_r2_HYP_003.json")
    manifest_p14_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_p14_file.write_text(json.dumps(json.loads(manifest_json), indent=2), encoding="utf-8")
    print(f" -> Persisted R2 Manifest: {manifest_p14_file}")

    # 7. Write Phase 14 Step R2 Data Preparation Audit Record
    audit_md_file = Path("docs/phase14/phase14_r2_data_preparation_audit_HYP_003.md")
    audit_md_content = f"""# Phase 14 Step R2 Data Preparation & Qualification Audit: HYP_003

```text
[HUMAN-RATIFIED LINEAGE]
[STEP R2 COMPLETE]
[IN-SAMPLE ONLY: 2017-01-01 TO 2022-12-31]
[OUT-OF-SAMPLE SEALED: 2023-01-01 TO 2026-12-31]
[FEED: CONSOLIDATED SIP (RAW)]
[CALENDAR AUTHORITY: NYSE CA-1]
[STEP R3 LOCKED]
[ZERO BACKTEST CALCULATIONS]
```

- **Document ID:** `docs/phase14/phase14_r2_data_preparation_audit_HYP_003.md`
- **Target Hypothesis:** `HYP_003` (Opening Range Breakout on `SPY` under MEC-0013 Price-Only Mechanics)
- **Mechanism ID:** `MEC-0013`
- **Upstream Governance Basis:**
  - `docs/phase14/mec_0013_price_only_preregistration.md` (SHA-256: `{preconditions['preregistration_sha256']}`)
  - `docs/phase14/hypotheses/HYP_003.json` (SHA-256: `{preconditions['hypothesis_sha256']}`)
  - `docs/phase14/manifests/manifest_r1_HYP_003.json` (SHA-256: `{preconditions['r1_manifest_sha256']}`)
  - `docs/phase14/phase14_r1_semantic_conformance_record_HYP_003.md` (Commit: `9b12040e2d4654da32f737be5b4ba84123b23e58`)
- **Step R2 Durable Manifest:** `docs/phase14/manifests/manifest_r2_HYP_003.json`
- **Session Ledger:** `data/manifests/research/HYP_003_session_ledger.json`
- **Canonical Parquet:** `data/parquet/research/HYP_003_SPY_1Min_IS_canonical.parquet`
- **Canonical Dataset SHA-256:** `{canonical_batch_sha256}`
- **Raw Evidence Aggregate SHA-256:** `{raw_evidence_sha256}`
- **Execution Date:** `{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}`

---

## 1. Executive Summary

Under the explicit Human authorization for Step R2 execution, the quantitative historical dataset for hypothesis `HYP_003` has been ingested, validated, and sealed strictly within the In-Sample temporal window (`2017-01-01` to `2022-12-31`).

- **Total Calendar Days in Window:** {universe.total_calendar_days}
- **Weekend Days Excluded:** {len(universe.weekend_days)}
- **Official Exchange Holidays Excluded:** {universe.total_holidays}
- **Official Early-Close Sessions Excluded:** {universe.total_early_close_sessions}
- **Regular Sessions Expected (390-min):** {universe.total_regular_sessions}
- **Regular Sessions Qualified:** {len(qualified_sessions)}
- **Total Incomplete Sessions:** {excluded_counts['EXCLUDED_INCOMPLETE_DATA']}
- **Total Canonical 1-Minute Bars:** {total_bars:,}
- **First Bar Timestamp (UTC):** `{first_ts}`
- **Last Bar Timestamp (UTC):** `{last_ts}`

Zero strategy signals, zero breakout calculations, zero trades, and zero PnL/Sharpe calculations were performed during this step. Out-of-Sample data (`2023-01-01` through `2026-12-31`) remains strictly unread, unopened, and sealed.

---

## 2. Calendar Authority & Session Census (CA-1)

Sovereign calendar authority `NyseCa1Calendar` was used to classify all {universe.total_calendar_days} days in the In-Sample period:

| Category | Count | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Regular Sessions (390m)** | {universe.total_regular_sessions} | Qualified ({len(qualified_sessions)} passed) | Monotonic 1m bars from 09:30 to 15:59 ET |
| **Early Close Sessions (210m)** | {universe.total_early_close_sessions} | Excluded | Day after Thanksgiving, Christmas Eve, etc. |
| **Official Holidays** | {universe.total_holidays} | Excluded | Full market closures |
| **Weekend Days** | {len(universe.weekend_days)} | Excluded | Saturdays and Sundays |
| **Total Calendar Days** | {universe.total_calendar_days} | 100% Accounted | Complete partition coverage |

---

## 3. Data Ingestion & Validation Integrity

- **Provider:** Alpaca Markets Historical Data API v2 (`/v2/stocks/SPY/bars`)
- **Feed:** Consolidated Tape (`feed=sip`)
- **Price Adjustment:** Raw unadjusted (`adjustment=raw`)
- **Bar Invariant:** Exactly 390 bars per regular session. Every bar validated for:
  1. Time alignment strictly within regular trading hours (`09:30:00` to `15:59:00` America/New_York)
  2. Timestamp strict monotonicity (strictly increasing, zero duplicates)
  3. Price positivity (`open > 0`, `high > 0`, `low > 0`, `close > 0`)
  4. OHLC geometric consistency (`high >= low`, `high >= open`, `high >= close`, `low <= open`, `low <= close`)
  5. Non-negative volume (`volume >= 0`)
- **Arrow Canonical Schema:** `CANONICAL_ARROW_SCHEMA` (`timestamp[us, tz=UTC]`, `decimal128(38,18)`, `int64`)

---

## 4. Cryptographic Lineage & Sealing

- **Canonical Parquet SHA-256:** `{canonical_batch_sha256}`
- **Raw Evidence Aggregate SHA-256:** `{raw_evidence_sha256}`
- **Manifest Location:** `docs/phase14/manifests/manifest_r2_HYP_003.json`
- **Session Ledger Location:** `data/manifests/research/HYP_003_session_ledger.json`

---

## 5. Boundary Preservation & Governance Invariants

```markdown
### Verification Ledger
- Implementation Status: COMPLETE
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: NyseCa1Calendar (CA-1) & SEC SIP Consolidated Tape
- Temporal Scope: 2017-01-01 to 2022-12-31 (In-Sample ONLY)
- Out-of-Sample Window: 2023-01-01 to 2026-12-31 (SEALED / UNREAD / FORBIDDEN)
- Step R3 Status: LOCKED (NOT INVOKED)
- Backtest Calculations: NONE (ZERO SIGNALS / ZERO TRADES)
- Capital Authority: $0.00
- Execution Policy: NO_REAL_ORDERS=true
```
"""
    audit_md_file.parent.mkdir(parents=True, exist_ok=True)
    audit_md_file.write_text(audit_md_content, encoding="utf-8")
    print(f" -> Persisted Audit Report: {audit_md_file}")

    print("\n" + "=" * 80)
    print("[STOP POINT B] STEP R2 HISTORICAL DATA QUALIFICATION COMPLETE")
    print("Zero strategy calculations executed. Backtesting and Step R3 remain LOCKED.")
    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_step_r2())

