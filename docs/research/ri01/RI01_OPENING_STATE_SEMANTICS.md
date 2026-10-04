# RI-01 Opening-State Semantics (methodology, no outcomes)

This is the most important methodological section: whether RI-01 can obtain a
deterministic, reproducible opening-state representation at all.

## 1. Distinct opening concepts (must never be conflated)

| Concept | Definition | Status for RI-01 |
| :--- | :--- | :--- |
| Official exchange open | RTH open instant from CA-1 (09:30 ET regular sessions) | `RESOLVED` (calendar authority) |
| Opening auction/cross | Primary-exchange opening cross print and timestamp | `OPEN` — dedicated auction endpoint unqualified for RI-01 scope |
| First trade | First continuous-session trade print | `OPEN` — requires trade-level (not bar-level) authority |
| First minute bar (`BAR_0930`) | Left-edge-labelled `[09:30:00, 09:31:00)` OHLCV bar | `RESOLVED_IN_PRINCIPLE` (MEC-0015 left-edge semantics; RI-01 scope unqualified) |
| 09:30:00 bar semantics | Bar START timestamp, not end (Alpaca convention, MEC-0015 §4) | `RESOLVED_IN_PRINCIPLE` |
| Bar start vs bar end | Provider stamps start; decision logic must convert explicitly | `RESOLVED_IN_PRINCIPLE` (mapping rule pinned in MEC-0015 §4.2) |
| Adjusted vs raw | Raw preserves execution boundaries; split-adjusted rewrites history | `POLICY_PINNED` — raw required; adjusted prohibited for opening attribution |
| Overnight gap | Prior close → open discontinuity (includes all overnight news flow) | `DEFINED` — belongs to the $r_1$ predictor by construction (Gao et seq.) |
| Pre-market contamination | Extended-hours prints must never enter RTH bars | `POLICY_PINNED` — RTH-only grid; any pre-market inclusion is a defect |

## 2. Predictor definitional fork (must be frozen at preregistration, not here)

Following Gao et al. (2018), the canonical predictor is:

```text
r1(t) = ln(P_10:00,t / P_16:00,t-1)   # previous close THROUGH 10:00 ET
```

This deliberately INCLUDES the overnight gap — it is not "09:30→10:00".
Consequences for feasibility:

1. **$P_{16:00,t-1}$ authority is the single hardest definitional item.**
   Candidates: official closing-auction cross, SIP daily-bar close, 15:59
   continuous bar close. MEC-0014 §10.2 already mandates a contract test
   (auction vs daily close equivalence) before any definition is frozen.
   Feasibility status: `OPEN` (test designed, not executed).
2. **$P_{10:00,t}$ authority** is the 10:00 bar open (first exposure minute),
   never the 10:00 close. Status: `DEFINED_IN_PRINCIPLE` (left-edge mapping).
3. **Retail-rule variants are OUT.** First-5-minute EMA, 1-minute FVG, fixed
   09:30–09:45 range levels are NOT candidate definitions here (R0 keeps all
   parameters UNSET; Fetna 2026 independently falsified cost-robust ORB).

## 3. Session-shape edge cases

| Case | Rule |
| :--- | :--- |
| DST spring-forward / fall-back | UTC bounds derived from CA-1 per session; never hand-offset ET↔UTC |
| Half-days (e.g. day-after-Thanksgiving, Christmas Eve) | Early-close calendar semantics; minute grid pro-rated; 390-bar completeness does NOT apply |
| Late open / delayed open | Session excluded unless the calendar + provider jointly attest the realized open instant |
| Trading halt straddling the open | Session excluded (zero-volume opening bars are evidence of halt, not of zero information) |
| Zero-volume opening bar, no halt on record | `DATA_UNAVAILABLE` for opening-state purposes; never treated as a zero return |
| Missing `BAR_0930` | Session excluded; never forward-filled from 09:31 |
| Symbol not yet listed / delisted | Outside universe for that session; never backfilled |

## 4. Determinism verdict (feasibility-level)

A deterministic opening-state representation is CONSTRUCTIBLE IN PRINCIPLE
from (CA-1 calendar × left-edge 1Min SIP raw × prior-close authority ×
fail-closed exclusion), but it is NOT YET DEMONSTRATED for RI-01 scope
because the prior-close authority test and RI-01-scope minute coverage are
both unexecuted. If either fails, RI-01 remains blocked.
