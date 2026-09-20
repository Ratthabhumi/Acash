# MEC-0015: Friction & Transaction Cost Contract

```text
[GOVERNANCE ARTIFACT: FRICTION AND TRANSACTION COST CONTRACT]
[GENERATED: 2026-09-20]
[CANONICAL HEAD: 5b09ccadeccbc250a88f881b80b2845d5c2f7ec9]
[HYP_005: NOT CREATED]
[BACKTEST: NOT STARTED]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true]
```

---

## 1. Purpose

This document establishes the complete, pre-registered friction and transaction cost
contracts for **MEC-0015** that must be frozen before `HYP_005` is registered.
All thresholds are declared prior to observing any strategy results.

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

> [!IMPORTANT]
> These are the **literature baseline** friction parameters. They represent the minimum
> cost model necessary to reproduce published results. They are **insufficient** for ACASH
> economic qualification, which requires an independent, conservative model.

---

## 3. Commission Model (RESOLVED — ACASH Baseline)

**`ACASH_COMMISSION_MODEL = LITERATURE_BASELINE_CONSERVATIVE`**

For the ACASH economic qualification baseline, adopt the literature commission as the
conservative minimum:
$$\text{Commission} = \max(\$0.35, \$0.0035 \times \text{shares}) \quad \text{per order execution side}$$

Rationale:
- Prevents granting an artificial zero-commission advantage.
- Equivalent to Interactive Brokers' tiered commission for retail-size orders.
- May be upgraded prospectively via a separate broker qualification.

---

## 4. Spread Model (OPEN_BLOCKER)

**`ACASH_SPREAD_MODEL = OPEN_BLOCKER`**

### 4.1. Terminology (Corrected)

Under SEC Rule 612, US equities priced above $\$1.00$ have a minimum quoting increment of $\$0.01$:
$$\text{One-tick full spread} = \$0.01 / \text{share}$$
$$\text{Half-spread (cost per share per trade side)} = \$0.005 / \text{share}$$

Claiming "$0.01 half-spread" is factually incorrect; it implies a $\$0.02$ full spread.

### 4.2. SEC Rule 612 Amendment Status

The SEC adopted amendments to Rule 612 creating sub-penny quote increments for qualifying NMS stocks.
As of September 2026, the compliance date is formally delayed to the **first business day of November 2026**.
No historical backtest may assume sub-penny quoting for pre-November 2026 data.

### 4.3. Model Options

| Model | Classification | Pros | Cons |
| :--- | :--- | :--- | :--- |
| NBBO Bid/Ask fills (buy at Ask, sell at Bid) | Preferred | Naturally incorporates contemporaneous spread | Requires Alpaca quote history qualification |
| Conservative fixed proxy ($0.01 full spread) | Fallback | Deterministic | Does not capture historical spread variation |

When using NBBO fills: **do NOT add a separate half-spread deduction** (mutual exclusivity rule).
When using Next-Minute-Open fills: a separate explicit spread cost MUST be added.

**`DOUBLE_COUNTING_PROHIBITION = ENFORCED`**

---

## 5. Slippage Model (OPEN)

| Classification | Value | Notes |
| :--- | :--- | :--- |
| `PAPER_REPORTED_SLIPPAGE` | `$0.001/share` | Paper text approximation only |
| `AUTHOR_REFERENCE_CODE_APPLIED_SLIPPAGE` | None standalone | Reference code does not apply this |
| `ACASH_SLIPPAGE_POLICY` | Embedded in spread model | No standalone deduction when using NBBO fills |

**`ACASH_SLIPPAGE_MODEL = OPEN`** (resolved when execution fill model is finalized).

---

## 6. Regulatory Fee Model (OPEN_BLOCKER)

Regulatory fees are **time-varying** and MUST use effective-date schedules.
Hardcoding contemporary rates into historical years is prohibited.

### 6.1. SEC Section 31 Fee

- Applies to: sell transactions only (equity and ETF).
- Calculation: `fee = principal_sold × applicable_rate`.
- Rates vary by fiscal year and SEC rule revision.
- `REGULATORY_FEE_HISTORICAL_SCHEDULE_SEC31 = OPEN_BLOCKER` (schedule must be sourced and pinned).

### 6.2. FINRA Trading Activity Fee (TAF)

- Applies to: covered equity sells and certain agency trades.
- Calculation: `fee = shares_sold × per_share_rate`, capped at per-trade maximum.

| Period | FINRA TAF Rate | Cap | Source |
| :--- | :--- | :--- | :--- |
| **2026 (effective from NOF-IMM-EFF-FINRA-2024-019)** | `$0.000195 / share` | `$9.79 / trade` | FINRA.org |
| **Prior years (2007–2025)** | `OPEN_BLOCKER` | `OPEN_BLOCKER` | Historical schedule required |

> [!CAUTION]
> The 2026 FINRA TAF rate of $0.000195/share with a $9.79 cap **cannot** be applied to
> historical years 2007–2025. Historical rates differ and must be sourced from FINRA
> archived Notice announcements.

**`ACASH_REGULATORY_FEE_MODEL = OPEN_BLOCKER`**

Until the complete historical effective-date schedule is sourced:
- No strategy execution is authorized under a regulatory fee model.
- Sensitivity analysis MUST be run to characterize regulatory fee impact.

---

## 7. Short Borrow Contract (PROVISIONALLY RESOLVED)

| Item | Status | Value |
| :--- | :--- | :--- |
| SPY borrow availability | `PROVISIONAL` | Generally Easy-To-Borrow (ETB) |
| Locate confirmation | `REQUIRED` | Must be confirmed before short orders |
| Hard-to-borrow override | `RESOLVED` | `FAIL_CLOSED_NO_SHORT` |
| Borrow fee | `OPEN` | Pro-rated intraday |
| Long-only substitution | `PROHIBITED` | Cannot silently substitute long-only when short unavailable |

**`SHORT_AVAILABILITY_MODEL = REQUIRED_LOCATE_CONFIRMATION`**
**`BORROW_FEE_STATUS = BORROW_COST_UNOBSERVED_SENSITIVITY_REQUIRED`**

If authoritative historical SPY borrow rates are unavailable:
- A conservative borrow-cost stress scenario must be included in the acceptance gate analysis.
- Sensitivity range: 0 bps to 50 bps annualized (pro-rated per holding minute).

---

## 8. Complete Friction Stack

When fully resolved, the ACASH MEC-0015 friction stack per trade leg:

$$\text{Total Cost Per Leg} = \text{Commission} + \text{Spread Cost} + \text{Regulatory Fees} + \text{Borrow Fee (shorts only)}$$

Where:
- Commission: $\max(\$0.35, \$0.0035 \times \text{shares})$
- Spread Cost: half-spread (if using next-minute-Open fills) OR embedded in bid/ask (if NBBO)
- Regulatory Fees: time-varying SEC Section 31 (sells) + FINRA TAF (sells), per effective-date schedule
- Borrow Fee: time-prorated daily borrow rate × intraday holding duration (shorts only)

> [!IMPORTANT]
> The $2\times$ friction stress test (Part O of the authorization) must also be applied to
> the complete friction stack, not only the commission component.

---

## 9. Anti-Overcounting Constraint

| Rule | Enforcement |
| :--- | :--- |
| Spread embedding + half-spread deduction | PROHIBITED (double-counting) |
| Commission-free execution assumption | PROHIBITED |
| Zero borrow fee without stress test | PROHIBITED |
| Contemporary rate retroactive application | PROHIBITED |

---

## 10. Open Blockers Summary

| Blocker | Blocks HYP_005? | Next Action |
| :--- | :--- | :--- |
| `ACASH_SPREAD_MODEL = OPEN_BLOCKER` | Yes | Qualify NBBO or ratify conservative proxy |
| `ACASH_REGULATORY_FEE_MODEL = OPEN_BLOCKER` | Yes | Source historical SEC/FINRA schedules |
| `ACASH_EXECUTION_FILL_PRICE_MODEL = OPEN` | Yes | Separate qualification probe |
| `BORROW_FEE_STATUS = OPEN (stress required)` | Partial | Sensitivity analysis required |
