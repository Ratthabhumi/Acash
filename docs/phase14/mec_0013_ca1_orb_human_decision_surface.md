# MEC-0013 & CA-1 — Human Governance Decision Surface & Ratification Record

```text
[RATIFIED HUMAN GOVERNANCE DECISION RECORD]
[HUMAN-RATIFIED: 2026-09-18]
[NON-NORMATIVE RESEARCH RECORD]
[NO EMPIRICAL AUTHORITY]
[NO BACKTEST AUTHORITY]
[MEC-0013 REMAINS ARCHIVED]
```

**Document ID:** `docs/phase14/mec_0013_ca1_orb_human_decision_surface.md`  
**Purpose:** Durable canonical Human Governance Decision Record ratifying Decision Points C1, C2, and C3.  
**Ratification Date:** 2026-09-18  
**Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)  
**Authority:** Human Operator via explicit directive (`AGENTS.md`).  

---

> [!IMPORTANT]
> ### HARD GOVERNANCE BOUNDARIES (PRESERVED & UNCHANGED)
> - **MEC-0013:** Remains **ARCHIVED** / `NOT PROMOTED`.
> - **HYP_003:** **NOT CREATED** (absent repository-wide).
> - **Inception Gate R1:** **NOT STARTED** / `ResearchReInceptionGate` not invoked.
> - **Empirical Backtesting:** **STRICTLY LOCKED**.
> - **Trading Authority:** Paper `NOT AUTHORIZED`, Live `LOCKED`, Capital `$0.00`, `NO_REAL_ORDERS=true`.
> - **Scope:** These ratifications advance data-plane and pre-registration scaffolding only. They do **NOT** grant empirical execution or model backtesting authority.

---

## 1. Decision C1 — Formal Disposition of D13 (1-Minute Consolidated SIP Data)

### Human Ratification:
```text
RATIFIED SELECTION: OPTION B — PARTIAL D13 RECLASSIFICATION
Date:               2026-09-18
Ratifying Authority: Human Operator
```

### Exact Ratified Scope & Meaning:
1. **Retired Blocker Components:**
   - **$0 Historical Access Availability:** Retired by verified empirical evidence. Alpaca Basic accounts support authenticated consolidated SIP access (`feed=sip`, `adjustment=raw`, `timeframe=1Min`).
   - **Multi-Year Depth:** Retired by verified empirical evidence across 9 calendar years (2017, 2020, 2023, 2026), each yielding exactly 390 continuous regular-session 1-minute bars on `SPY`.
   - **SPY 1-Minute SIP Availability:** Verified under documented API contract.
   - **Reproducible Archival Feasibility:** Verified via length-prefixed composite framing digests and canonical bars hashing.
2. **Components Remaining OPEN / Unresolved:**
   - **Point-in-Time Historical Vintage Authority:** Probes do not prove that historical bars retrieved today are permanently immutable across future retrieval dates.
   - **As-Published Market-Data Tape State:** Historical endpoints serve current aggregated database states, not historical as-published tape releases prior to restatements.
   - **Provider Correction & Restatement Semantics:** Untested against late-arriving trade corrections.
3. **Canonical Impact:**
   - D13 in `docs/phase14/mec_0013_orb_readiness_checklist.md` is updated to split status: `PARTIALLY RESOLVED (AVAILABILITY/DEPTH: RETIRED; PIT/VINTAGE: OPEN)`.
   - This is **NOT** full D13 closure. Full closure requires PIT vintage verification.

---

## 2. Decision C2 — Operational Acceptance of Executable CA-1 Calendar Engine

### Human Ratification:
```text
RATIFIED SELECTION: OPTION A — ACCEPT OPERATIONAL IMPLEMENTATION
Date:               2026-09-18
Ratifying Authority: Human Operator
```

### Exact Ratified Scope & Meaning:
1. **Operational Calendar Authority:**
   - The implemented `NyseCa1Calendar` (`src/acash/data/calendar/nyse_ca1.py`) is accepted as the operational executable representation of the already-ratified CA-1 authority for its currently ratified historical coverage.
2. **Coverage Bounds:**
   - Coverage is strictly bounded to **2013-01-01 through 2026-12-31** (14 calendar years).
   - Zero authority is granted or inferred for 2027+.
3. **Operational Invariants Bound to Acceptance:**
   - Derives session dates, holidays, and early closes strictly from pinned CA-1 authority records (15 official NYSE artifacts).
   - Uses native `ZoneInfo("America/New_York")` with zero hard-coded UTC offsets.
   - Avoids generic holiday inference rules.
   - Fails closed (`CalendarAuthorityOutOfRangeError`) for dates outside [2013, 2026].
   - Preserves official 13:00 ET early-close sessions (210 minute bars).
4. **Integration Status:**
   - Integrated into `HistoricalBarValidator` to authorize session completeness checks on covered dates without emitting false `CALENDAR_AUTHORITY_UNVERIFIED` findings.

---

## 3. Decision C3 — Disposition of Price-Only ORB Research Scaffold

### Human Ratification:
```text
RATIFIED SELECTION: OPTION A — ACCEPT SCAFFOLD FOR PRE-REGISTRATION COMPLETION
Date:               2026-09-18
Ratifying Authority: Human Operator
```

### Exact Ratified Scope & Meaning:
1. **Scaffold Standing:**
   - `MEC-0013-PRICE-ONLY-DRAFT` (`docs/phase14/mec_0013_price_only_draft_scaffold.md`) is formally accepted for **PRE-REGISTRATION COMPLETION ONLY**.
2. **Fixed Design Parameters:**
   - Single instrument (`SPY`), 1-minute SIP aggregates, CA-1 session bounds, unadjusted price basis.
   - Bounded primary hypothesis grid of exactly **$K = 4$ cells** (5m/15m $\times$ Long/Short).
   - Complete decoupling from VWAP (D14).
3. **Explicit Non-Authorizing Boundaries:**
   - Does **NOT** promote or revive MEC-0013.
   - Does **NOT** create `HYP_003`.
   - Does **NOT** invoke `ResearchReInceptionGate` (R1).
   - Does **NOT** authorize empirical validation or backtesting.
   - Does **NOT** authorize Paper or Live execution.
4. **Immediate Next Step:**
   - The 14 open parameters identified in Section 4 of the scaffold remain open and shall be frozen in a subsequent dedicated Pre-Registration Specification step prior to any empirical authorization.

---

### Verification Ledger
- Implementation Status: COMPLETE (Human Governance Decisions C1, C2, C3 formally ratified and recorded)
- Contract Enforcement: STRICT FAIL-CLOSED (Split D13 status, bounded CA-1 coverage, non-authorizing scaffold acceptance)
- Mathematical Authority: HUMAN GOVERNANCE RATIFICATION (2026-09-18)
- Local Test Suite: VERIFIED (42 passed focused, 2460 passed full suite)
- Type Checker (MyPy): VERIFIED (439 source files clean)
- Remote CI Status: NOT APPLICABLE
