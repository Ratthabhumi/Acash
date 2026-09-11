# MEC-0013 — Pre-Registration & Research-Readiness Checklist

**Document ID:** `docs/phase14/mec_0013_orb_readiness_checklist.md`  
**Object:** 20-Point Multi-Dimensional Pre-Registration and Empirical Readiness Audit for MEC-0013 (Opening Range Breakout).  
**Status:** `[RESEARCH READINESS AUDIT]` `[NON-NORMATIVE]` `[NO IMPLEMENTATION AUTHORITY]` `[NOT HYP_003]`  
**Date:** 2026-09-11  
**Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)  
**Authority:** `AGENTS.md` (Strict Fail-Closed, Implementation Correctness != Mathematical Validity).

---

## 1. 20-Point Governance & Pre-Registration Checklist

| Check # | Audit Dimension | Status | Verified Evidence / Governance Finding |
|---|---|---|---|
| **01** | **Mechanism Formalization** | `RESOLVED` | Fully formalized as deterministic boundary conditions in `mec_0013_orb_research_audit.md` Section 6. Qualitative chart lore eliminated. |
| **02** | **Literature Precedent** | `RESOLVED` | Historical roots (Crabel 1990) and modern decay (Holmberg et al. 2013, Ni et al. 2015, SSRN 0DTE options hedging 2024–2026) audited. |
| **03** | **Measurable Signal Definition** | `RESOLVED` | Explicit formulas for `OR_high`, `OR_low`, `OR_width_pct`, `FIRST_BREAK_UP`, `FIRST_BREAK_DOWN`, and `VWAP_State`. |
| **04** | **Instrument & Asset Class** | `RESOLVED` | Bounded strictly to US Cash Equities / Index ETFs (`SPY`, `QQQ`). Futures/FX/Crypto excluded. |
| **05** | **Session & Calendar Authority** | `RESOLVED` | Bound to NYSE RTH (09:30:00–16:00:00 ET) normalized to UTC under CA-1 session authority. Pre/post-market excluded. |
| **06** | **Opening Print Ambiguity** | `PARTIALLY RESOLVED` | Formal requirement established: bar open must explicitly declare consolidated auction price vs. first continuous trade. |
| **07** | **Cost Model Architecture** | `RESOLVED` | Minimum institutional friction defined: 1.0–1.6 bps roundtrip hurdle on SPY (spread expansion + slippage + regulatory fees). |
| **08** | **Single vs. Repeated Breaks** | `RESOLVED` | Primary test scope restricted strictly to `FIRST_BREAK` to prevent serial dependent auto-correlation. |
| **09** | **Full Search Space Mapped** | `RESOLVED` | Complete 7-parameter space enumerated ($K = 5,184$ combinations). Multiple-testing penalty quantified. |
| **10** | **Anti-HARKing Grid Constraint** | `PROVISIONAL` | Mandate established that any future pre-registration must freeze $K \le 6$ hypothesis cells derived ex-ante. |
| **11** | **Survivorship Controls** | `RESOLVED (CONDITIONAL)` | SPY single-instrument testing is immune to constituent survivorship; dynamic equity universes remain blocked. |
| **12** | **Corporate Action Treatment** | `RESOLVED` | Intraday boundaries require unadjusted price levels on trade day; forward returns account for cash distributions. |
| **13** | **1-Minute Consolidated SIP Data** | `BLOCKED` | **NO source at $0 provides multi-year, point-in-time consolidated 1m data.** Free feeds are truncated or IEX-only. |
| **14** | **Point-in-Time VWAP Authority** | `BLOCKED` | Free feeds lack consolidated market-wide volume, producing distorted intraday VWAP values. |
| **15** | **Quarantine Data Protection** | `RESOLVED` | Isolated from quarantined HYP_001 (2026 M5 Holdout) and HYP_002 (H4 Validation/OOS partitions). |
| **16** | **MACRO-001 Independence** | `RESOLVED` | Completely decoupled from MACRO-001 mainline and parked D17 SPX close authority. |
| **17** | **Candidate Formal Promotion** | `HUMAN DECISION REQUIRED` | MEC-0013 is not promoted to an approved research candidate in `free_data_research_registry.md`. |
| **18** | **HYP_003 Creation** | `LOCKED` | `HYP_003` is ABSENT repository-wide. |
| **19** | **Inception Gate R1** | `LOCKED` | `ResearchReInceptionGate` is NOT INVOKED. |
| **20** | **Empirical Backtest Authority** | `STRICTLY NOT AUTHORIZED` | Empirical execution, return simulation, and parameter tuning remain hard-locked. |

---

## 2. Summary Status

- **Theoretical & Microstructural Specifications:** **12/12 RESOLVED**
- **Data-Plane Authority at $0:** **0/2 RESOLVED (CRITICAL DATA BLOCKER)**
- **Governance & Candidate Standing:** **0/6 AUTHORIZED (STRICTLY LOCKED)**
- **Overall Disposition:** **NOT READY FOR EMPIRICAL BACKTESTING (DATA & GOVERNANCE BLOCKED)**

---

## 3. Human Decision Surface for MEC-0013

If Human Governance wishes to progress MEC-0013 in the future, the following decision surface governs:

```text
Decision ID:        MEC-0013-D01
Question:           How shall ACASH resolve the intraday 1-minute data authority blocker for MEC-0013?
Why Uninferable:    Requires budget authorization ($0 vs paid) or scope truncation (<30 days vs multi-year).

Option A:           Procure commercial consolidated 1-minute historical intraday dataset
                    (e.g. FirstRate Data, Databento, Polygon, Tick Data).
                    Consequence: Solves data authority cleanly; requires commercial budget.

Option B:           Truncate research to recent rolling sample using free API (e.g. 30-day Yahoo 1m).
                    Consequence: $0 cost; severely under-powered sample ($N < 25$ days);
                    fails ACASH statistical power standards.

Option C (Recom.):  Maintain MEC-0013 as an archived, formal, complete theoretical mechanism intake.
                    Do NOT promote to candidate; do NOT allocate capital; keep backtest LOCKED.
                    Focus data procurement / authority efforts on the mainline MACRO-001 track.
```

---

### Verification Ledger
- Implementation Status: COMPLETE (Documentation-only readiness checklist)
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: CANONICAL SPEC / AGENTS.md
- Local Test Suite / MyPy: NOT RUN (Documentation-only artifact)
- Remote CI Status: NOT APPLICABLE
