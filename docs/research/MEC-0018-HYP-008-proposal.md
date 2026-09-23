# Research Re-Inception Proposal (PROPOSED — NOT PREREGISTERED): MEC-0018 / HYP_008

```text
[CANDIDATE HYPOTHESIS ID: HYP_008]
[REGISTRATION STATE: PROPOSED_NOT_PREREGISTERED]
[MECHANISM LINEAGE: MEC-0018]
[AUTHORIZATION: AUTHORIZE_HYP_007_POST_R4_CLOSURE_AND_CONDITIONAL_HYP_008_RESEARCH_INCEPTION]
[CANONICAL HEAD: 653b007e4d5ce73c5022086f40737a4525410a55]
[CLOSURE COMMIT: 526a0eb]
[HYP_007 STATE: OPERATIONALLY CLOSED]
[HYP_008 BACKTEST AUTHORIZATION: NONE]
[M3 ACCESS: FALSE (records read = 0)]
[QUARANTINE GAP ACCESS: FALSE (records read = 0)]
[PAPER / LIVE / CAPITAL: LOCKED / LOCKED / 0.00]
```

> **Read this first.** This document is a *research-quality proposal*, **not** a registration, and
> it creates **no** authority to backtest, trade, or access data. It exists solely to support the
> human review step `REVIEW_HYP_008_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION`. M1/M2 evidence is
> `DISCOVERY / DESIGN` only; every tool setting below that would numerically exploit M2 is rejected.

---

## 1. Metadata

| Field | Value |
| :--- | :--- |
| Candidate ID | `HYP_008` |
| Version | `v0 proposal (PROPOSED_NOT_PREREGISTERED)` |
| Mechanism lineage | `MEC-0018` |
| Research family | D. Regime Filtering (backlog Family C) |
| Working title | Volatility & Liquidity Regime-Conditioned Time-Series Trend vs. Unconditioned Trend Baseline |
| Registry refs | `RQ-BACKLOG-003`; `CAND-REGIME-MA-FILTER-001` (F-5) |
| Ancestor (design context, NOT evidence) | `HYP_007 / MEC-0017` — operationally closed; decomposition dossier `docs/phase14/HYP_007_POST_R4_FAILURE_DECOMPOSITION.md` |

## 2. Research Question (Preregistration Skeleton)

> Does conditioning a standard time-series trend model on an objective, **pre-declared**,
> eponymous ex-ante volatility/volume regime filter yield a statistically superior risk-adjusted
> net-of-cost profile **relative to an identical unconditioned trend baseline**, after penalizing
> filter-induced turnover and after a multiple-testing haircut?

Skeleton pair:
- **H₀:** Regime-conditioned variant has post-cost (DSR) ≤ unconditioned baseline (no improvement).
- **H₁:** Regime-conditioned variant shows preregistered-significant post-cost improvement in DSR /
  MinTRL **and** no unacceptable tail-risk increase, net of whipsaw turnover.

## 3. Scope & Target (Proposed — to be frozen at R1)

- Target instrument(s): `ES` (primary) or `BTC` (secondary) — **exactly one** baseline to be frozen
  at R1; both are outside the exhausted SPY intraday family.
- Timeframe: H1–D1 (multi-hour to daily), per backlog.
- Baseline trend formulation: TO BE DECIDED by human (SMA-based vs time-series momentum candidate) —
  explicitly an open human decision, **not** an agent choice.
- Search-space cardinality: small, frozen pre-registration; every parameter first-principles or
  literature-derived; **zero parameters derived from M1/M2**.

## 4. Anti-Harking / Anti-Decay Contract (Non-Negotiable)

1. **M1/M2 are DISCOVERY/DESIGN forever** — no HYP_008 estimate may quote M1/M2 as evidence.
2. All thresholds/parameters declared before any data touch; registered `return_sha256` lineage.
3. **Mandatory unconditioned baseline control** with explicit ablation isolating the filter.
4. Ex-ante volatility estimator (unshifted, no centered windows) — PIT-safe by construction.
5. Multiple-testing haircut (trial-cardinality-aware DSR) using the sealed Phase 6 statistical engine.
6. Fresh data only; data provider qualification and manifest sealing occur **before** R1, after
   explicit human authorization.

## 5. Required Data & Current Status

| Dataset | Status |
| :--- | :--- |
| `ES` or `BTC` qualified OHLCV (H1–D1) | **NO CONNECTOR INSTALLED** — feasibility step required |
| Correct calendar / session metadata | To be qualified |
| Volume series | To be qualified |
| SEC31/FINRA schedule reuse | Existing MEC-0015 schedules apply by reference |

## 6. PIT / Confounder Risks (Pre-R1)

- Regime-estimator look-ahead (mitigated: ex-ante unshifted estimator).
- Regime classifier acting as disguised post-hoc curve fit (mitigated: pre-registration, K small).
- False regime transitions generating turnover (measured into H₀ by construction).
- Missing the single largest trend run due to false "hostile" classification (H₀ captures this).

## 7. Gate Governance

- Uses the Phase 6 DSR/PBO engine; no G1–G7 from HYP_007 are inherited or reused.
- Terminal-research style follows the HYP_004 closure precedent (additive decision manifest).
- No gate may be relaxed post-hoc.

## 8. Explicit Non-Authorizations (unchanged)

Capital `$0.00` · `NO_REAL_ORDERS=true` · Paper `LOCKED` · Live `LOCKED` · M3 `LOCKED_ZERO_ACCESS` ·
Quarantine gap `[2026-08-15, 2026-09-23)` `STRICTLY_ZERO_ACCESSED`.

## 9. Human Decision Requested

Ratify/reject this `PROPOSED_NOT_PREREGISTERED` proposal via
**`REVIEW_HYP_008_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION`**. If rejected, `HYP_008 = NOT_CREATED`
and the null branch (abandon trend-momentum family) is retained per
`docs/phase14/HYP_008_RESEARCH_INCEPTION_REVIEW.md` §6.

---

### Verification Ledger
- Implementation Status: COMPLETE (document only — zero mutations)
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: N/A (no computations in this proposal)
- Local Test Suite: N/A (no code change)
- Type Checker (MyPy): PENDING (run before Commit B)
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats: PROPOSED_NOT_PREREGISTERED ONLY; promotion is a research-quality judgment,
  not a validity or profitability claim.