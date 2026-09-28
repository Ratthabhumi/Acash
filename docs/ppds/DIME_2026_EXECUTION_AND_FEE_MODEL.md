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
| **SEC Section 31 Fee** | **0.00206%** ($20.60 per $1M covered sales) | **SELL orders only** | Pass-through US regulatory fee. Statutory rate effective 2026-04-04 (SEC Fee Rate Advisory FY2026). Confirmed on Dime official schedule. |
| **FINRA TAF Fee** | **Date-Effective Schedule** (See § 2.1) | **SELL orders only** | **2026-01-01 .. 2026-09-30:** $0.000195/share (max $9.79/trade).<br>**2026-10-01 .. 2026-12-31:** **$0.00** (Temporary pause under SR-FINRA-2026-021). |
| **CAT Regulatory Fee** | Variable / Inconsistent across pages | Per-transaction / per-share | **SOURCE CONFLICT (See § 3.2)**: Observed $0.000046/share vs $0.000003/share. Configurable parameter. |
| **W-8BEN Treaty Benefit** | **15.0%** dividend withholding ceiling | US Cash Distributions | Form W-8BEN establishes foreign beneficial-owner status to claim treaty benefit under US–Thailand DTA Art. 10 (subject to eligibility). |
| **Account Maintenance Fee** | **$0.00** / Free | Account custody | No monthly or annual account holding fee. |
| **Inbound THB Deposit** | **Free** (PromptPay / Bank Transfer) | Cash funding | Instant deposit via KKP Mobile / Thai QR. |


### 2.1 Regulatory Fee Lineage & Date-Effective Schedules (SEC, FINRA TAF)

Regulatory fees on covered US equity sell orders are dynamic statutory pass-throughs and must not be modeled as timeless constants:

1. **SEC Section 31 Fee:**
   - **Authority:** SEC Fee Rate Advisory for Fiscal Year 2026 (Order 2026-2).
   - **Statutory Rate:** **USD 20.60 per USD 1,000,000** of covered sales (**0.00206%** or $0.0000206 per dollar of gross sales proceeds), effective **2026-04-04**.
   - **Broker Schedule:** Dime!'s current official US stock fee schedule confirms pass-through SEC Fee = 0.00206% of sell value. Stale FY2025 rates (~0.00278%) are superseded.

2. **FINRA Trading Activity Fee (TAF):**
   - **Date-Effective Policy Model:**
     - **2026-01-01 through 2026-09-30:** Standard 2026 equity TAF rate of **$0.000195 per share** sold, with a maximum cap of **$9.79 per trade** (rounded up to the nearest cent). Confirmed on Dime! official rate disclosures.
     - **2026-10-01 through 2026-12-31:** **$0.00 / share (Rate = 0)**.
       - *Regulatory Authority:* SEC Release No. 34-106409; File No. SR-FINRA-2026-021 (filed 2026-09-15, published 2026-09-18, designated immediately effective).
       - *Policy Scope:* FINRA temporarily paused the assessment of TAF on covered equity transactions from 2026-10-01 through 2026-12-31 inclusive.
     - **Post-2026-12-31:** Requires new regulatory determination. Do not extrapolate beyond 2026-12-31 without a ratified SRO/SEC filing. Classified as `VOLATILE`.

### 2.2 Dime Club 2026 Dynamic Sliding Commission Model

Broker commission is **account-specific, dynamic, promotion-aware, and effective-dated** (`ACCOUNT_SPECIFIC + EFFECTIVE_DATED + PROMOTION_AWARE`), not a static 0.15% constant:

- **Authority:** Dime! Official Campaign Terms ("Sliding Commission / Dime Club", published 2026).
- **Mechanics:** For Dime Club members, cumulative monthly trading value in month $T$ determines the US stock **BUY commission** applied in month $T+1$:
  - **Tier 1 ($\le$ THB 5,000,000):** BUY Commission = **0.15%**
  - **Tier 2 (THB 5,000,001 – 20,000,000):** BUY Commission = **0.10%**
  - **Tier 3 (> THB 20,000,000):** BUY Commission = **0.05%**
- **Sell Orders:** US stock SELL commission remains statutory **0.15%** across all volume tiers.
- **Validity Horizon:** The current campaign schedule covers qualification periods through November 2026 and fee benefit execution through **December 2026**.
- **Portfolio Context:** For the operator's current observed portfolio scale (~THB 100k), the baseline tier (0.15%) applies unless verified account records prove higher cumulative volume. The cost engine must enforce:
  ```text
  DIME_EFFECTIVE_COMMISSION_RATE = ACCOUNT_STATE_REQUIRED
  ```
- **Distinct Execution Mechanisms Preserved:**
  1. *Monthly Free Trade:* First trade of each calendar month is commission-free (0.00%).
  2. *Dime Club Level 1 Free Trade Day:* Pre-scheduled promotional BUY windows (0.00% commission).
  3. *Sliding Commission:* Volume-tiered baseline BUY commission (0.05% – 0.15%).

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

### 3.2 Account Architecture & Sourced Disclosures

#### A. `DIME_FCD_VS_DIME_USD` (Resolved Distinct Products):
- **Primary Source:** Dime! Official Product Portal (`https://dime.co.th/save/dime-fcd`, retrieved 2026-09-28).
- **Product Distinction:**
  - **Dime! FCD - USD:** A Foreign Currency Deposit (FCD) bank account with Kiatnakin Phatra Bank (KKP) that can accrue deposit interest and holds USD cash usable across US stocks, US options, and gold investments.
  - **Dime! USD:** An investment trading cash wallet designated specifically for US stock and options transactions.
- **Resolution:** Because these are distinct legal and operational account products, the observation that one campaign (e.g. Free Trade Day) permits Dime! FCD while another campaign (e.g. Payday) excludes Dime! USD is **not a source conflict**. Each campaign establishes its own explicit product eligibility.
- **Status:**
  ```text
  DIME_FCD_VS_DIME_USD = RESOLVED_DISTINCT_PRODUCTS
  ```

#### B. `DIME_CAT_FEE` (Source Conflict Preserved):
- Published official Dime! documentation reflects irreconcilable CAT fee rates across active pages retrieved 2026-09-28:
  - Official Page Rendering 1: **$0.000046 per share**.
  - Official Page Rendering 2: **$0.000003 per share**.
- **Reconciliation Status:** `SOURCE_CONFLICT`. Handled dynamically via an effective-dated, configurable parameter in the execution cost model rather than silently selecting an arbitrary value.

---

## 4. Total Friction Waterfall Model

In ACASH, **commission-free does not mean friction-free**. The total expected friction $\Phi_{\text{total}}$ of an execution comprises:

$$\Phi_{\text{total}} = \text{Commission} + \text{VAT} + \text{SEC} + \text{TAF} + \text{CAT} + \text{Spread Drag} + \text{Slippage Drag} + \text{FX Drag} + \text{Timing Cost}$$

### Friction Component Breakdown & Modeling Status:
1. **Commission & Regulatory Fees (Calibrated):** Contractually determined by account tier, monthly free-trade status, promotional window, SEC Section 31 rate (0.00206%), date-effective TAF schedule, and configurable CAT fee.
2. **Spread & Market Impact Drag (`MODEL_ASSUMPTION_NOT_CALIBRATED`):** Bid-ask spread and market impact vary by security liquidity, market session, order size, and contemporaneous quote depth. Quantitative estimates (e.g. 1–2 bps on index ETFs, 50–100 bps on small-cap thematic equities) are working design hypotheses and must not be treated as calibrated broker-contract invariants without empirical quote-book logging.
3. **FX Conversion Drag (`MODEL_ASSUMPTION_NOT_CALIBRATED`):** THB-to-USD conversion spreads depend on time-of-day bank counter spreads and broker FX markup. Maintaining pre-funded FCD balances mitigates recurring per-trade conversion spread.
4. **Opportunity & Timing Cost (`MODEL_ASSUMPTION_NOT_CALIBRATED`):** Delaying accumulation purchases solely to capture promotional commission savings exposes capital to market drift $\Delta P$. ACASH does not accelerate or delay trade recommendations based on uncalibrated heuristic trend forecasts.

> **OPTIMIZER DESIGN PRINCIPLE:**
> Expected execution friction requires: observed contemporaneous bid/ask, order size, prevailing liquidity, verified commission tier, statutory regulatory fees, actual quoted FX, execution delay horizon, and an empirically validated timing-cost model. No execution recommendation is authorized.

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
- Commission savings meaningful            - Timing drift risk > commission
- Consider monthly free trade             - Prioritize contemporaneous
  or verified promotional window            liquidity and minimal slippage
```

---

## 6. Verification Ledger

- Custodian Profile: DIME! (KKP) COMPLETE
- SEC Section 31 Rate: 0.00206% (statutory effective 2026-04-04)
- FINRA TAF Rate: DATE-EFFECTIVE ($0.000195/share max $9.79 through 2026-09-30; $0.00 through 2026-12-31 per SR-FINRA-2026-021)
- Commission Architecture: `ACCOUNT_SPECIFIC + EFFECTIVE_DATED + PROMOTION_AWARE` (Sliding Commission verified through Dec 2026)
- Product Distinction: `DIME_FCD_VS_DIME_USD = RESOLVED_DISTINCT_PRODUCTS`
- Source Conflicts Recorded: 1 (`DIME_CAT_FEE`: $0.000046 vs $0.000003)
- Friction Model: COMPREHENSIVE (Demoted uncalibrated spread/FX precision to `MODEL_ASSUMPTION_NOT_CALIBRATED`)
