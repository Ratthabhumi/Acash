# MEC-0015: Friction & Transaction Cost Contract

```text
[GOVERNANCE ARTIFACT: FRICTION AND TRANSACTION COST CONTRACT]
[GENERATED: 2026-09-20]
[UPDATED: 2026-09-21]
[CANONICAL STARTING HEAD: dd249d54e59c471bfdc98bc3c6d17781cbc2a08e]
[HYP_005: NOT CREATED]
[BACKTEST: NOT STARTED]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true]
```

---

## 1. Purpose

This document establishes the complete, pre-registered friction and transaction cost
contracts for **MEC-0015** that are frozen prior to `HYP_005` registration.
All parameters, schedules, and models are declared prior to observing any strategy results.

---

## 2. Literature Friction Model (RESOLVED — for Replication Reference Only)

The Zarattini, Aziz, Barbon (2024) paper and Concretum Group reference implementation
establish:

| Cost Component | Literature Value | Source | Status |
| :--- | :--- | :--- | :--- |
| Commission rate | `$0.0035 / share` | Concretum Reference Code | `RESOLVED` |
| Minimum commission ticket | `$0.35 / order` | Concretum Reference Code | `RESOLVED` |
| Slippage (text) | `$0.001 / share` | Paper prose only | `RESOLVED_PAPER_REPORTED_ONLY` |
| Slippage (code) | None standalone | Reference code inspection | `RESOLVED_NOT_IN_AUTHOR_CODE` |

**`LITERATURE_COMMISSION_MODEL = max($0.35, $0.0035 × shares)`**

---

## 3. Commission Model (RESOLVED — ACASH Baseline)

**`ACASH_COMMISSION_MODEL = LITERATURE_BASELINE_CONSERVATIVE`**

For the ACASH economic qualification baseline:
$$\text{Commission} = \max(\$0.35, \$0.0035 \times \text{shares}) \quad \text{per order execution side}$$

- Applied symmetrically to all buy and sell order executions.
- Eliminates any artificial zero-commission bias.

---

## 4. Spread Model (RESOLVED)

**`ACASH_SPREAD_MODEL = EMBEDDED_IN_NBBO_FILL`**

### 4.1. Execution Fill Mechanics
Orders are executed against the contemporaneous SIP National Best Bid and Offer (NBBO):
- Long entry / Short cover (BUY): fills at NBBO **Ask**.
- Short entry / Long exit (SELL): fills at NBBO **Bid**.

Because the quoted spread $(\text{Ask} - \text{Bid})$ is naturally captured by crossing the spread:
**`EXPLICIT_HALF_SPREAD_DEDUCTION_WITH_NBBO = PROHIBITED`**
Zero additional half-spread deduction may be applied, strictly preventing double-counting.

### 4.2. SEC Rule 612 Status
Under SEC Rule 612, US equities priced $> \$1.00$ have a minimum quotation increment of $\$0.01$. The SEC Rule 612 amendments introducing sub-penny tick categories have compliance delayed to **November 2026**. Historical backtests strictly use prevailing penny increments.

---

## 5. Slippage Model (RESOLVED)

**`BASELINE_STANDALONE_SLIPPAGE = $0.001/share` per executed side.**

To preserve the literature-reported adverse execution penalty without double-deducting spread:
- BUY: Execution price adjusted adversely to $\text{Ask} + \$0.001$.
- SELL: Execution price adjusted adversely to $\text{Bid} - \$0.001$.
- No negative or non-positive execution prices permitted.

---

## 6. Regulatory Fee Model (RESOLVED)

Regulatory fees are **time-varying** and follow exact historical effective-date schedules.
Calculation is implemented via pure Decimal arithmetic in `src/acash/execution/regulatory_fees.py`.

### 6.1. SEC Section 31 Fee
- Applies strictly to covered **SELL** transactions (equity/ETF).
- Zero fee on BUY transactions.
- Historical Schedule: `docs/research/manifests/MEC-0015-sec31-fee-schedule.json` (25 distinct rate tiers covering 2007-05-01 through 2024-04-30, sourced from official SEC Fee Rate Advisories).
- Pure function: `compute_sec31_fee(date, sale_principal)`.

### 6.2. FINRA Trading Activity Fee (TAF)
- Applies strictly to covered **SELL** transactions.
- Zero fee on BUY transactions.
- Historical Schedule: `docs/research/manifests/MEC-0015-finra-taf-fee-schedule.json` (5 distinct tiers covering 2007-05-01 through 2024-04-30 with per-trade caps, sourced from official FINRA Notices 04-70, 11-27, 12-06, 12-31).
- Pure function: `compute_finra_taf(date, shares_sold)`.

---

## 7. Short Borrow Contract (RESOLVED)

- **`SHORT_LOCATE_ASSUMPTION = SPY_AVAILABLE_UNLESS_PROVIDER_OR_BROKER_MARKS_UNAVAILABLE`**
- **`HISTORICAL_BORROW_RATE = UNOBSERVED`**
- **Baseline Borrow Cost:** `0 bps` (justified by SPY extreme liquidity and strictly intraday holding durations).
- **Mandatory Friction Stress:** `50 bps annualized`, pro-rated to actual intraday holding duration:
  $$\text{Borrow Stress Fee} = \text{Principal} \times 0.0050 \times \frac{\text{holding\_minutes}}{390 \times 252}$$
- Must be included in all 2× friction stress evaluations for short positions.
- Long-only substitution is strictly prohibited.

---

## 8. Complete Friction Stack & 2× Friction Stress Specification

### 8.1. Baseline Trade Leg Friction
$$\text{Cost Per Trade Leg} = \text{NBBO Spread Crossing} + \$0.001/\text{share Slippage} + \text{Commission} + \text{Regulatory Fees (sells only)}$$

### 8.2. 2× Friction Stress Test Specification
To stress-test economic survivability without double-subtracting the quoted spread:
1. Retain observed NBBO bid/ask fill.
2. Multiply all non-spread explicit transaction costs by 2.0:
   $$\text{Stressed Commission} = 2.0 \times \text{Commission}$$
   $$\text{Stressed Regulatory Fees} = 2.0 \times \text{Regulatory Fees}$$
3. Add an additional adverse slippage stress component equal to **one observed half-spread per side**:
   $$\text{Additional Adverse Slippage Stress} = \frac{\text{Ask} - \text{Bid}}{2} \times \text{shares}$$
4. For short positions: Add the pro-rated 50 bps annualized short borrow fee.

---

## 9. Friction Contracts Resolution Summary

| Contract Item | Status | Governing Specification |
| :--- | :--- | :--- |
| Baseline Commission | `RESOLVED` | $\max(\$0.35, \$0.0035 \times \text{shares})$ |
| Spread Model | `RESOLVED` | Embedded in NBBO fills (`Ask` for buy, `Bid` for sell) |
| Standalone Slippage | `RESOLVED` | $\$0.001/\text{share}$ adverse per side |
| SEC Section 31 Fee | `RESOLVED` | Pinned historical schedule (`MEC-0015-sec31-fee-schedule.json`) |
| FINRA TAF Fee | `RESOLVED` | Pinned historical schedule (`MEC-0015-finra-taf-fee-schedule.json`) |
| Short Borrow Baseline | `RESOLVED` | 0 bps baseline (SPY ETB locate assumed) |
| Short Borrow Stress | `RESOLVED` | 50 bps annualized pro-rated stress |
| 2× Friction Stress Formula | `RESOLVED` | Retain NBBO + $2\times$ explicit costs + half-spread adverse + short stress |

**TOTAL REMAINING OPEN FRICTION BLOCKERS: 0**
