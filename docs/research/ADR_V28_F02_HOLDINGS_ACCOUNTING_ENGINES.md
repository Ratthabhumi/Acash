# ADR V28-F02 — Holdings accounting engines

- Status: `ACCEPTED_ENGINEERING_POLICY` (no historical result re-evaluated).
- Scope: `HoldingsBasedBenchmark` (`src/acash/data/contracts/etf_fx_benchmark.py`) vs
  `run_d6_portfolio` (`src/acash/research/d6/accounting.py`).

## Comparison

| Aspect | HoldingsBasedBenchmark | D6 `run_d6_portfolio` |
|---|---|---|
| Portfolios | weights must sum to 1 | weights ≤ 1, includes cash comparator |
| Timing | fills at given (close) prices | prior-close decision, next-open fill (primary); same-open sizing (sensitivity) |
| Fractional | optional; friction model is whole-share only | fractional primary, whole-share sensitivity |
| Distribution identity | full event key, revision guard | reuses `HoldingsBasedBenchmark._entitlement_key` + revision guard (V28-F03) |
| Costs | IBKR-inspired tiered friction | named scenario; SEC/FINRA via canonical `regulatory_fees.py` |
| Funding shortfall | fails closed | sells first, buys scale down (partial), never borrows |
| Consumers | legacy tests / benchmark scope | D6 registered comparators |

## Options

1. **Separate engines, shared primitives** — low migration risk, no historical drift;
   cost: two loops to maintain.
2. Adapter/facade — would need to bend D6 timing and cost contracts through an API that
   cannot express them; medium risk.
3. Full consolidation — high risk of changing frozen benchmark results; large test churn.

## Decision

Option 1. `HoldingsBasedBenchmark` = legacy benchmark compatibility. D6 accounting =
canonical engine for the registered D6 comparators. `regulatory_fees.py` = sole
historical SEC/FINRA source for new work. Shared semantics are reused by import (event
identity, `adverse_fill`, fee functions, FX fixing resolution), never re-implemented.
New portfolio-accounting work must extend D6 or justify a new ADR. HYP_007 M2 keeps its
frozen local fee schedule (see `docs/phase14/HYP_007_M2_TAF_RATE_CORRECTION_001.md`).
