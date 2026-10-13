# $1,000 Capital Feasibility Research Plan (Paper-Gated)

**Status:** RESEARCH PLAN — NOT A CAPITAL ALLOCATION DECISION, NOT AN AUTHORIZATION.
**Date:** 2026-10-13
**Standing authority at time of writing:** `REAL_CAPITAL_AUTHORITY = $0.00`; `NO_REAL_ORDERS = true`. Changing either requires an explicit, separately recorded human ratification. This plan does not change them.

## 1. Question

Given $1,000 of hypothetical committed capital, which ACASH research paths are economically feasible (fees, spread, and minimum-size constraints dominate), and what gate sequence must clear before any of them may be tested on paper or live?

## 2. Candidate Alternatives (Descriptive)

| # | Path | Rough Economic Reality at $1,000 | Primary Gate Dependency |
| :-- | :--- | :--- | :--- |
| A | US ETF swing/trend (VOO/BND/GLD/BIL panel) | $0 commissions at IBKR/Alpaca; $1,000 = 1-4 shares per name; position granularity (share-level) is the binding constraint, not fees | Lane A data admission -> benchmark -> paper R1 |
| B | Broad optimizer/rebalancer over same ETFs | Same fee structure; needs >= 4 names with meaningful weights — feasible but variance of allocation error is high at share granularity | Same as A + allocator evaluation on admitted data |
| C | Futures/micro contracts (e.g., MES) | Margin feasible at $1,000, but roll mechanics and contract data admission do not exist in ACASH; would be a new data lane entirely | New qualification lane (out of M1.7 scope) |
| D | FX/cryptovernight carry hypotheses | 24/7 data path exists only as synthetic; no admitted real feed; leverage rules differ | Out of scope; new admission required |

## 3. Recommended Order (Research Only)

1. **Path A first:** it reuses the Lane A universe already specified in `docs/research/LANE_A_UNISSUED_AUTHORITY_PACKET_20261013.md` and the offline authority machinery in `src/acash/data/qualification/lane_a_authority.py`.
2. Path B as a follow-on using the same admitted panel.
3. Paths C/D are explicitly deferred; no admission machinery exists and inventing one is out of scope for M1.7.

## 4. Gate Dependencies (No Step May Be Skipped)

```
Human issues Lane A authority
  -> offline dry run (lane_a_authority.dry_run_validate) passes
  -> [separately authorized bounded network execution: <=12 ops, <=512 KiB, $0 paid]
  -> manifest + integrity qualification of the 5-day x 4-symbol x 2-adjustment panel
  -> benchmark correctness (M1.6, landed) applied to the admitted panel
  -> paper exercise under existing paper infrastructure (NO_REAL_ORDERS stays true)
  -> economics review: share-granularity impact, slippage model, minimum testable size
  -> ONLY THEN a human may consider a capital-authority amendment ($0.00 -> $1,000)
```

## 5. Honest Boundaries

- Nothing in this plan demonstrates profitability; M1.6/M1.7 establish correctness and data admissibility only.
- $1,000 feasibility conclusions here are desk arithmetic on documented fee schedules, not empirical fill data.
- A profitable paper result, if ever obtained, does not itself authorize live capital; that boundary remains human.
