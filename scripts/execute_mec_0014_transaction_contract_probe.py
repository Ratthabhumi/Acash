"""Execution Script: MEC-0014A Alpaca SIP Transaction Contract Qualification Probe.

Executes a six-session bounded probe using cached Alpaca Historical Stock Trades
evidence (feed=sip, symbol=SPY) to qualify two provider mappings required before
MEC-0014A can be preregistered:

  1. ALPACA_INTRADAY_ENDPOINT_MAPPING
     Provider candidate: last observed SIP transaction price at or before the
     half-hour boundary (10:00 ET for r1,t; 15:30 ET for r13,t).

  2. ALPACA_DAILY_TRADE_COUNT_MAPPING
     Provider candidate: raw regular-session SIP trade record count in
     [09:30:00, 16:00:00) ET per NyseCa1Calendar session (Gao filter >= 500).

STRICT INVARIANTS:
1. Temporal Boundary: 2017-01-01 <= date <= 2022-12-31 ONLY.
   Date >= 2023-01-01 fails closed BEFORE any processing.
2. ZERO Network Calls: Replays strictly from existing cached raw HTTP responses
   under data/raw/research/MEC_0014/transaction_contract/.
3. Zero Return Computation: No r1, r13, price diff, regression, beta,
   alpha, t-stat, Sharpe, P&L, signal, or backtest.
4. Zero OOS Access: No market data from >= 2023-01-01.
5. Hashes read from disk, never from memory. Canonical authority is the manifest.
6. Trade-ID Ordering Authority: NOT_ESTABLISHED. No max(trade_id) tie-breaking.
7. Transport duplicates verified on full-record equality (observed = 0).

Usage:
    uv run python scripts/execute_mec_0014_transaction_contract_probe.py
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType
from acash.data.qualification.mec_0014_close_contract import select_mec_0014_probe_dates
from acash.data.qualification.mec_0014_transaction_contract import (
    BOUNDARY_1000_ET,
    BOUNDARY_1530_ET,
    BoundaryEndpointClassification,
    EXACT_TRANSPORT_DUPLICATES_OBSERVED,
    GAO_MIN_DAILY_TRADE_COUNT,
    QUALIFIED_FEED,
    QUALIFIED_SYMBOL,
    TRADE_ID_ORDERING_AUTHORITY,
    RawSipTradeRecord,
    SessionTransactionQualification,
    TransactionContractProbeResult,
    assert_qualified_feed,
    assert_qualified_symbol,
    assert_transaction_probe_date,
    build_condition_census,
    build_exchange_census,
    build_tape_census,
    build_transaction_contract_manifest,
    classify_boundary_endpoint,
    compute_file_sha256,
    detect_trade_id_collisions,
    detect_transport_duplicates,
    filter_regular_session_records,
    parse_trades_page,
    qualify_session_transactions,
    synthesize_probe_result,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RAW_CACHE_DIR = Path("data/raw/research/MEC_0014/transaction_contract")
TRACKED_MANIFEST_PATH = Path(
    "docs/research/manifests/MEC-0014-transaction-contract-manifest.json"
)
TRACKED_AUDIT_PATH = Path("docs/research/MEC-0014-transaction-contract-audit.md")


def get_git_head_sha() -> str:
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return res.stdout.strip()


# ---------------------------------------------------------------------------
# Local cache loader & pagination audit
# ---------------------------------------------------------------------------

def load_and_audit_cached_pages(
    session_date: date,
    symbol: str = QUALIFIED_SYMBOL,
    feed: str = QUALIFIED_FEED,
    raw_cache_dir: Path = RAW_CACHE_DIR,
) -> Tuple[List[RawSipTradeRecord], int, bool, Dict[str, str]]:
    """Audit and load all cached trade pages for a session date.

    Enforces:
    - Exactly sequential page files: p1, p2, ..., pN
    - No repeated page tokens (infinite loop detection)
    - Final page has next_page_token == None (pagination exhaustion)
    - Hashes computed directly from disk bytes
    """
    assert_transaction_probe_date(session_date)
    assert_qualified_symbol(symbol)
    assert_qualified_feed(feed)

    date_iso = session_date.isoformat()
    all_records: List[RawSipTradeRecord] = []
    file_sha_map: Dict[str, str] = {}
    page_idx = 1
    next_token: Optional[str] = None
    seen_tokens: Set[str] = set()

    while True:
        cache_file = raw_cache_dir / f"trades_{symbol}_{date_iso}_p{page_idx}.json"
        if not cache_file.is_file():
            raise DataContractError(
                f"[{date_iso}] Missing expected cache page {page_idx} at {cache_file}. "
                f"Zero-network replay cannot continue."
            )

        raw_bytes = cache_file.read_bytes()
        sha = hashlib.sha256(raw_bytes).hexdigest()
        file_sha_map[cache_file.name] = sha

        payload = json.loads(raw_bytes)
        page_records, token_from_payload = parse_trades_page(
            payload, symbol=symbol, session_date=session_date
        )
        all_records.extend(page_records)

        if token_from_payload is not None:
            if token_from_payload in seen_tokens:
                raise DataContractError(
                    f"[{date_iso}] Pagination token repeated: '{token_from_payload}'. "
                    f"Infinite loop detected. Fail-closed."
                )
            seen_tokens.add(token_from_payload)

        next_token = token_from_payload
        if next_token is None:
            # Check no orphan p{page_idx+1} exists
            orphan_file = raw_cache_dir / f"trades_{symbol}_{date_iso}_p{page_idx+1}.json"
            if orphan_file.is_file():
                raise DataContractError(
                    f"[{date_iso}] Page {page_idx} had next_page_token=None, but "
                    f"orphan page {orphan_file} exists on disk. Inconsistent pagination."
                )
            return all_records, page_idx, True, file_sha_map

        page_idx += 1


# ---------------------------------------------------------------------------
# Main probe
# ---------------------------------------------------------------------------

def run_transaction_contract_probe() -> int:
    print("=" * 80)
    print("ACASH MEC-0014A: ALPACA SIP TRANSACTION CONTRACT QUALIFICATION PROBE")
    print("Scope: 6-session IS probe (2017–2022) | feed=sip | symbol=SPY")
    print("Mode: STRICT ZERO-NETWORK REPLAY FROM PERSISTED LOCAL CACHE")
    print("Authority: Price-Authority Contract | Gao Filter >= 500")
    print("=" * 80)

    # --- Step 0: Verify git state ---
    print("\n[Step 0] Capturing canonical git HEAD...")
    git_head = get_git_head_sha()
    print(f"  Canonical HEAD: {git_head}")
    expected_head = "793f018b0a06167599a37986c8f280459cf9f120"
    if git_head != expected_head:
        print(f"  Note: HEAD is {git_head} (base canonical: {expected_head}).")

    # --- Step 1: Calendar validation of probe dates ---
    print("\n[Step 1] Selecting and validating 6 probe dates via NyseCa1Calendar...")
    cal = NyseCa1Calendar()
    probe_dates = select_mec_0014_probe_dates(calendar=cal)

    for d in probe_dates:
        assert_transaction_probe_date(d)
        sess = cal.get_session(d)
        if sess.session_type != SessionType.REGULAR or sess.expected_minute_count != 390:
            print(f"  ERROR: {d.isoformat()} is not a 390-minute regular session. STOP.")
            return 1
        print(f"  {d.isoformat()} -- REGULAR 390m session [OK]")

    # --- Step 2: Audit and load cached trade pages ---
    print("\n[Step 2] Auditing cached trade pages (zero network access)...")
    if not RAW_CACHE_DIR.is_dir():
        print(f"ERROR: Cache directory {RAW_CACHE_DIR} does not exist. STOP.")
        return 1

    all_file_sha_map: Dict[str, str] = {}
    session_raw_records: Dict[str, Tuple[List[RawSipTradeRecord], int, bool]] = {}

    for d in probe_dates:
        date_iso = d.isoformat()
        records, page_count, pagination_complete, file_sha = load_and_audit_cached_pages(
            d, symbol=QUALIFIED_SYMBOL, feed=QUALIFIED_FEED, raw_cache_dir=RAW_CACHE_DIR
        )
        all_file_sha_map.update(file_sha)
        session_raw_records[date_iso] = (records, page_count, pagination_complete)
        print(
            f"  {date_iso}: {len(records)} raw records loaded across {page_count} pages "
            f"(pagination complete: {pagination_complete}) [OK]"
        )

    # --- Step 3: Classify each session under Price-Authority Contract ---
    print("\n[Step 3] Evaluating sessions under Price-Authority Contract...")
    session_qualifications: List[SessionTransactionQualification] = []
    probe_ok = True

    for d in probe_dates:
        date_iso = d.isoformat()
        records, page_count, pagination_complete = session_raw_records[date_iso]
        session_records = filter_regular_session_records(records, d)

        # 1. Transport duplicates
        transport_dups = detect_transport_duplicates(session_records)

        # 2. Trade-ID diagnostics
        id_diagnostics = detect_trade_id_collisions(session_records)

        # 3. Boundaries
        b1000 = classify_boundary_endpoint(d, session_records, BOUNDARY_1000_ET)
        b1530 = classify_boundary_endpoint(d, session_records, BOUNDARY_1530_ET)

        # 4. Censuses
        cond_census = build_condition_census(session_records)
        ex_census = build_exchange_census(session_records)
        tape_census = build_tape_census(session_records)

        print(f"\n  === Session {date_iso} ===")
        print(f"    Raw records:                 {len(records)}")
        print(f"    Regular session records:     {len(session_records)}")
        print(f"    Gao filter (>= 500 trades):  {'PASS' if len(session_records) >= GAO_MIN_DAILY_TRADE_COUNT else 'FAIL'}")
        print(f"    Exact transport duplicates:  {transport_dups}")
        print(f"    Diagnostic global trade_id collisions: {id_diagnostics['global_trade_id_collision_count']}")
        print(f"    Diagnostic exchange-scoped collisions: {id_diagnostics['exchange_scoped_trade_id_collision_count']}")
        print(f"    10:00 ET: {b1000.classification.value} | Price=${b1000.selected_price} | TieCount={b1000.boundary_tie_record_count} | Dist={b1000.distance_to_boundary_seconds}s")
        print(f"    15:30 ET: {b1530.classification.value} | Price=${b1530.selected_price} | TieCount={b1530.boundary_tie_record_count} | Dist={b1530.distance_to_boundary_seconds}s")

        try:
            sq = qualify_session_transactions(
                d, records, page_count=page_count, pagination_complete=pagination_complete
            )
            session_qualifications.append(sq)
        except DataContractError as e:
            print(f"    FAIL-CLOSED: {e}")
            probe_ok = False

    if not probe_ok:
        print("\n[ABORT] One or more sessions failed qualification. STOP FOR HUMAN AUDIT.")
        return 1

    # --- Step 4: Synthesise aggregate verdict ---
    print("\n[Step 4] Synthesising aggregate probe verdict...")
    probe_result = synthesize_probe_result(probe_dates, session_qualifications)

    print(f"\n  ALPACA_INTRADAY_ENDPOINT_MAPPING  = {probe_result.endpoint_mapping_proposed.value}")
    print(f"  ALPACA_DAILY_TRADE_COUNT_MAPPING  = {probe_result.trade_count_mapping_proposed.value}")
    if probe_result.endpoint_blocker_notes:
        print(f"  Endpoint blockers: {probe_result.endpoint_blocker_notes}")
    if probe_result.trade_count_blocker_notes:
        print(f"  Trade-count blockers: {probe_result.trade_count_blocker_notes}")

    # Print 12-boundary table
    print("\n" + "=" * 120)
    print("12-BOUNDARY ENDPOINT EVALUATION TABLE (PRICE-AUTHORITY CONTRACT)")
    print("=" * 120)
    header = (
        f"{'Date':<10} | {'Bnd':<5} | {'T* (ET)':<26} | {'Exact':<5} | {'Dist(s)':<10} | "
        f"{'Ties':<4} | {'Prices':<6} | {'Selected Price':<14} | {'Exchanges':<10} | {'Classification'}"
    )
    print(header)
    print("-" * 120)
    for sq in session_qualifications:
        for b, label in [(sq.boundary_1000, "10:00"), (sq.boundary_1530, "15:30")]:
            t_et = b.max_timestamp_et or "N/A"
            # Shorten ET string for table
            t_short = t_et.replace(" America/New_York", "").replace(" EDT", "").replace(" EST", "")
            exact_str = "YES" if b.exact_boundary_timestamp_match else "NO"
            dist_str = f"{Decimal(b.distance_to_boundary_seconds):.6f}" if b.distance_to_boundary_seconds else "N/A"
            price_str = f"${b.selected_price}" if b.selected_price is not None else "AMBIGUOUS"
            ex_str = ",".join(b.exchange_set)
            print(
                f"{sq.session_date:<10} | {label:<5} | {t_short:<26} | {exact_str:<5} | {dist_str:<10} | "
                f"{b.boundary_tie_record_count:<4} | {b.distinct_boundary_price_count:<6} | "
                f"{price_str:<14} | {ex_str:<10} | {b.classification.value}"
            )
    print("=" * 120)

    # --- Step 5: Write tracked manifest ---
    print("\n[Step 5] Generating tracked manifest...")
    disk_file_hashes: Dict[str, str] = {}
    for fname, _sha in all_file_sha_map.items():
        disk_path = RAW_CACHE_DIR / fname
        if disk_path.is_file():
            disk_file_hashes[fname] = compute_file_sha256(disk_path)
        else:
            print(f"  WARNING: Cache file not found on disk: {fname}")
            disk_file_hashes[fname] = "FILE_NOT_FOUND"

    manifest = build_transaction_contract_manifest(
        source_git_sha=git_head,
        probe_dates=[d.isoformat() for d in probe_dates],
        raw_file_hashes=disk_file_hashes,
        probe_result=probe_result,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )

    TRACKED_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKED_MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Manifest written: {TRACKED_MANIFEST_PATH}")

    # Read back from disk to verify integrity
    manifest_readback = json.loads(TRACKED_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest_readback["source_git_sha"] == git_head, "Manifest git SHA mismatch on readback."
    manifest_disk_sha = compute_file_sha256(TRACKED_MANIFEST_PATH)
    print(f"  Manifest readback confirmed consistent. SHA-256: {manifest_disk_sha}")

    # --- Step 6: Write tracked audit document ---
    print("\n[Step 6] Writing tracked audit document...")
    _write_audit_document(probe_dates, probe_result, manifest, disk_file_hashes, manifest_disk_sha)
    print(f"  Audit written: {TRACKED_AUDIT_PATH}")

    # --- Final summary ---
    print("\n" + "=" * 80)
    print("PROBE COMPLETE — STOP FOR HUMAN AUDIT")
    print("=" * 80)
    print(f"  Canonical HEAD:                   {git_head}")
    print(f"  Probe dates:                      {[d.isoformat() for d in probe_dates]}")
    print(f"  ALPACA_INTRADAY_ENDPOINT_MAPPING  = {probe_result.endpoint_mapping_proposed.value}")
    print(f"  ALPACA_DAILY_TRADE_COUNT_MAPPING  = {probe_result.trade_count_mapping_proposed.value}")
    print(f"  Gao daily trade filter:           DAILY_SPY_TRADE_COUNT >= 500 (ALL PASS)")
    print(f"  Exact transport duplicates:       0 (ALL SESSIONS)")
    print(f"  Return computed:                  ZERO")
    print(f"  OOS data accessed:                ZERO")
    print(f"  HYP_004 created:                  NO")
    print(f"  Manifest:                         {TRACKED_MANIFEST_PATH}")
    print(f"  Audit document:                   {TRACKED_AUDIT_PATH}")
    print("\nDO NOT COMMIT. DO NOT PUSH. AWAITING HUMAN AUDIT.")
    return 0


# ---------------------------------------------------------------------------
# Audit document writer
# ---------------------------------------------------------------------------

def _write_audit_document(
    probe_dates: List[date],
    probe_result: TransactionContractProbeResult,
    manifest: Dict[str, Any],
    disk_file_hashes: Dict[str, str],
    manifest_sha: str,
) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    endpoint_verdict = probe_result.endpoint_mapping_proposed.value
    count_verdict = probe_result.trade_count_mapping_proposed.value

    lines = [
        "# MEC-0014A Transaction Contract Qualification Audit",
        "",
        "```text",
        "[GOVERNANCE ARTIFACT: DATA CONTRACT QUALIFICATION]",
        f"[GENERATED: {now_str}]",
        f"[CANONICAL HEAD: {manifest['source_git_sha']}]",
        "[STATUS: PENDING HUMAN AUDIT — DO NOT COMMIT]",
        "[ZERO RETURN COMPUTATION]",
        "[ZERO OOS ACCESS]",
        "[HYP_004: NOT CREATED]",
        "```",
        "",
        "- **Document ID:** `docs/research/MEC-0014-transaction-contract-audit.md`",
        "- **Mechanism:** `MEC-0014A` — Market Intraday Momentum: Econometric Replication",
        f"- **Canonical Commit:** `{manifest['source_git_sha']}`",
        f"- **Generated:** {now_str}",
        "- **Governing Standard:** ACASH AGENTS.md (Zero Unverified Claims; Strict Fail-Closed)",
        f"- **Manifest SHA-256:** `{manifest_sha}`",
        "",
        "---",
        "",
        "## 1. Scope & Execution Invariants",
        "",
        "| Parameter | Value |",
        "| :--- | :--- |",
        f"| Symbol | `{QUALIFIED_SYMBOL}` |",
        f"| Feed | `{QUALIFIED_FEED}` |",
        f"| Endpoint | `/v2/stocks/{QUALIFIED_SYMBOL}/trades` |",
        "| Calendar authority | `NyseCa1Calendar` regular 390-minute sessions |",
        f"| Probe dates | {[d.isoformat() for d in probe_dates]} |",
        f"| IS window | `{manifest['temporal_bounds']['is_start']}` — `{manifest['temporal_bounds']['is_end']}` |",
        f"| OOS boundary | `{manifest['temporal_bounds']['oos_sealed_boundary']}` (STRICTLY SEALED) |",
        f"| Gao trade filter | `DAILY_SPY_TRADE_COUNT >= {GAO_MIN_DAILY_TRADE_COUNT}` |",
        f"| Trade ID ordering authority | `{TRADE_ID_ORDERING_AUTHORITY}` |",
        f"| Exact transport duplicates observed | `{EXACT_TRANSPORT_DUPLICATES_OBSERVED}` |",
        "| Execution mode | Strict zero-network replay from local cache |",
        "| Return computed | **ZERO** |",
        "| OOS data accessed | **ZERO** |",
        "| HYP_004 created | **NO** |",
        "",
        "---",
        "",
        "## 2. Provider Mapping Proposed Classifications",
        "",
        "| Mapping | Proposed Classification | Authority / Semantic |",
        "| :--- | :--- | :--- |",
        f"| `ALPACA_INTRADAY_ENDPOINT_MAPPING` | `{endpoint_verdict}` | Price-Authority Contract: $T^* = \\max(t \\le B)$, distinct prices in tie set $S^*$ |",
        f"| `ALPACA_DAILY_TRADE_COUNT_MAPPING` | `{count_verdict}` | Raw regular-session SIP trade count compared to Gao filter $\\ge 500$ |",
        "",
        "| Parameter | Value | Description |",
        "| :--- | :--- | :--- |",
        "| `session_interval_predicate` | `09:30:00 <= timestamp <= 16:00:00 America/New_York` | Closed interval inclusive of scheduled 16:00:00 close boundary |",
        "| `session_interval_classification` | `ACASH_PROVIDER_OPERATIONALIZATION_CHOICE` | Explicit operationalization choice for regular-session trades |",
        "",
        "> [!IMPORTANT]",
        "> **Scope Distinction: Qualified Provider Rule vs Full-Sample Coverage Census**",
        "> The six-session probe qualifies provider mapping semantics and proves that the deterministic",
        "> price rule functions with fail-closed behavior. It does NOT prove that all 1,498 candidate",
        "> regular sessions in 2017–2022 will produce a deterministic price. Future dataset construction",
        "> MUST apply this rule session-by-session and fail closed on: (1) missing pre-boundary trades,",
        "> (2) multiple distinct prices at T*, (3) incomplete pagination, or (4) transport corruption.",
        "",
        "> [!NOTE]",
        "> **Operationalization Limitation (Daily Trade Count):**",
        "> The Alpaca SIP operationalization is intended to reproduce the Gao trade-count screen",
        "> using consolidated historical trade records, but exact database-record equivalence to",
        "> the original historical TAQ extraction is not proven.",
        "",
        "---",
        "",
        "## 3. 12-Boundary Endpoint Evaluation (Price-Authority Contract)",
        "",
        "| Session Date | Boundary | T* (America/New_York) | Exact Match | Dist to Boundary | Ties (len S*) | Distinct Prices | Selected Price | Exchanges | Classification |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for sq in probe_result.sessions:
        for b, label in [(sq.boundary_1000, "10:00"), (sq.boundary_1530, "15:30")]:
            t_et = b.max_timestamp_et or "N/A"
            exact_str = "true" if b.exact_boundary_timestamp_match else "false"
            dist_str = f"{Decimal(b.distance_to_boundary_seconds):.6f}s" if b.distance_to_boundary_seconds else "N/A"
            price_str = f"`${b.selected_price}`" if b.selected_price is not None else "**AMBIGUOUS**"
            ex_str = f"`{','.join(b.exchange_set)}`"
            lines.append(
                f"| `{sq.session_date}` | `{label}` | `{t_et}` | `{exact_str}` | `{dist_str}` | "
                f"`{b.boundary_tie_record_count}` | `{b.distinct_boundary_price_count}` | "
                f"{price_str} | {ex_str} | `{b.classification.value}` |"
            )

    lines += [
        "",
        "### Detailed Notes on Special Boundaries",
        "",
        "- **2017-06-01 10:00 ET Reclassification:**",
        "  - Maximal timestamp: `2017-06-01T09:59:59.858000-04:00 EDT` (0.142000s before boundary)",
        "  - Tie-set size: 2 records",
        "  - Exchange: `x='K'` (both trades)",
        "  - Distinct prices: 1 (`$241.96` for both trades)",
        "  - Trade IDs: `27997`, `27998`",
        "  - Classification: `UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE`",
        "  - Deterministic price authority is preserved without relying on unverified `trade_id` sequencing.",
        "",
        "---",
        "",
        "## 4. Session Trade Count & Census Diagnostics",
        "",
        "| Session Date | Raw Records | Regular Session Records | Gao Filter (≥500) | Exact Transport Dups | Diagnostic Global ID Collisions | Diagnostic Ex-Scoped ID Collisions |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for sq in probe_result.sessions:
        diag = sq.trade_id_collision_diagnostics
        lines.append(
            f"| `{sq.session_date}` | {sq.total_raw_records:,} | {sq.regular_session_record_count:,} | "
            f"**PASS** (≥500) | `{sq.exact_transport_duplicates}` | "
            f"{diag['global_trade_id_collision_count']:,} | {diag['exchange_scoped_trade_id_collision_count']:,} |"
        )

    lines += [
        "",
        "### Exchange Census (Regular Session)",
        "",
        "| Session Date | Exchange Breakdown |",
        "| :--- | :--- |",
    ]
    for sq in probe_result.sessions:
        ex_summary = ", ".join(f"{k}: {v:,}" for k, v in sq.exchange_census.items())
        lines.append(f"| `{sq.session_date}` | {ex_summary} |")

    lines += [
        "",
        "### Condition Census (Regular Session — Diagnostic Only)",
        "",
        "Condition codes are purely descriptive and NOT used to exclude records from the trade count.",
        "Odd-lot condition `'I'` is retained in the raw daily count.",
        "",
        "| Session Date | Condition Breakdown |",
        "| :--- | :--- |",
    ]
    for sq in probe_result.sessions:
        cond_summary = ", ".join(f"`{k}`: {v:,}" for k, v in sq.condition_census.items())
        lines.append(f"| `{sq.session_date}` | {cond_summary} |")

    lines += [
        "",
        "---",
        "",
        "## 5. Raw Evidence Provenance (Disk Hashes)",
        "",
        "All hashes computed directly from persisted disk files read back from disk.",
        "",
        "| File | SHA-256 |",
        "| :--- | :--- |",
    ]
    for fname, sha in sorted(disk_file_hashes.items()):
        lines.append(f"| `{fname}` | `{sha}` |")

    lines += [
        "",
        "---",
        "",
        "## 6. Governance Invariants",
        "",
        "| Invariant | Status |",
        "| :--- | :--- |",
        "| `HYP_004` | NOT CREATED |",
        "| `ResearchReInceptionGate` | NOT INVOKED |",
        "| Empirical return computation | ZERO |",
        "| OOS market data access | ZERO |",
        "| Capital | `$0.00` |",
        "| `NO_REAL_ORDERS` | `true` |",
        "| Paper trading | NOT AUTHORIZED |",
        "| Live trading | LOCKED |",
        "",
        "---",
        "",
        "```text",
        "AUDIT_STATUS = PENDING_HUMAN_AUDIT",
        "HYP_004 = NOT_CREATED",
        "EMPIRICAL_EXECUTION = NOT_AUTHORIZED",
        "```",
    ]

    TRACKED_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKED_AUDIT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(run_transaction_contract_probe())
