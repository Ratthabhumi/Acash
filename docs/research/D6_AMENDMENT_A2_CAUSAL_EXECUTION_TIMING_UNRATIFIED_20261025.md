# D6 Amendment A2 — Causal Execution Timing (UNRATIFIED)

- Status: `PROPOSED_UNRATIFIED`; requires an explicit owner decision before any admitted
  empirical D6 run. Complements A1 (descriptive comparison), which is also unratified.

## Proposed text

| Item | PRIMARY (`PRIOR_CLOSE_DECISION_NEXT_OPEN`) |
|---|---|
| Decision time | close of the previous admitted session |
| Information set | prices, holdings, settled cash through that close; receivables excluded |
| Order quantities | target shares frozen at decision; rescaled only by a split effective at execution |
| Execution | next admitted session open, adverse slippage, commission, statutory fees |
| Mark-to-market | execution session close |
| First session | no prior close: stay in cash; initial construction at the second admitted session. No synthetic prior close, no warmup unless separately qualified |
| Annual rebalance | decided at the last close of year Y−1, executed at the first open of year Y |
| Gaps / insufficient cash | sells first; buys scale down proportionally (partial); never borrow |
| Missing prior close | fail closed (`D6_MISSING_CLOSE_PRICE`); no forward fill |
| Ex-date on execution day | entitlement from holdings before that session's trades |

SENSITIVITY: `SAME_OPEN_SIZING_IDEALIZED` (sizing on the execution-session open) is
reported only as a labelled idealization.

Initial study currency is USD. USD/THB is a reporting overlay (`d6_nav_in_currency`,
exact-date fixings, no fallback); empirical FX sensitivity is `NOT_RUN` until a dated,
licensed FX history is admitted.
