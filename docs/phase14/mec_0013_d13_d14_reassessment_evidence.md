# MEC-0013 — D13 & D14 Reassessment Evidence Synthesis

```text
[NON-NORMATIVE]
[EVIDENCE SYNTHESIS]
[NO GOVERNANCE AUTHORITY]
[NO EMPIRICAL AUTHORIZATION]
[MEC-0013 REMAINS ARCHIVED]
```

**Document ID:** `docs/phase14/mec_0013_d13_d14_reassessment_evidence.md`
**Object:** Technical and cryptographic evidence synthesis across 4 historical SIP probe packages (2017, 2020, 2023, 2026) for Human governance review of MEC-0013 checklist items D13 and D14.
**Date:** 2026-09-18
**Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
**Authority:** Strict Fail-Closed (`AGENTS.md`). This document possesses **zero** sovereign governance authority and confers **zero** strategy qualification, **zero** backtesting permission, **zero** empirical admission, and **zero** capital authority. Canonical governance files remain unmutated.

---

## 1. Executive Summary & Purpose

This synthesis compiles empirical verification findings from four single-session historical SIP qualification probes conducted against Alpaca's historical market data endpoint using a `$0` Basic account under the documented API contract (`feed=sip`, `adjustment=raw`, `timeframe=1Min`, `asof=YYYY-MM-DD`).

The objective is to establish an unassailable factual basis for Human review regarding:
1. **D13 (1-Minute Consolidated SIP Data)**: Evaluating whether the prior availability and multi-year depth blocker rationale (*"NO source at $0 provides multi-year, point-in-time consolidated 1m data"*) remains factually accurate, while explicitly decoupling availability/depth from unresolved point-in-time (PIT) / historical vintage immutability questions.
2. **D14 (Point-in-Time VWAP Authority)**: Evaluating the presence and integrity of provider-supplied minute-bar VWAP values under `feed=sip`, while distinguishing observed provider outputs from independent trade reconstruction and historical restatement behavior.

---

## 2. Multi-Package Cryptographic Verification Table

All four evidence packages reside in `var/data/qualification/` and were independently audited using the canonical `verify_persisted_evidence_package` helper. Every package achieved 100% cryptographic integrity with zero errors, zero secret leakage, and strictly zero quality rule violations.

| Metric / Attribute | 2017 Session | 2020 Session | 2023 Session | 2026 Session |
| :--- | :--- | :--- | :--- | :--- |
| **Target Date** | `2017-09-15` | `2020-09-15` | `2023-09-15` | `2026-09-15` |
| **Manifest ID** | `SIP-QUAL-SPY-ac03e51c` | `SIP-QUAL-SPY-c924ae70` | `SIP-QUAL-SPY-19647058` | `SIP-QUAL-SPY-280f1628` |
| **Symbol / Timeframe** | `SPY` / `1Min` | `SPY` / `1Min` | `SPY` / `1Min` | `SPY` / `1Min` |
| **Requested Feed / Adjust** | `sip` / `raw` | `sip` / `raw` | `sip` / `raw` | `sip` / `raw` |
| **Symbol As-Of Context** | `2017-09-15` | `2020-09-15` | `2023-09-15` | `2026-09-15` |
| **Page Count** | 1 | 1 | 1 | 1 |
| **Raw Byte Length** | 42,097 bytes | 42,293 bytes | 42,740 bytes | 42,259 bytes |
| **Raw Page SHA-256** | `d2bb386966...` | `43ffb4159f...` | `58b34c0bf3...` | `89c46c484f...` |
| **Composite Framed SHA-256** | `6c6dbc7c8e...` | `d95cce6ced...` | `e1c2b304fb...` | `5b03043ec7...` |
| **Canonical Bars SHA-256** | `7471db34e6...` | `088edd3da1...` | `fb549ce90c...` | `dc6e038be2...` |
| **Package Integrity Status** | **VALID (0 errors)** | **VALID (0 errors)** | **VALID (0 errors)** | **VALID (0 errors)** |
| **Secret Leakage Scan** | **PASS (clean)** | **PASS (clean)** | **PASS (clean)** | **PASS (clean)** |
| **Record Count** | **390** | **390** | **390** | **390** |
| **First Timestamp (UTC)** | `2017-09-15T13:30:00Z` | `2020-09-15T13:30:00Z` | `2023-09-15T13:30:00Z` | `2026-09-15T13:30:00Z` |
| **Last Timestamp (UTC)** | `2017-09-15T19:59:00Z` | `2020-09-15T19:59:00Z` | `2023-09-15T19:59:00Z` | `2026-09-15T19:59:00Z` |
| **Provider VWAP (`vw`)** | 390 present / 0 missing | 390 present / 0 missing | 390 present / 0 missing | 390 present / 0 missing |
| **Trade Count (`n`)** | 390 present / 0 missing | 390 present / 0 missing | 390 present / 0 missing | 390 present / 0 missing |
| **Duplicate / Monotonicity** | 0 findings | 0 findings | 0 findings | 0 findings |
| **OHLC Bounds Violations** | 0 findings | 0 findings | 0 findings | 0 findings |
| **Volume Violations** | 0 findings | 0 findings | 0 findings | 0 findings |
| **OUTSIDE_REGULAR_HOURS** | **0 findings** | **0 findings** | **0 findings** | **0 findings** |
| **Request Contract Status** | `PASS` | `PASS` | `PASS` | `PASS` |
| **Network Access Status** | `PASS` | `PASS` | `PASS` | `PASS` |
| **Data Integrity Status** | `PASS` | `PASS` | `PASS` | `PASS` |
| **Provider Provenance** | `PASS` | `PASS` | `PASS` | `PASS` |
| **Provenance Basis** | `DOCUMENTED_API_CONTRACT` | `DOCUMENTED_API_CONTRACT` | `DOCUMENTED_API_CONTRACT` | `DOCUMENTED_API_CONTRACT` |
| **Feed Provenance (Header)** | `UNVERIFIED` | `UNVERIFIED` | `UNVERIFIED` | `UNVERIFIED` |
| **Source Qualification Status** | `DATA_SOURCE_TECHNICALLY_QUALIFIED` | `DATA_SOURCE_TECHNICALLY_QUALIFIED` | `DATA_SOURCE_TECHNICALLY_QUALIFIED` | `DATA_SOURCE_TECHNICALLY_QUALIFIED` |
| **VWAP Authority Status** | `QUALIFIED` | `QUALIFIED` | `QUALIFIED` | `QUALIFIED` |
| **Git Commit SHA** | `d77d38d41f...` | `d77d38d41f...` | `d77d38d41f...` | `d77d38d41f...` |
| **Git Dirty State** | `True` (untracked memo) | `True` (untracked memo) | `True` (untracked memo) | `True` (untracked memo) |

---

## 3. Multi-Year Depth Facts

Factual, mathematical properties established by these four probes:

1. **Earliest Verified Date:** `2017-09-15` (13:30:00Z to 19:59:00Z).
2. **Latest Verified Date:** `2026-09-15` (13:30:00Z to 19:59:00Z).
3. **Temporal Span:** Exactly **9.00 years** (3,287 calendar days).
4. **Sample Structure:** 4 discrete spot-check sessions separated by 3-year intervals (2017, 2020, 2023, 2026).
5. **Regular Session Completeness:** In all four sessions, **exactly 390 1-minute bars** were returned, spanning `09:30:00 ET` through `15:59:00 ET` continuously with zero missing bars and zero out-of-hours bars.
6. **Data Plane Uniformity:** All 4 sessions feature complete OHLCV, integer trade counts (`n`), and floating-point volume-weighted average prices (`vw`) on every single minute bar without exception (1,560 / 1,560 total bars populated).
7. **Zero Account Cost:** All retrievals were performed against a live, standard `$0` Basic account tier using the public Alpaca historical market data API.

---

## 4. D13 Evidence Assessment (1-Minute Consolidated SIP Data)

### Current Canonical Wording in Checklist
```text
Check 13: 1-Minute Consolidated SIP Data
Status:   BLOCKED
Finding:  NO source at $0 provides multi-year, point-in-time consolidated 1m data.
          Free feeds are truncated or IEX-only.
```

### Observed Technical Evidence vs. Point-in-Time Scope

To ensure rigorous governance compliance without overclaiming, the technical findings are explicitly partitioned:

#### A. PROVEN: Availability, Multi-Year Depth, and Ingestion Feasibility
1. **$0 Access**: Access to historical market data using `feed=sip` succeeded on a standard Basic tier account without paid subscription.
2. **Multi-Year Depth**: Spot checks span 2017 through 2026 (9 years), confirming coverage well beyond truncated 30-day or 1-year windows.
3. **Continuous 1-Minute Grid**: All sessions returned full 390 regular-session minute bars (`09:30:00` to `15:59:00 ET`) under normalized UTC boundaries.
4. **SIP Contract Basis**: Queries explicitly requested `feed=sip` under documented API semantics representing all US exchanges.
5. **Reproducible Raw Archive**: Exact HTTP payloads and per-page / framed composite digests are archived and cryptographically verifiable.

#### B. NOT YET PROVEN: Point-in-Time Immutability and Historical Vintage Semantics
1. **Immutable Vintage**: Current evidence does not independently prove that historical bar values retrieved today are immutable across future retrieval dates.
2. **As-Published Market-Data State**: The historical endpoint serves consolidated bars as currently aggregated in the provider's database; it does not explicitly track or reproduce earlier as-published data vintages prior to post-hoc trade cancellations or tape corrections.
3. **`asof` Parameter Scope**: In Alpaca's API, `asof` serves as symbol identity / mapping context (resolving ticker renames, mergers, or delistings as of that date). It is **not** documented or proven to enforce a point-in-time market-data release vintage.

### Non-Normative Conclusion for Human Review
> **Suggested Human-Review Finding:**
>
> The prior D13 availability/depth rationale is no longer supported for SPY historical 1-minute SIP access at $0. Verified evidence spans 2017-09-15 through 2026-09-15 across four distinct years with complete 390-bar regular-session samples and reproducible archived evidence.
>
> However, the remaining D13 authority question is point-in-time/vintage semantics: the current evidence does not independently prove that historical bars are immutable across provider retrieval dates or that the served dataset preserves an as-published market-data vintage.

---

## 5. D14 Evidence Assessment (Point-in-Time VWAP Authority)

### Current Canonical Wording in Checklist
```text
Check 14: Point-in-Time VWAP Authority
Status:   BLOCKED
Finding:  Free feeds lack consolidated market-wide volume, producing distorted intraday VWAP values.
```

### Observed Technical Evidence
1. **Provider Field Presence**: Alpaca returned a provider `vw` field on every verified 1-minute bar retrieved under the documented `feed=sip` contract (1,560 / 1,560 bars populated).
2. **Mathematical Consistency**: In all 1,560 bars, `Low <= vw <= High` strictly holds.
3. **Bucket Semantics**: Provider VWAP represents the volume-weighted average price within each discrete 1-minute interval ($\frac{\sum P \cdot V}{\sum V}$), not cumulative session-to-date VWAP.

### Boundary Limitations & Unresolved Authority Questions
1. **Zero Independent Trade Reconstruction**: The evidence does not independently reconstruct VWAP from underlying constituent trades and therefore does not by itself prove exact calculation lineage, correction policy, or historical vintage immutability.
2. **Tape Correction Policy**: It is unknown whether late-reported trades, trade breaks, or As-Of tape adjustments cause retroactive mutations to historical minute-bar VWAP.
3. **Constituent Cross Inclusion**: The handling of closing auction crosses coincident with the 16:00 ET timestamp and their interaction with the final continuous minute bars has not been audited at the tick level.

### Non-Normative Conclusion for Human Review
> **Suggested Human-Review Finding:**
> D14 has materially improved technical evidence: Alpaca returned a provider `vw` field on every verified 1-minute bar retrieved under the documented `feed=sip` contract, eliminating the prior blocker premise that free feeds strictly lack consolidated volume. However, the evidence does not independently reconstruct VWAP from underlying constituent trades and therefore does not by itself prove exact calculation lineage, correction policy, or historical vintage immutability. D14 remains **authority-conditional** pending explicit Human policy on whether provider-aggregated bucket VWAP satisfies frozen quantitative research requirements.

---

## 6. Human Decision Options (For Future Governance Ratification)

The Human Operator may evaluate these options during a formal governance session:

### OPTION 1 — STATUS QUO
- Maintain both D13 and D14 as `BLOCKED`.
- Keep MEC-0013 archived and dormant.
- Rationale: Prefer to leave all data-plane items blocked until a comprehensive point-in-time and calendar authority architecture is formally specified and verified.

### OPTION 2 — PARTIAL D13 RECLASSIFICATION (Recommended Review Stance)
- Human acknowledges that the prior D13 $0 availability and multi-year depth blocker is retired.
- D13 point-in-time / vintage immutability authority remains explicitly open.
- D14 remains authority-conditional pending determination on provider bucket VWAP versus tick-reconstructed cumulative VWAP.
- MEC-0013 remains `ARCHIVED` and `NOT READY FOR EMPIRICAL BACKTESTING`.
- All operational and governance locks (`HYP_003` absent, Gate R1 uninvoked, capital at $0.00, `NO_REAL_ORDERS=true`) remain preserved.

### OPTION 3 — REQUIRE ADDITIONAL PIT / VINTAGE AUTHORITY WORK
- Keep formal D13/D14 closure pending explicit empirical evidence regarding historical correction/restatement behavior (e.g. repeated retrieval over time to test vintage immutability).
- Defer any checklist modification until repeat-probe vintage stability is demonstrated.

---

## 7. Mandatory Governance Confirmation

As of this document's creation:
- **MEC-0013 Status:** `ARCHIVED` (not promoted).
- **D13 & D14 Status in Canonical Files:** `BLOCKED` (unmodified).
- **Hypothesis Registry:** `HYP_003` does **NOT** exist.
- **Research Gates:** Inception Gate `R1` has **NOT** been invoked.
- **Backtesting & Simulation:** `LOCKED`.
- **Trading Capital:** `$0.00` (Strictly `NO_REAL_ORDERS=true`).
