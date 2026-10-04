# RI-01 Point-in-Time / Lookahead Control (mandatory)

No input may silently use information unavailable at the simulated decision
timestamp. Classification is per FIELD, not per dataset: the same vendor
response can carry fields with different availability labels.

## 1. Availability labels (single authority for this pack)

| Label | Meaning |
| :--- | :--- |
| `AVAILABLE_AT_OPEN` | Knowable at/before the 09:30 ET open (e.g. prior close, calendar, static symbol master) |
| `AVAILABLE_AFTER_N_SECONDS` | Knowable N seconds after a stated event (e.g. first trade + tape latency) |
| `AVAILABLE_AFTER_BAR_CLOSE` | Knowable only when the stated minute bar completes (e.g. 10:00 bar open is knowable at 10:00:00, not before) |
| `END_OF_DAY_ONLY` | Knowable only after session close (e.g. official daily close, closing-auction cross) |
| `REVISED_LATER` | First published value may be overwritten (vendor revision); backtest must use the as-first-published vintage or exclude |
| `UNKNOWN` | Observability timestamp not established — treated as UNAVAILABLE until proven otherwise |

Default rule: **unclassified ⇒ `UNKNOWN` ⇒ unavailable.** Availability is
proven per field by contract test, never assumed from field names.

## 2. Field classification (candidate baseline; each row needs its own proof)

| Field | Provisional label | Proof status |
| :--- | :--- | :--- |
| Prior session official close | `END_OF_DAY_ONLY` (t-1) → `AVAILABLE_AT_OPEN` (t) | `NEEDS_CONTRACT_TEST` (auction vs daily equivalence) |
| CA-1 session open/close instants | `AVAILABLE_AT_OPEN` | `PROVEN_IN_REPO` (calendar authority) |
| 09:30–10:00 minute bars | `AVAILABLE_AFTER_BAR_CLOSE` each | `NEEDS_CONTRACT_TEST` (RI-01 scope) |
| 10:00 bar open (decision price) | `AVAILABLE_AFTER_BAR_CLOSE` (10:00:00) | `NEEDS_CONTRACT_TEST` |
| Dividend cash amount / ex-date | `UNKNOWN` (vendor vintage not guaranteed) | `BLOCKED_ON_VENDOR_CONTRACT` |
| Split ratio / ex-date | `UNKNOWN` | `BLOCKED_ON_VENDOR_CONTRACT` |
| Symbol master (ticker/CUSIP mapping) | `UNKNOWN` | `BLOCKED_ON_VENDOR_CONTRACT` |
| Quote/spread at decision boundary | `UNKNOWN` (endpoint unqualified for RI-01) | `BLOCKED_ON_VENDOR_CONTRACT` |
| Provider request latency / delay | `UNKNOWN` (15-min SIP rule known for HYP_011 daily path only) | `NEEDS_CONTRACT_TEST` |

## 3. Lookahead invariants (binding on any future implementation)

```text
I_{10:00:00} = sigma({all fields with availability <= 10:00:00 ET on day t})
```

1. The $r_1$ predictor may only consume fields in $I_{10:00:00}$.
2. Prior-close fields enter $I$ only via the proven close authority (never via a
   bar that restates them later).
3. Any `REVISED_LATER` field used in backtest must carry its as-first-published
   vintage; otherwise the session is excluded.
4. Decision-price evaluation uses the bar OPEN at the decision instant, never
   that bar's close (same-bar ambiguity is a defect, not a modeling choice).
5. Macro-release timestamps (08:30/10:00 ET) are conditioning metadata for
   future regime analysis ONLY — quarantined from the baseline specification.
