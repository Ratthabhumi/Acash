# ACASH Phase 14 — MEC-0013 Session Handoff

```text
[WORKING CONTEXT]
[NO DIRECT GOVERNANCE AUTHORITY]
[MEC-0013 REMAINS ARCHIVED]
```

**Document ID:** `docs/phase14/session_handoff_mec_0013.md`
**Purpose:** Durable working-context handoff documenting MEC-0013 D13/D14 historical SIP qualification progress, verified evidence, probe boundary corrections, and recommended Human governance decision points.
**Target Audience:** Human Operator & AI Assistants resuming work across environments (e.g. Workstation to Home machine).
**Date:** 2026-09-18
**Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
**Authority:** Strict Fail-Closed (`AGENTS.md`). This document is a operational transfer log. It does **NOT** possess sovereign authority and does **NOT** alter canonical governance records.

---

## 1. Repository State

- **Repository:** `Ratthabhumi/Acash`
- **Active Branch:** `main`
- **Canonical Base HEAD:** `d77d38d41fb046510b07454ece8c494b4103cda7`
- **Pending Staged Work:**
  - `docs/phase14/mec_0013_d13_d14_reassessment_evidence.md` (non-normative evidence synthesis)
  - `docs/phase14/session_handoff_mec_0013.md` (this durable handoff record)
- **Unrelated Worktree Item:** `docs/research/RESEARCH-INTAKE-MARKET-STRUCTURE-001.md` remains untracked and excluded from all commits.

---

## 2. Hard Governance State (Strictly Preserved)

All repository-wide invariants and governance locks remain active and unchanged:

- **MEC-0013:** `ARCHIVED` / NOT PROMOTED.
- **HYP_003:** `NOT CREATED` (absent repository-wide).
- **Inception Gate R1:** `NOT STARTED` / NOT INVOKED.
- **Backtesting & Simulation Engine:** `LOCKED`.
- **Empirical Research & Strategy Validation:** `STRICTLY NOT AUTHORIZED`.
- **Paper Trading Execution:** `NOT AUTHORIZED`.
- **Live Trading Execution:** `LOCKED`.
- **Canonical Allocated Capital:** `$0.00`.
- **Order Safety Boundary:** `NO_REAL_ORDERS=true`.
- **D13 Canonical Status:** Currently remains `BLOCKED` in `docs/phase14/mec_0013_orb_readiness_checklist.md`.
- **D14 Canonical Status:** Currently remains `BLOCKED` in `docs/phase14/mec_0013_orb_readiness_checklist.md`.

> **Fundamental Principle:**
> Implementation correctness $\neq$ Mathematical validity $\neq$ Governance authorization. Technical evidence reassessment does **NOT** itself modify canonical governance.

---

## 3. Historical SIP Qualification Foundation

Three core implementation commits are established on `main`:

1. `81d3c08c653954d3233de3a58b5e840920db289a`
   `feat(data): add historical SIP qualification foundation`
2. `a61f5fb937a3143c4ea3f90a119e38af7286b149`
   `feat(data): persist SIP qualification evidence`
3. `d77d38d41fb046510b07454ece8c494b4103cda7`
   `fix(data): exclude session-close minute from SIP probe`

### Summary of Implemented Capabilities
- **Request Contract:** Strict enforcement of `feed=sip`, `timeframe=1Min`, `adjustment=raw`, with explicit RFC3339 start/end timestamps.
- **15-Minute Access Guard:** `FifteenMinuteAccessGuard` fails closed if requested `end >= now - 15m` to guarantee safe unsubscribed access under the Alpaca Basic contract.
- **Fail-Closed Auth:** Explicit handling of HTTP 401 (`AlpacaAuthenticationError`) and 403 (`AlpacaAccessDeniedError`).
- **Resilience:** Bounded 429 retry logic honoring `Retry-After` headers.
- **Deterministic Pagination:** Maximum-page boundaries and token verification.
- **Cryptographic Evidence Archiving:**
  - Persists exact raw response bytes without re-serialization.
  - Computes standard per-page SHA-256 digests.
  - Computes length-prefixed composite framed SHA-256 (`>Q` prefix) to eliminate concatenation ambiguity.
  - Computes deterministic canonical bars SHA-256 digest.
- **Epistemic Provenance Separation:** Explicitly distinguishes `DOCUMENTED_API_CONTRACT` from provider response header echo (`UNVERIFIED`).
- **Session Boundaries:** Enforces standard regular trading hours model `[09:30:00, 16:00:00) America/New_York` using native `ZoneInfo` without hard-coded UTC offsets.
- **Calendar Discipline:** Emits `CALENDAR_AUTHORITY_UNVERIFIED` without fabricating missing data or assuming holidays when certified CA-1 schedules are absent.
- **Dry-Run Default:** CLI probe defaults to dry-run mode (`--execute-network` required for live sockets).

---

## 4. Verified Real Alpaca SIP Evidence

Four discrete single-session qualification probes have been executed against live Alpaca infrastructure and cryptographically verified:

1. **2017 Session:**
   - Date: `2017-09-15`
   - Manifest ID: `SIP-QUAL-SPY-ac03e51c`
2. **2020 Session:**
   - Date: `2020-09-15`
   - Manifest ID: `SIP-QUAL-SPY-c924ae70`
3. **2023 Session:**
   - Date: `2023-09-15`
   - Manifest ID: `SIP-QUAL-SPY-19647058`
4. **2026 Session:**
   - Date: `2026-09-15`
   - Manifest ID: `SIP-QUAL-SPY-280f1628`

### Uniform Verification Results Across All Four Packages
- **Symbol:** `SPY`
- **Feed Requested:** `sip`
- **Timeframe:** `1Min`
- **Adjustment:** `raw`
- **Bar Count Returned:** **Exactly 390 bars**
- **First Bar:** `13:30:00Z` (09:30:00 ET)
- **Last Bar:** `19:59:00Z` (15:59:00 ET)
- **Request Contract Status:** `PASS`
- **Network Access Status:** `PASS`
- **Data Integrity Status:** `PASS`
- **Provider Provenance:** `PASS` (`DOCUMENTED_API_CONTRACT`)
- **Feed Response Provenance:** `UNVERIFIED` (Alpaca headers do not echo feed)
- **Source Qualification Status:** `DATA_SOURCE_TECHNICALLY_QUALIFIED`
- **VWAP Authority Status:** `QUALIFIED`
- **Provider VWAP (`vw`):** Present on all 390 bars (0 missing)
- **Trade Count (`n`):** Present on all 390 bars (0 missing)
- **Duplicate / Monotonicity Findings:** `0`
- **OHLC Bounds Violations:** `0`
- **Volume Violations:** `0`
- **OUTSIDE_REGULAR_HOURS:** `0`
- **Cryptographic Readback Integrity:** `is_valid: True` (0 errors across all digests)

### Aggregate Empirical Facts
- **Verified Years:** 4 distinct years (`2017`, `2020`, `2023`, `2026`).
- **Historical Span:** **9.00 years** (3,287 calendar days).
- **Total Verified Bars:** 1,560 continuous regular-session 1-minute bars.
- *Boundary Statement:* These four sessions represent spot-check verification across a 9-year span; they do not imply that all intermediate dates have been queried or ingested.

---

## 5. Important Probe Boundary Finding

During initial testing on `2026-09-15`, an initial probe requested `end=20:00:00Z` (`16:00:00 ET`) and returned **391 bars**.

- **Root Cause:** Alpaca's API treats query parameter `end` as **inclusive** on the bar interval's left timestamp `[T, T + 1m)`.
- **The 391st Bar:** Timestamped `2026-09-15T20:00:00Z` (`16:00 ET`), covering `[16:00, 16:01)`. It recorded 1,749,372 shares coincident with the NYSE official closing auction timestamp.
- **Correction Applied (`d77d38d`):** Preserved the conceptual RTH session as `[09:30:00, 16:00:00) America/New_York` while adapting outbound provider queries to end at `15:59:59 ET` (`19:59:59Z` EDT / `20:59:59Z` EST) via `RthSessionBounds.get_rth_query_interval(session_date)`. This successfully yielded exactly the 390 continuous minute buckets with zero `OUTSIDE_REGULAR_HOURS` warnings.

---

## 6. D13 Current Evidence Interpretation

### What Is Proven
- `$0` historical access using `feed=sip` works operationally on Alpaca Basic accounts.
- Multi-year depth exists across tested samples spanning 9 years (2017–2026).
- 1-minute bars are completely populated (390/session).
- SIP request contract is verified under documented API semantics representing all US exchanges.
- Raw payloads and digests can be sealed and verified reproducibly.

### What Is Not Yet Proven
- **Historical Vintage Immutability:** Current probes do not prove that historical bar values retrieved today remain permanently unchanged across future retrieval dates.
- **As-Published Market-Data State:** The historical endpoint serves consolidated bars as aggregated in the provider's database today; it does not reproduce an earlier as-published tape state prior to trade cancellations.
- **`asof` Parameter Semantics:** In Alpaca, `asof` serves as symbol identity / mapping context (ticker renames/delistings), not as a release-vintage time-freeze mechanism.

### Suggested Human Review Stance
> **D13 availability and multi-year depth blocker appears retired by evidence, but point-in-time / vintage authority remains open.**
> Canonical D13 status remains `BLOCKED` until explicit Human ratification.

---

## 7. D14 Current Evidence Interpretation

### Observed Facts
- Alpaca returned a provider `vw` field on every verified 1-minute bar retrieved under the documented `feed=sip` contract (1,560 / 1,560 bars populated, `Low <= vw <= High`).

### Unresolved Authority Questions
- **Zero Independent Trade Reconstruction:** VWAP has not been reconstructed from underlying tick-level trades.
- **Restatement / Correction Policy:** Behavior regarding late-reported tape corrections is unknown.
- **Bucket vs. Cumulative Session VWAP:** Provider VWAP represents discrete 1-minute volume-weighted prices ($\frac{\sum P \cdot V}{\sum V}$), not cumulative session-to-date VWAP.

### Suggested Human Review Stance
> **D14 has materially improved evidence but remains authority-conditional pending explicit Human decision on provider VWAP and vintage semantics.**
> Canonical D14 status remains `BLOCKED` until explicit Human ratification.

---

## 8. New Non-Normative Reassessment Memo

Detailed technical data and analysis are recorded in:
[`docs/phase14/mec_0013_d13_d14_reassessment_evidence.md`](file:///C:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/phase14/mec_0013_d13_d14_reassessment_evidence.md)

Document Classifications:
- `[NON-NORMATIVE]`
- `[EVIDENCE SYNTHESIS]`
- `[NO GOVERNANCE AUTHORITY]`
- `[NO EMPIRICAL AUTHORIZATION]`
- `[MEC-0013 REMAINS ARCHIVED]`

Documented Decision Options for Human Governance:
- **OPTION 1 — STATUS QUO:** Maintain both D13 and D14 as `BLOCKED`. Keep MEC-0013 archived.
- **OPTION 2 — PARTIAL D13 RECLASSIFICATION (Recommended):** Acknowledge $0 availability/depth blocker retired; keep D13 PIT/vintage authority open; keep D14 authority-conditional; keep MEC-0013 archived and backtesting locked.
- **OPTION 3 — REQUIRE ADDITIONAL PIT/VINTAGE AUTHORITY WORK:** Defer checklist modification pending repeat-probe vintage immutability testing.

---

## 9. Credentials & Local Evidence Safety

- **Credentials Policy:** Alpaca API credentials are **NEVER** committed to this repository. They are supplied strictly via external environment variables (`ACASH_ALPACA_API_KEY_ID`, `ACASH_ALPACA_API_SECRET`).
- **Local Artifacts:** Real probe packages reside locally under:
  ```text
  var/data/qualification/
    SIP-QUAL-SPY-ac03e51c/
    SIP-QUAL-SPY-c924ae70/
    SIP-QUAL-SPY-19647058/
    SIP-QUAL-SPY-280f1628/
    SIP-QUAL-SPY-c0c7f658/
  ```
- **Git-Ignore Boundary:** `var/` is git-ignored and must **NEVER** be committed.
- **Cross-Machine Note:** These raw JSON files exist only on the workstation where probes were executed. When pulling from another machine (e.g. Home machine), do **not** assume raw files are present, and do **not** fabricate mock artifacts. The committed hashes and memos serve as the canonical audit trail.

---

## 10. Known Untracked File

The following unrelated research file exists in the local workspace:
```text
docs/research/RESEARCH-INTAKE-MARKET-STRUCTURE-001.md
```
It is outside the scope of Phase 14 / MEC-0013. It must remain untouched and **MUST NOT** be staged or committed.

---

## 11. Recommended Next Steps

The next milestone is **HUMAN GOVERNANCE REVIEW**, not backtesting or model execution.

1. **Human Decision Surface:**
   - Determine whether to ratify Option 2 (retire availability/depth blocker while keeping PIT/vintage authority open).
   - If ratified, record a formal Human decision record amending `mec_0013_orb_readiness_checklist.md`.
2. **If Stronger PIT Evidence Is Required:**
   - Formulate a repeat-retrieval test protocol to compare historical bars over time for vintage stability.
3. **Hard Restrictions (DO NOT):**
   - Do NOT backtest ORB.
   - Do NOT create `HYP_003`.
   - Do NOT start Inception Gate `R1`.
   - Do NOT promote MEC-0013 to the candidate registry.
   - Do NOT authorize Paper or Live trading.

---

## 12. Resume Checklist From Home Machine

When continuing work from the home machine:

```bash
# 1. Pull latest canonical main
git checkout main
git pull origin main

# 2. Verify HEAD matches origin/main
git rev-parse HEAD
git rev-parse origin/main
git status -sb

# 3. Read context files in sequence:
#    - docs/phase14/session_handoff_mec_0013.md (this file)
#    - docs/phase14/mec_0013_d13_d14_reassessment_evidence.md
#    - docs/phase14/mec_0013_orb_readiness_checklist.md
#    - docs/phase14/mec_0013_orb_research_audit.md
#    - docs/ROADMAP.md

# 4. Verify governance state remains locked:
#    - MEC-0013 is ARCHIVED
#    - Capital is $0.00
#    - Backtesting is LOCKED

# 5. Proceed with Human Governance Review.
```
