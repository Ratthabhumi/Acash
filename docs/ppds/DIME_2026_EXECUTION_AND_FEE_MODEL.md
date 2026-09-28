# ACASH Dime! (KKP) 2026 Execution & Fee Model R0

**Document:** `docs/ppds/DIME_2026_EXECUTION_AND_FEE_MODEL.md`
**System Module:** Broker Execution Economics & Custodian Due Diligence
**Custodian:** Dime! by Kiatnakin Phatra Securities (KKP)
**Stage:** R0 Due Diligence & Cost Specification
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 1, 3, 6

---

## 1. Executive Summary & Custodian Role

Dime! (operated by Kiatnakin Phatra Securities Public Company Limited) serves as the primary custodian for the user's existing **Investment Book** (Core/DCA, Satellite quality stocks, and FCD cash balances).

This document establishes the empirical fee structure, promotional calendar constraints, regulatory frictions, and execution trade-offs governing Dime! in 2026.

---

## 2. Standard Commission & Baseline Fee Architecture

| Fee Component | Statutory / Contractual Value | Applies To | Notes |
| :--- | :--- | :--- | :--- |
| **Standard Broker Commission** | **0.15%** of gross trade value | BUY and SELL | No minimum commission per ticket (min USD 0.00). |
| **Monthly Free Trade** | **1 Free Trade per calendar month** | BUY or SELL | First trade executed in each calendar month is exempt from the 0.15% commission. |
| **VAT on Commission** | **7.0%** of broker commission | All commission-bearing trades | Applies only to the broker commission portion, not to gross principal. |
| **SEC Section 31 Fee** | Currently ~**0.00278%** ($0.0000278) | **SELL orders only** | Pass-through US regulatory fee. Subject to periodic US SEC updates. |
| **FINRA TAF Fee** | **$0.000166 per share** (Max $8.30/trade) | **SELL orders only** | Trading Activity Fee; rounded up to the nearest cent. |
| **CAT Regulatory Fee** | Variable / Inconsistent across pages | Per-transaction / per-share | **SOURCE CONFLICT (See § 3.2)**. Parameterized in friction model. |
| **W-8BEN Withholding Tax** | **15.0%** on gross US dividends | US Cash Distributions | Reduced rate under the US–Thailand Double Taxation Agreement (DTA). |
| **Account Maintenance Fee** | **$0.00** / Free | Account custody | No monthly or annual account holding fee. |
| **Inbound THB Deposit** | **Free** (PromptPay / Bank Transfer) | Cash funding | Instant deposit via KKP Mobile / Thai QR. |

---

## 3. Dime Club Level 1 Free Trade Day (2026 Promotion Audit)

### 3.1 Promotional Specification & Valid Constraints
- **Eligibility:** Dime Club Level 1 members.
- **Published Calendar Horizon:** Official published schedule is verified **through 30 September 2026**.
  > *Rule:* Do **not** assume that Free Trade Day automatically occurs on the 15th and 30th of every month indefinitely. It must be modeled as a dynamic, timestamped broker promotion calendar requiring recurring verification.
- **Eligible Trading Hours (US Market):** Strictly **22:00 – 23:50 Thailand Time (ICT)**.
- **Eligible Products:** US Equities and ETFs.
- **Eligible Order Type:** **BUY orders only** executed as **Market Orders** specified by monetary amount (Amount-based order). Limit orders and share-quantity orders are excluded.
- **Eligible Funding Currency:**
  - Funded in **THB amount** (instant FX conversion at broker rate).
  - Funded in **USD amount from Dime! FCD**.

### 3.2 Source Conflicts Preserved

#### A. `DIME_FCD_VS_DIME_USD` Conflict:
- The Dime Club Level 1 terms explicitly allow USD funding via "Dime! FCD".
- Conversely, promotional fine print in campaign materials (e.g. Payday September 2026) states: *"Transactions funded via Dime! USD are excluded from campaign benefits."*
- **Reconciliation Status:** `NEEDS_PRIMARY_SOURCE_RECONCILIATION`. The system preserves both wallet designations without assuming equivalence.

#### B. `DIME_CAT_FEE` Conflict:
- Published official help documentation reflects conflicting CAT fee rates across versions (some showing $0.0000X/share, others omitting it or incorporating it into pass-through regulatory fees).
- **Reconciliation Status:** `SOURCE_CONFLICT`. Handled dynamically via configurable parameters in the execution cost model.

---

## 4. Total Friction Waterfall Model

In ACASH, **commission-free does not mean friction-free**. The total expected friction $\Phi_{\text{total}}$ of an execution comprises:

$$\Phi_{\text{total}} = \text{Commission} + \text{VAT} + \text{SEC} + \text{TAF} + \text{CAT} + \text{Spread Drag} + \text{Slippage Drag} + \text{FX Drag} + \text{Timing Cost}$$

### Friction Component Breakdown:
1. **Spread & Market Impact Drag:** Market orders executed during the 22:00–23:50 ICT window incur bid-ask spread crossing. For liquid ETFs (`VOO`, `QQQM`), spread drag is minimal (~1–2 bps); for smaller-cap thematic holdings (`SATL`, `SIDU`), spread drag can exceed 50–100 bps.
2. **FX Conversion Drag:** Funding trades via THB incurs an embedded currency conversion spread (typically 10–25 bps from interbank mid-rate). Using pre-funded Dime! FCD balances eliminates recurring FX drag on individual trades.
3. **Opportunity & Timing Cost:** Delaying an accumulation purchase by 10 to 14 days solely to wait for a Free Trade Day exposes capital to market drift $\Delta P$. If expected upward trend or volatility drag exceeds the 0.15% commission savings ($1.50 on a $1,000 order), waiting is economically irrational.

---

## 5. Broker-Aware Execution Optimization Protocol

The PPDS allocator strictly separates:
- **WHAT TO BUY:** Derived purely from investment thesis, asset quality, valuation, and portfolio risk ceilings.
- **WHERE & WHEN TO EXECUTE:** Evaluated by the execution cost optimizer.

```text
               ┌──────────────────────────────┐
               │ Target Deployment Identified │
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │   Execution Cost Evaluator   │
               └──────────────┬───────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
[ Small Ticket (< $500) ]                 [ Large Ticket (> $2,000) ]
- 0.15% commission = $0.75                - 0.15% commission = $3.00+
- Free Trade Day value: HIGH              - Timing drift risk > commission
- Recommendation: Utilize monthly         - Recommendation: Execute on
  free trade or Free Trade Day              favorable liquidity without delay
```

---

## 6. Verification Ledger

- Custodian Profile: DIME! (KKP) COMPLETE
- Promotional Calendar: BOUNDED TO 2026-09-30 (Dynamic)
- Source Conflicts Recorded: 2 (`DIME_FCD_VS_DIME_USD`, `DIME_CAT_FEE`)
- Friction Model: COMPREHENSIVE (9-component waterfall)
