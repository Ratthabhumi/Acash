# ACASH Personal Capital Governance & Allocation Policy V1 (Draft)

**Document:** `docs/ppds/PERSONAL_CAPITAL_GOVERNANCE_V1_DRAFT.md`
**System Module:** Capital Governance & Operator Policy Constraints
**Stage:** R0 Policy Specification
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 7, 8, 10

---

## 1. Executive Summary & Policy Invariant

In strict compliance with Section 7 of the ACASH PPDS Master Specification, **the system does NOT assume, guess, or hardcode an arbitrary allocation ratio between Investment and Trading** (such as 80/20, 90/10, or 70/30).

Setting capital allocation proportions without verified personal balance-sheet context, emergency cash buffers, and verified personal risk tolerance violates the core charter invariant: *Do not scale before validation; preserve explicit capital authority*.

Until the human operator formally ratifies the explicit risk parameters in Section 2:
```text
PERSONAL_CAPITAL_ALLOCATION_POLICY = UNRESOLVED
INVESTMENT_VS_TRADING_SPLIT = UNRESOLVED (PENDING_OPERATOR_INPUT)
```

---

## 2. Operator Policy Input Ledger (`HUMAN_INPUT_REQUIRED`)

The following parameter surface must be formally completed and signed by the human operator before active portfolio deployment rules can be generated:

| Parameter Key | Description & Scope | Units | Operator Input Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| `TOTAL_LIQUID_ASSETS` | Total investable liquid net worth across all bank and broker accounts | THB / USD | *Operator to provide* | **UNRESOLVED** |
| `EMERGENCY_RESERVE_FLOOR` | Untouchable liquid cash buffer reserved for personal living expenses (e.g. 6–12 months expenses) | THB | *Operator to provide* | **UNRESOLVED** |
| `CAPITAL_NEED_12M` | Funds required for personal commitments within the next 12 months | THB | *Operator to provide* | **UNRESOLVED** |
| `CAPITAL_NEED_24M` | Funds required for personal commitments within 12–24 months | THB | *Operator to provide* | **UNRESOLVED** |
| `CAPITAL_NEED_36M` | Funds required for personal commitments within 24–36 months | THB | *Operator to provide* | **UNRESOLVED** |
| `INVESTMENT_HORIZON_YEARS` | Target investment duration for the Investment Core/Satellite book | Years | *Operator to provide* | **UNRESOLVED** |
| `MAX_INVESTMENT_DRAWDOWN` | Maximum tolerable peak-to-trough paper drawdown on the Investment Book before derisking review | Percent (%) | *Operator to provide* | **UNRESOLVED** |
| `MAX_TRADING_CAPITAL_BUDGET` | Maximum total capital allocated to the entire Trading Book (Tactical Equity + Futures) | THB / USD | *Operator to provide* | **UNRESOLVED** |
| `MAX_DAILY_TRADING_LOSS` | Hard monetary stop: maximum allowable trading loss in a single calendar day across all trading positions | USD / THB | *Operator to provide* | **UNRESOLVED** |
| `MAX_TRADING_DRAWDOWN` | Maximum allowable drawdown on trading capital before complete tactical shutdown | Percent (%) | *Operator to provide* | **UNRESOLVED** |
| `MAX_RISK_PER_TRADE` | Maximum allowable economic loss at stop-loss invalidation on any single tactical trade | % of Trading Cap | *Operator to provide* | **UNRESOLVED** |
| `FUTURES_OVERNIGHT_ALLOWED` | Policy flag: whether CME Micro futures contracts may be held across session closes or intraday only | Boolean | *Operator to provide* | **UNRESOLVED** |
| `MONTHLY_NEW_SAVINGS` | Projected recurring monthly cash savings available for new deployment | THB / Month | *Operator to provide* | **UNRESOLVED** |
| `TAX_REMITTANCE_PREFERENCE` | Planned repatriation timeframe for offshore gains relative to Thai Revenue Department tax years | Policy Option | *Operator to provide* | **UNRESOLVED** |

---

## 3. Core Capital Governance Rules

### 3.1 Cash as an Active Allocation (`HOLD_CASH`)
- **First-Class Asset:** In PPDS, unallocated cash is **not** a defect or drag. Cash is an active risk-management allocation that protects optionality.
- **Fail-Closed Condition:** If no candidate opportunity in the investment or trading universe satisfies all pre-registered selection hurdles, the system issues `HOLD_CASH`. The system must **never** force trades merely because unallocated cash balances exist.

### 3.2 Strict Book Separation & Anti-Contagion
- **Decoupled Ledgers:** The Investment Book and Trading Book run completely independent accounting ledgers.
- **Loss Containment:** A catastrophic loss in Equity Tactical or Futures Trading can **never** trigger automatic margin transfers or asset sales from the Investment Book.
- **Transfer Authorization:** Any re-allocation of capital between books requires an explicit, cryptographically signed operator record.

### 3.3 Speculative Theme Ceiling
- High-uncertainty, thematic investments (e.g. Space tech, quantum computing, speculative small-caps) are segregated into the **Speculative / Thematic Book**.
- The book is governed by a hard capital ceiling $\theta_{\text{spec}}$. If valuation appreciation causes the book to exceed $\theta_{\text{spec}}$, new cash deployments to this bucket are strictly halted, and a rebalancing review is flagged.

### 3.4 Invalidation-Based Sizing Discipline
- **Economic Risk Sizing:** Every trading order must define an explicit structural invalidation level (stop loss). Position sizing is derived from the dollar loss at invalidation, inclusive of transaction friction and slippage.
- **Prohibition on Margin-Based Sizing:** Broker-displayed day margins (e.g. $50 per CME micro contract) must **never** be used to determine position size. Sizing by margin power is irresponsible leverage and violates ACASH risk standards.

---

## 4. Verification Ledger

- Policy Status: DRAFTED (V1 Complete)
- Capital Allocation Split: UNRESOLVED (Awaiting Human Inputs)
- Human Parameter Surface: 14 Critical Inputs Censused
- Risk Firewalls: FORMALLY CODIFIED
