# ACASH Futures Instrument Universe Specification R0 (CME Micro Contracts)

**Document:** `docs/ppds/FUTURES_INSTRUMENT_UNIVERSE_R0.md`
**System Module:** Derivatives Product Specifications & Contract Lineage
**Exchange Authority:** Chicago Mercantile Exchange Group (CME, CBOT, NYMEX, COMEX)
**Stage:** R0 Technical Contract Specification
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 2, 6, 7

---

## 1. Executive Summary & Product Selection Rationale

The candidate **Futures / Macro Trading Book** evaluates centrally cleared, exchange-traded futures contracts governed by the rules of the CME Group.

### Primary Selection Axioms:
1. **Exchange-Traded Futures vs Bilateral OTC / CFDs:**
   - **CME Futures:** Standardized exchange contracts, centrally cleared via CME Clearing, with transparent public rulebooks, centralized order book depth on CME Globex, CFTC/NFA regulatory oversight, and statutory customer-fund segregation rules where applicable. Central clearing mitigates bilateral counterparty risk, though broker/FCM operational, solvency, and custody risks remain non-zero.
   - **Bilateral CFDs / OTC:** Over-the-counter contracts between trader and broker where contract specifications, margin requirements, spread mechanics, execution policies, and overnight funding rates are determined bilaterally by the issuer under their governing jurisdiction.
   - **ACASH Architectural Decision:** ACASH selects CME exchange futures because of **standardized contract lineage, centralized exchange audit data, and deterministic contract settlement and expiration semantics**, not due to sweeping claims regarding all CFD providers.
2. **Micro Contracts for Granular Sizing:**
   Standard full-size contracts (`NQ`, `ES`, `GC`, `CL`, `6E`) carry large notional exposures per contract, making risk budgeting and sizing granularly constrained for personal capital allocations. R0 candidate research focuses on **CME Micro Contracts**.

```text
Notional Formula:
Notional Value (t) = Current Futures Price (t) × Invariant Multiplier

Illustrative Snapshot (2026-09-28 CME prices for scale illustration only):
- CME E-mini Nasdaq-100 (NQ): Multiplier $20.00/pt | at ~20,000 pts => Notional ~$400,000 [ILLUSTRATIVE_SNAPSHOT]
- CME Micro E-mini Nasdaq-100 (MNQ): Multiplier $2.00/pt | at ~20,000 pts => Notional ~$40,000 (1/10th size) [ILLUSTRATIVE_SNAPSHOT]
```

---

## 2. CME Micro Contract Specifications (Primary CME Group Authority)

| Contract Symbol | Underlying Benchmark | Exchange Division | Contract Multiplier | Minimum Price Fluctuation (Tick) | Dollar Value Per Tick | Settlement Method (CME Rulebook) | Expiration / Termination Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`MNQ`** | Nasdaq-100 Index | **CME** | **$2.00** $\times$ Index | 0.25 Index pts | **$0.50** | **Financial (Cash)** | Quarterly (H, M, U, Z); cash settled on 3rd Friday of contract month |
| **`MES`** | S&P 500 Index | **CME** | **$5.00** $\times$ Index | 0.25 Index pts | **$1.25** | **Financial (Cash)** | Quarterly (H, M, U, Z); cash settled on 3rd Friday of contract month |
| **`MGC`** | Gold (Troy Ounces) | **COMEX** | **10** Troy Ounces | $0.10 / troy oz | **$1.00** | **Physical Delivery** | Bi-Monthly (G, J, M, Q, V, Z); delivery via COMEX-approved depositories |
| **`MCL`** | WTI Crude Oil | **NYMEX** | **100** Barrels | $0.01 / barrel | **$1.00** | **Financial (Cash)** | Monthly (All 12 months); cash settled against NYMEX Light Sweet Crude Oil |
| **`M6E`** | Euro / US Dollar | **CME** | **12,500** EUR | $0.0001 / EUR | **$1.25** | **Physical Delivery** | Quarterly (H, M, U, Z); trading terminates 9:16 AM CT 2nd business day prior to 3rd Wednesday; delivery on 3rd Wednesday |

---

## 3. Physical Delivery Boundaries: Exchange Law vs ACASH Safety Policy

Retail algorithmic accounts must never take or make physical delivery of underlying commodities or foreign currencies.

### Critical Demarcation:
1. **Exchange Rules (CME / COMEX / NYMEX Law):**
   - **`MCL` (NYMEX Micro WTI):** Financially (cash) settled. There is no physical delivery obligation at NYMEX contract maturity.
   - **`MGC` (COMEX Micro Gold):** Physically deliverable. Trading terminates on the third to last business day of the delivery month. First Notice Day (FND) occurs on the last business day of the month preceding the delivery month.
   - **`M6E` (CME Micro EUR/USD):** Deliverable currency contract. Trading terminates at 9:16 AM CT on the second business day immediately preceding the third Wednesday of the contract month. Delivery occurs on the third Wednesday. There is no commodity-style First Notice Day.
2. **ACASH Proposed Safety Buffer Policy (`DELIVERY_RISK_BUFFER_POLICY = UNRATIFIED`):**
   - To eliminate delivery risks, ACASH requires a software-enforced liquidation or roll buffer prior to any exchange delivery cutoff.
   - *Candidate Policy:* Liquidate or roll positions $N$ business days before First Notice Day (for COMEX physical metals) or $N$ business days before trading termination (for deliverable FX).
   - *Status:* The specific buffer window (e.g., 3 business days vs FCM-specific liquidation schedule) is a **CANDIDATE_SAFETY_POLICY**, not an exchange rule. FCMs enforce their own auto-liquidation deadlines (often earlier than exchange FND).

---

## 4. Market Structure Comparison: CME Futures vs Retail OTC / CFDs

| Dimension | CME Exchange Micro Futures (`MNQ`, `MES`, `MGC`, `MCL`, `M6E`) | Retail Broker CFD / OTC Products |
| :--- | :--- | :--- |
| **Contract Standardization** | Standardized exchange contract terms established by CME/COMEX/NYMEX rulebooks. | Bilateral contracts defined by individual broker product agreements. |
| **Clearing & Counterparty** | Centrally cleared by CME Clearing. Bilateral counterparty risk mitigated; broker/FCM solvency and operational risks remain. | Direct counterparty risk to issuing broker entity (internal dealing desk, STP, or hybrid B-book). |
| **Order Book & Price Formation** | Central limit order book (CME Globex). Visible Level 2/Level 3 market data. | Synthetic quote feed constructed by issuing broker from liquidity providers. |
| **Execution Mechanics** | Explicit exchange match engine; FIFO or pro-rata matching algorithms. | Broker-controlled execution; spreads and slippage subject to broker execution policy. |
| **Financing / Carry Costs** | Cost of carry explicitly priced into futures basis; no independent swap rate schedule. | Daily overnight financing / rollover debit/credit rates applied by broker. |
| **Regulatory Supervision** | US CFTC / NFA oversight; mandatory customer segregated fund requirements (17 CFR § 1.20). | Varies by issuing broker license jurisdiction (FCA, ASIC, CySEC, FSA, etc.). |

---

## 5. Contract Expiration & Rollover Policy

Futures contracts expire on fixed calendar schedules. Continuous analytical research series require deterministic rollover logic.

1. **Exchange Expiration Schedule:**
   - Equity index micros (`MNQ`, `MES`): March (H), June (M), September (U), December (Z).
   - Micro Energy (`MCL`): Monthly expiration calendar per NYMEX rules.
   - Micro Metals (`MGC`): Bi-monthly cycle per COMEX rules.
   - Micro FX (`M6E`): Quarterly cycle per CME rules.
2. **Roll Timing Convention vs Policy:**
   - *Market Convention:* Equity index market volume and open interest frequently transition toward the deferred month around the second Thursday of the expiration month. This is an **observed market convention**, not an exchange rule.
   - *ACASH Policy:* `FUTURES_CONTINUOUS_ROLL_POLICY = UNRESOLVED`. Production backtests must pre-register an explicit, deterministic roll rule (e.g., fixed calendar cutoff, volume/open-interest crossover threshold, or days-to-maturity trigger).
3. **Continuous Synthetic Lineage:**
   - Historical continuous series (Panama back-adjustment, ratio stitching, or unadjusted perpetuals) are analytical artifacts.
   - *Contract Invariant:* Continuous synthetic price series must **never** be substituted for raw contract order execution. Raw contract tick and bar lineage must remain auditable.

---

## 6. Verification Ledger

- **Specifications Authority:** Primary CME Group Rulebooks (CME, COMEX, NYMEX)
- **Settlement Method Verified:**
  - `MNQ`: Financial (Cash)
  - `MES`: Financial (Cash)
  - `MCL`: Financial (Cash) [NYMEX Cash Settlement]
  - `MGC`: Physical Delivery (COMEX depositories)
  - `M6E`: Deliverable Currency (CME FX delivery schedule)
- **Delivery Risk Buffer:** `DELIVERY_RISK_BUFFER_POLICY = UNRATIFIED` (candidate operator safety buffer, not exchange law)
- **Roll Policy:** `FUTURES_CONTINUOUS_ROLL_POLICY = UNRESOLVED` (requires deterministic pre-registered rule)
- **Sizing Invariant:** Fixed contract multiplier ($2/pt, $5/pt, 10 oz, 100 bbl, 12,500 EUR); notional is price-dependent snapshot
