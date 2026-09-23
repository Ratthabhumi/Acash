# Phase 14 HYP_008: Conditional Research Inception Review

```text
[DOCUMENT ID: docs/phase14/HYP_008_RESEARCH_INCEPTION_REVIEW.md]
[AUTHORIZATION: AUTHORIZE_HYP_007_POST_R4_CLOSURE_AND_CONDITIONAL_HYP_008_RESEARCH_INCEPTION]
[CANONICAL HEAD: 653b007e4d5ce73c5022086f40737a4525410a55]
[CLOSURE COMMIT: 526a0eb]
[HYP_007 STATE: OPERATIONALLY CLOSED (FAIL_CURRENT_EDGE_NOT_SUPPORTED)]
[HYP_008 STATE: PROPOSED_NOT_PREREGISTERED (subject to human ratification)]
[MECHANISM LINEAGE: MEC-0018 (candidate proposal only — NOT registered)]
[M3 ACCESS: FALSE (records read = 0)]
[QUARANTINE GAP ACCESS: FALSE (records read = 0)]
[BACKTEST AUTHORIZATION: NONE]
```

- **Decision type:** Conditional research-inception **recommendation**. This document does **not**
  register, seal, or authorize a hypothesis. Only a human decision may ratify a proposal and open R1.
- **Anti-harking rule (in force):** M1/M2 are irrevocably re-classified as
  `DISCOVERY / DESIGN` evidence. The descriptive failure-decomposition tables
  (see `HYP_007_POST_R4_FAILURE_DECOMPOSITION.md`) may inform *design*, but **no statistic computed
  on M1/M2 may be used as new-hypothesis evidence**. Any future HYP_008 evaluation must use fresh,
  never-consulted data only.

---

## 1. Purpose

Given the post-R4 closure verdict (`FAIL_CURRENT_EDGE_NOT_SUPPORTED`), the authorization requires a
descriptive failure decomposition (delivered separately) and a **conditional** assessment of whether
any research candidate from the repository registry qualifies to be **promoted** to a
`PROPOSED_NOT_PREREGISTERED` HYP_008. Up to five candidates may be compared; at most one may be
promoted; if none qualifies, the verdict is `NO_HYP_008_READY — CONTINUE_MECHANISM_RESEARCH`.

## 2. Descriptive Findings That Inform Design (NOT Hypothesis Evidence)

From `HYP_007_POST_R4_FAILURE_DECOMPOSITION.md` (post-hoc, descriptive only):

1. **Gross-edge decay dominates:** M2 gross expectancy `$14.33/trade` vs M1 `$131.37` (−89.1%).
2. **LONG leg collapsed:** M2 LONG net expectancy `−6.13/trade` vs M1 `+163.56`; SHORT retained
   positive `+21.78` in M2.
3. **Time-of-day:** strongest deterioration at `15:00` (M1 +13,291.56 → M2 −8,508.92) and `11:30`.
4. **Calendar-time decay:** M2 2024 net-positive (+77.68/trade), 2025 (−15.06), 2026 (−28.64).
5. **Volatility-state:** M1 positive in all terciles; M2 positive only in LOW-realized-vol states
   (MEDIUM −78.75, HIGH −43.73) under **M1-derived** fixed cutoffs.
6. **Liquidity/friction burden stable per trade** (`$7.85` M1 → `$7.36` M2 baseline) — friction is an
   amplifier, not the root cause.

These observations are consistent with the peer-reviewed record on **post-publication decay of
market intraday momentum**:
- Rosa (2022), *Journal of Futures Markets*: the intraday-momentum predictability **disappears
  out-of-sample**; regime-conditional thresholds matter.
- Gao et al. (2018), *Journal of Financial Economics* (the M2-family canonical paper): the effect is
  **stronger on high-volatility days, higher-volume days, and news days** — a regime-dependent
  characteristic that M2's MEDIUM/HIGH-vol failure directly inverts.
- Li, Sakkas & Urquhart (2022), *Journal of Financial Markets*: intraday time-series momentum is
  stronger when liquidity is low, volatility high, and information discrete.
- McLean & Pontiff (2016), *Journal of Finance* (mechanism class of post-publication anomalies):
  documented anomaly returns decline materially after publication.

## 3. Candidate Mechanism Matrix (≤ 5)

| # | Candidate | Family | Registry ref | Qualifies for HYP_008? | Why / Why not |
| :--- | :--- | :--- | :--- | :--- | :--- |
| C-1 | **Volatility & liquidity regime-conditioned trend** (with **mandatory** unconditioned baseline) | D. Regime Filtering / Family C backlog | `RQ-BACKLOG-003`; `CAND-REGIME-MA-FILTER-001` (F-5), `docs/phase14/research_candidates.md` | **YES — promoted** (single candidate) | Orthogonal target (`ES`/`BTC`, H1–D1), distinct mechanism, explicit unconditioned-baseline control, low data barrier, doctrine-13 H0 framing; directly motivated by descriptive vol-state concentration. |
| C-2 | Intraday momentum **variant** (SPY, epochs/vol target tweak) | C. Momentum | — (prohibited scope) | **NO** | Expressly prohibited by closure covenant: no parameter/rescue variants of HYP_007. |
| C-3 | **Macro-announcement day conditioning** | A. Structural / Forced Flow | MEC-0014 quarantine list | **NO** | Quarantined variable class for MEC-0014+/HYP_007 rescue; promotion requires authoritative timestamp authority that ACASH does not currently possess for the full required window. |
| C-4 | **Options gamma / short-vol (GEX)** exposure explanation | Mechanistic explanation only | MEC-0014 quarantine item | **NO** | Historical point-in-time GEX is unresolved in ACASH. Usable only as a `MECHANISTIC_EXPLANATION_ONLY` lens, never as a promotable micro-hypothesis. |
| C-5 | **Abandon intraday-momentum family entirely** (null alternative) | Terminal | (required null) | **NO — but retained as mandatory control** | Required as the null branch in §6 any promoted alternative must beat; no new backtest needed to hold it. |

## 4. Candidate C-1 Qualification Appraisal (per quality standard)

| Field | Assessment |
| :--- | :--- |
| Economic mechanism | Regime/volatility conditioning toggles exposure of a simple trend model; H0 = no risk-adjusted improvement after whipsaw costs (doctrine 13). |
| Why an edge could exist | Vol clustering (ARCH family); trends operate with higher SNR in moderate-sustained vol; post-hoc M2 vol-state concentration is directionally consistent — but is `DISCOVERY`, not evidence. |
| Why it might NOT exist | Regime-classifier lag; filtering removes the most profitable trend phases; whipsaw costs. |
| Orthogonality to HYP_007 | Different target (`ES`/`BTC`), different timeframe (H1–D1), different mechanism class (regime filter on a *separate* trend baseline, not a HYP_007 rescue). |
| Required data | Qualified OHLCV (timestamp, OHLC, volume) on `ES` or `BTC`; **no connector currently installed** — must be qualified and manifest-sealed during a pre-R1 feasibility step. |
| PIT risk | Look-ahead bias in volatility estimator (centered windows); must use unshifted ex-ante estimator. |
| Falsification | Pre-registered DSR / MinTRL improvement over unconditioned baseline with explicit multiple-testing haircut (pre-existing Phase 6 engine). |
| Promotion limits | `PROPOSED_NOT_PREREGISTERED` only. No parameter partially from M2. All thresholds first-principles. |

## 5. Promotion Decision

**PROMOTED (single candidate):** `HYP_008` as `PROPOSED_NOT_PREREGISTERED`, mechanism lineage
`MEC-0018`, research family **D / Family-C-backlog**: *"Volatility & Liquidity Regime-Conditioned
Time-Series Trend vs. Unconditioned Trend Baseline."*

Promotion conditions that must hold before any R1:
1. All M1/M2 evidence remains `DISCOVERY / DESIGN` (never confirmatory).
2. Thresholds pre-declared from first principles or literature — **zero M2-derived parameters**.
3. **Mandatory** explicit unconditioned baseline control (self-configuration ablation).
4. Data provider qualification + manifest sealing for the fresh target (no connector today).
5. Human ratification via `REVIEW_HYP_008_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION`.

Rationale (design-informed, not M2-optimization): the only repository candidate with (a) a cleaner
falsification frame than the rest, (b) a mandatory baseline control that the decomposition's
"friction-as-amplifier, gross-edge-decay" finding directly rewards, and (c) zero entanglement with
the prohibited HYP_007 rescue space is the regime-conditioned trend question (`RQ-BACKLOG-003` /
F-5). The decomposition's vol-state concentration (M2 positive only in LOW vol under M1 cutoffs) is
used **only** as design motivation, never as evidence or as a threshold source.

## 6. Null-Alternative Covenant

The **abandon-family null branch (`C-5`)** is automatically retained: if, on fresh prospective data,
no regime-conditioned specification survives confidentially pre-registered falsification against its
unconditioned baseline, the intraday/trend-momentum research family stays closed. Both branches —
promotion-worthy alternative vs. null — must be compared; the null requires **no** new backtest to
be held true until evidence to the contrary is produced.

## 7. Explicit Non-Authorizations

| Item | State |
| :--- | :--- |
| HYP_008 registration | NOT PERFORMED (proposed only) |
| R1 (ResearchReInceptionGate) | NOT OPENED |
| Backtest on M3 | NOT AUTHORIZED |
| Backtest on M1/M2 for HYP_008 confirmation | PROHIBITED (anti-harking) |
| Market data connector install | NOT AUTHORIZED |
| M3 / quarantine reads | ZERO |
| Paper / live / capital | `LOCKED` / `LOCKED` / `$0.00` (unchanged) |

## 8. Next Human Decision (single possible outcome)

**`REVIEW_HYP_008_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION`** —
review `docs/research/MEC-0018-HYP-008-proposal.md` (PROPOSED_NOT_PREREGISTERED), ratify or reject,
and (if ratified) authorize the pre-R1 data-qualification and R1 registration steps explicitly.

If the human instead rejects C-1, the fallback verdict is automatically
`NO_HYP_008_READY — CONTINUE_MECHANISM_RESEARCH` (null branch C-5 remains held).

---

### Verification Ledger
- Implementation Status: COMPLETE (recommendation only; no mutation performed)
- Contract Enforcement: STRICT FAIL-CLOSED (M3/0, quarantine/0, anti-harking, zero backtest)
- Mathematical Authority: N/A (no statistics performed in this decision; statistics in sibling
  decomposition dossier)
- Local Test Suite: N/A for this decision doc (analysis engine already tested 10/10)
- Type Checker (MyPy): PENDING (run before Commit B)
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats: POST-HOC DESCRIPTIVE only; promotion is a research-quality judgment,
  not a validity claim; no M2-optimal threshold was derived or used.