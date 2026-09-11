# CAND-FREE-MACRO-001 — Anti-HARKing Audit Checklist & Draft Freeze Governance Template

**Document ID:** `docs/phase14/macro_001_anti_harking_audit_template.md`  
**Classification:** `[DOCUMENTATION-ONLY]` · `[NON-EMPIRICAL]` · `[AUDIT TEMPLATE]`  
**Status:** `READY FOR PRE-REGISTRATION FREEZE`  
**Applicable Candidate:** `CAND-FREE-MACRO-001` (Scheduled Macro-Announcement Premium Conditioning)  
**Parent Governance:** AGENTS.md §1 Core Principles; Research Doctrine §4 Anti-HARKing Protocol  

---

## 1. Executive Summary & Purpose

The purpose of this document is to establish a rigorous, fail-closed **Anti-HARKing (Hypothesizing After the Results are Known)** audit protocol for `CAND-FREE-MACRO-001` before pre-registration freeze and before any authorized empirical execution.

Under AGENTS.md §1 #2 and #13, statistical validity requires that hypotheses, parameters, sample boundaries, and evaluation metrics be fixed immutably **ex-ante**. Any modification of hypotheses or selection of parameters after data exploration or empirical execution constitutes HARKing and immediately invalidates the candidate.

---

## 2. Anti-HARKing Core Audit Dimensions

| Dimension | Ex-Ante Frozen Specification | Verification Standard | Pre-Execution Status |
|-----------|------------------------------|-----------------------|----------------------|
| **1. Hypothesis Directionality** | Two-sided deviation $H_0: \mathbb{E}[D] = 0$ vs $H_1: \mathbb{E}[D] \neq 0$ (Batch A3 / D5 / D20) | No directional trading rule, long/short bias, or sign assertion may be adopted post-hoc based on sample return signs. | `[VERIFIED EX-ANTE FROZEN]` |
| **2. Search Space ($K$)** | Exactly $K=3$ grid cells: 1h, 2h, 4h post-announcement (Round 3A D11/D12) | No cell may be added, removed, tuned, or shifted. Grid size is immutable at $K=3$. | `[VERIFIED EX-ANTE FROZEN]` |
| **3. Instrument Hierarchy** | SPX index = primary research series; SPY ETF = robustness proxy (Batch A4 / D6) | SPY results cannot substitute for SPX failure. Statistical evidence cannot be conflated with tradable ETF returns. | `[VERIFIED EX-ANTE FROZEN]` |
| **4. Event Universe & Filtering** | FOMC, CPI, NFP under unified protocol (Batch A1); O-2 chronological drop for overlaps; TR-1 tie-break (CPI < NFP < FOMC) | No discretionary event exclusion, post-hoc filtering, or cherry-picking of "clean" macro releases. | `[VERIFIED EX-ANTE FROZEN]` |
| **5. Temporal Partitions** | IS: 2013-12-01 $\to$ 2021-12-31<br>OOS: 2022-01-01 $\to$ 2024-12-31<br>Blind: 2025-01-01 $\to$ 2026-09-10 (Round 4 D14–D16) | Partition boundaries are fixed by calendar dates. No shifting of cutoff dates to optimize OOS Sharpe or p-values. | `[VERIFIED EX-ANTE FROZEN]` |
| **6. Statistical Estimator** | Two-way clustered $t$-test (family $\times$ calendar quarter T2), variance-ratio effective sample size (F2), $df = G-1$, $\alpha = 0.05$ (Round 3B S-2/S-7 / Round 5 D20) | No post-hoc substitution of alternative standard errors (e.g. naive OLS, unclustered White, or ad-hoc lag lengths) to achieve statistical significance. | `[VERIFIED EX-ANTE FROZEN]` |
| **7. Census Evaluation Rule** | D6 census semantics: all $K=3$ cells must be evaluated; mixed results fail closed (Batch A5 / D13) | No selective reporting of passing cells. If any cell fails or errors, the family fails closed. | `[VERIFIED EX-ANTE FROZEN]` |
| **8. Empirical Execution Boundary** | Zero empirical backtests run; zero performance stats computed; broker disconnected (Phase 14 mandate) | Confirms that no preliminary data mining or unrecorded exploratory trials occurred prior to pre-registration. | `[VERIFIED ZERO TESTS RUN]` |

---

## 3. Pre-Registration Draft Freeze Protocol

When D17 and D18 are resolved by Human Governance, the Draft Freeze shall proceed under the following 4-step sequence:

```
Step 1: Check 26/26 Pre-Registration Checklist Items
        (Requires D17 Data Authority + D18 Sealed Manifest)
        │
        ▼
Step 2: Execute Anti-HARKing Audit Verification
        (Confirm All 8 Audit Dimensions Pass Without Deviation)
        │
        ▼
Step 3: Freeze Specification Hash Chain
        (Compute SHA-256 of Frozen Specification Documents)
        │
        ▼
Step 4: Formal Human Authorization Submission
        (Submit Pre-Registration Freeze Package for Human Signature)
```

---

## 4. Current Audit Declaration

```
ANTI-HARKING AUDIT VERDICT: PASS (PRE-REGISTRATION PHASE)

Basis:
- The parameter space is restricted to K=3 declared cells.
- The hypothesis is explicitly two-sided descriptive deviation.
- No market-data exploration, optimization, or backtesting has occurred.
- Current repository state contains zero empirical performance evidence for MACRO-001.
- Gated strictly on D17 SPX Data Authority resolution and Human Authorization.
```
