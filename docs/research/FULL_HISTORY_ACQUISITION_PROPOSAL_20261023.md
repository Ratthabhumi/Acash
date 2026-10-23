# Full-History ETF Acquisition Proposal (Not Issued)

**Date:** 2026-10-23
**Status:** `PROPOSED_NOT_ISSUED`
**Parent main:** `ef89fd49b1f092bacd0847d6d56dfc4d8c132bfd`
**Real-data admission:** `NOT_ADMITTED`

This is a proposed scope, not an authority. It does not authorize HTTP, credentials,
raw retention, dataset admission, Lane B, D6 execution, paper/live trading or capital.

## 1. Why a Separate Scope Is Required

The existing Lane A canary is five sessions (`2026-09-28` through `2026-10-02`). It can
prove retrieval mechanics only. It cannot support a multi-year D6 after-cost study.
Broadening that canary silently would violate the exact-scope rule. This proposal is the
separate scope that must be authorized, if the owner chooses to proceed.

## 2. Proposed Scope

| Field | Proposed value |
| :--- | :--- |
| Provider | Alpaca |
| Feed | One operator-selected feed, `sip` preferred only if entitled |
| Timeframe | `1Day` |
| Symbols | `VOO`, `BND`, `GLD`, `BIL` |
| Adjustments | `raw` and `split` |
| Start | 2016-01-01 |
| End | 2025-12-31 (inclusive) |
| HTTP budget | At most 32 requests |
| Observed-byte budget | At most 8,388,608 bytes |
| Retry / fallback | Zero / none |
| Paid amount | USD 0 |
| Orders / capital | None; USD 0.00 |

The window deliberately stops before the current year so that the study does not mix a
completed historical panel with unfinished 2026 data. Any later extension is a new scope.

## 3. Budget Rationale

At `limit=1000`, approximately 2,517 NYSE sessions per symbol and two adjustment series
requires about 3 pages per series. Eight series therefore need about 24 pages. A budget
of 32 requests leaves limited pagination/operational headroom without permitting an
unbounded crawl. The byte ceiling is a hard observed cap, not an estimate.

The budget is a ceiling, not an entitlement to spend it. Every request must remain
bound to the exact scope and the frozen request identity.

## 4. Acceptance Prerequisites

1. Signed V2 byte-contract ratification.
2. Written Alpaca rights answer covering current tier, SIP/IEX, raw retention, derived
   use, redistribution and 2016-2025 access.
3. A signed, exact-scope acquisition authority with the budgets above.
4. A D4 corporate-action plan for the full window, including BND/BIL monthly
   distributions, VOO quarterly distributions and GLD no-cash-distribution treatment.
5. A decision on trust root, key custody, trusted clock and crash durability, or an
   explicit recorded acceptance of the unresolved state.
6. Independent admission through `evaluate_d5_real_admission()`; no direct D5 seal.

## 5. Explicit Non-Claims

- This proposal does not assert that 2016-2025 data is currently accessible.
- It does not assert that raw retention or derived redistribution is permitted.
- It does not qualify corporate actions, PIT vintages or survivorship treatment.
- It does not authorize a D6 run, strategy selection or live capital.
- It does not convert the 30 `SOURCE_VERIFIED_CANDIDATE` events into admitted evidence.

## 6. Recommended Sequence

1. Close V2 ratification and the rights answer.
2. Issue a bounded canary under the existing Lane A packet, if the owner still wants a
   retrieval check.
3. If the canary succeeds, issue this full-history scope as a separate decision.
4. Acquire within budget; retain raw pages and receipts.
5. Admit at `RETROSPECTIVE_QUALITY_QUALIFIED` first; only then decide whether a PIT
   upgrade is supportable.
6. Run D6 only after D5 admission and a separate empirical-run authorization.

Until every step is explicitly authorized, the correct state is `UNISSUED` and
`NO_REAL_ORDERS=true`.
