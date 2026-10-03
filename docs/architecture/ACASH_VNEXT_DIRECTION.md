# ACASH VNext Direction (Proposal — No Authority Conferred)

**Date Context**: 2026-10-01
**Status**: `PROPOSED_PENDING_HUMAN_RATIFICATION`. This document recommends
direction only. It authorizes no runtime, no merge, no data acquisition, no
backtests, and no capital.

> Thesis: ACASH is a research + capital-decision platform that proves itself.
> HYP_011 is its baseline/control experiment, not its definition — and not
> its endgame. HYP_011's own acceptance condition (504 observations + 2
> rebalances) gates HYP_011 only, never the rest of the platform.

---

## 1. Proposed Architecture

```text
ACASH
├── Evidence Kernel
│   ├── immutable evidence (hash-chained observations, manifests, ledgers)
│   ├── provenance (sponsor/source binding, byte digests, retrieval logs)
│   ├── authority (intent → dispatch → consumption ledger)
│   ├── experiment registry (hypotheses, preregistrations, amendments)
│   └── dispatch ledger (single-use attempt consumption)
│   Status: PARTIALLY BUILT (HYP_011 + HYP_009 machinery; generalize next)
│
├── Research Lab
│   ├── HYP_011 = baseline/control (live, S1=1/20)
│   ├── opening-state lane (Shortlist A — feasibility first)
│   ├── order-flow / absorption lane (Shortlist B — feasibility first)
│   └── options / GEX / OI / IV lane (Shortlist C — feasibility first)
│   Status: ONE LIVE LANE; THREE GATED LANES
│
├── Portfolio Decision Support (PPDS)
│   └── read-only: statement ingestion → normalized ledger → cash/position
│       reconciliation → exposure/overlap → decision support.
│       No order endpoint. No allocation authority.
│   Status: SYNTHETIC_READONLY_RUNTIME_IMPLEMENTED_ON_REPAIR_BRANCH
│       (12 tests; real statements/broker/credentials/orders still forbidden)
│
├── Observation / Market Data Platform
│   ├── point-in-time data (SIP daily + intraday qualification paths)
│   ├── corporate actions (sponsor-authority intake, enforced end-to-end)
│   └── calendars (CA-1 NYSE authority)
│   Status: PARTIALLY BUILT (reuse HYP_009/HYP_011 paths; extend per lane)
│
└── Execution Layer
    └── remains isolated / zero authority until explicitly unlocked.
    Status: LOCKED ($0.00, NO_REAL_ORDERS, no Paper, no Live)
```

## 2. What Changes vs Today

1. **HYP_011 stops being the only lane.** It continues as the control that
   exercises the Evidence Kernel on a fixed schedule; its outcome (good or
   bad) grades the platform, not ACASH itself.
2. **Research Lab opens three gated lanes** — but the ONLY permitted next
   step per R0 governance is a Zero-Outcome Data Feasibility Audit (separate
   authorization each). No returns viewed before preregistration. No backtests
   in this task or implied by this document.
3. **PPDS starts as read-only plumbing** reusing existing Dime/Webull/IBKR/
   tax research as ingestion contracts. Statement → ledger → reconciliation
   → exposure. Still zero order authority.
4. **Market Data Platform generalizes** the HYP_009 daily + HYP_011 intraday
   qualification paths and the F10 sponsor-authority intake pattern to serve
   all lanes, instead of rebuilding per experiment.

## 3. Recommended Next Independent Lane (Data Feasibility Order)

Recommendation is ordered by DATA FEASIBILITY (cheapest verifiable data
first), not by expected returns. No mechanism is endorsed for profitability.

1. **Shortlist A — opening-state information (RI-01) first.** Rationale:
   daily bars + session opens are already qualificable through the existing
   SIP daily path; feasibility questions are answerable without new
   entitlements (coverage? open-price semantics? corporate-action
   cleanliness?). Zero-outcome audit only.
2. **Shortlist B — order flow / absorption (RI-03/RI-04) second.** Requires
   intraday trade/quote granularity (TAQ-grade); feasibility must establish
   source, cost, and point-in-time cleanliness before any design work.
3. **Shortlist C — options positioning / GEX / OI / IV (RI-05/06/08) last.**
   Requires options chains + OI history; typically the most expensive and
   license-encumbered data of the three. Feasibility first, always.

Each lane, if ever promoted past feasibility, gets its own preregistration,
negative controls, and dispatch authority — reusing (never bypassing) the
Evidence Kernel.

## 4. Explicit Non-Goals for This Proposal

- No backtests (none run, none implied).
- No Paper/Live/broker wiring.
- No real-statement ingestion, broker connectivity, or execution authority
  (synthetic PPDS read-only runtime now implemented on the repair branch;
  the old "No PPDS runtime implementation" line described the pre-code state).
- No HYP_011 acceleration, no observation-count gaming, no selection
  discretion over sessions (F14 intent-lock discipline applies platform-wide).
- NoCI/branch-protection changes (recorded as still missing).

## 5. Suggested Sequencing (Requires Separate Authorizations)

1. Ratify F14/F15 (+ F16/F10-end-to-end as implemented on the repair branch).
2. Decide Obs #2 session inclusion under the intent-lock rule.
3. Authorize Zero-Outcome Data Feasibility Audit for Shortlist A only.
4. Stand up PPDS read-only ingestion skeleton (statement → ledger) as a
   pure software task with synthetic fixtures, no real statements.
5. Revisit B/C lanes only after A-feasibility reports.
