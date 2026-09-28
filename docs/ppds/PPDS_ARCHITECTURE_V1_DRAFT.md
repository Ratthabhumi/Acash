# ACASH Personal Portfolio Decision Support (PPDS) Architecture V1 (Draft)

**Document:** `docs/ppds/PPDS_ARCHITECTURE_V1_DRAFT.md`
**System Module:** Capital Allocation & Portfolio Architecture
**Stage:** R0 Architectural Specification
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda)

---

## 1. Executive Summary & Architectural Philosophy

The **ACASH Personal Portfolio Decision Support (PPDS)** engine expands ACASH from an algorithmic research and backtesting framework into a sovereign, multi-book personal capital allocation system.

### Core Architectural Mandate
PPDS is explicitly **NOT**:
- An autonomous stock-picking machine making automated purchases.
- A black-box ML scoring system that forces 100% equity market exposure.
- A monolithic account viewer that blends high-risk tactical trading with long-term retirement compounding.

PPDS **IS**:
- A **Sovereign Capital Allocator**: Determines whether new savings/capital should remain as `CASH` or be deployed into specific, pre-authorized books.
- An **Evidence-Driven Decision Support System**: Delivers transparent, auditable decision surfaces (`BUY_CANDIDATE`, `HOLD`, `REDUCE_REVIEW`, `NO_ACTION`, `INSUFFICIENT_EVIDENCE`) requiring explicit human authorization.
- A **Centralized Multi-Broker Risk Engine**: Calculates look-through portfolio concentration, factor overlap, single-name limits, and economic loss ceilings across disparate custodians.
- A **Multi-Venue Reconciliation & Tax Evidence Ledger**: Preserves immutable, double-entry records of fills, dividends, fees, foreign exchange conversions, and remittances to support Thai tax reporting.

```text
                                 PERSONAL CAPITAL
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
          INVESTMENT BOOK                                 TRADING BOOK
     (Long-Horizon Compounding)                      (Asymmetric Alpha / Tactical)
                 │                                             │
      ┌──────────┼──────────┐                       ┌──────────┴──────────┐
      ▼          ▼          ▼                       ▼                     ▼
   Core/DCA  Satellite  Speculative          Equity Tactical       Futures/Macro
  (ETFs/Mkt) (Quality)  (Thematic)               (Sniper)             (CME Micros)
      │          │          │                       │                     │
      └──────────┼──────────┘                       │                     │
                 ▼                                  ▼                     ▼
            Dime! (KKP)                         Webull TH             Futures FCM
```

---

## 2. Decoupled Multi-Book Hierarchy

PPDS enforces a strict architectural and accounting firewall between **Investment** and **Trading**:

### 2.1 The Investment Book
- **Objective (`CANDIDATE_POLICY_UNRATIFIED`):** Generational wealth creation, broad risk-premia harvesting, and long-horizon compounding with minimal portfolio turnover.
- **Horizon (`CANDIDATE_POLICY_UNRATIFIED`):** 3 to 10+ years (subject to operator ratification).
- **Benchmark (`CANDIDATE_POLICY_UNRATIFIED`):** Broad market index (e.g. MSCI ACWI, S&P 500, or a blended 80/20 equity/bond benchmark).
- **Sub-Books & Illustrative Existing Holdings (`BOOK_ASSIGNMENT_UNRATIFIED`):**
  1. **Core / DCA:** Market-cap and factor index ETFs. Illustrative observed holdings: `VOO`, `QQQM` (`ILLUSTRATIVE_EXISTING_HOLDING`). Low turnover, scheduled accumulation, automated cash allocation rules.
  2. **Satellite / Conviction:** Focused corporate equity positions. Illustrative observed holdings: `TSM`, `PLTR`, `NOW` (`ILLUSTRATIVE_EXISTING_HOLDING`). Every allocation requires an explicit, audited investment thesis prior to formal book ratification.
  3. **Speculative / Thematic:** High-uncertainty emerging themes. Illustrative observed holdings: `RKLB`, `RDW`, `SATL` (`ILLUSTRATIVE_EXISTING_HOLDING`). Governed by a strict aggregate capital ceiling to prevent speculative drift.

### 2.2 The Trading Book
- **Objective & Strategy Authority:** The Trading Book may host only separately researched, validated, and formally authorized strategies. The system does not assume innate market edge. Current state:
  ```text
  NO_AUTHORIZED_TRADING_STRATEGY
  NO_TRADE
  ```
- **Horizon (`CANDIDATE_POLICY_UNRATIFIED`):** Intraday to several weeks.
- **Benchmark (`CANDIDATE_POLICY_UNRATIFIED`):** Cash hurdle rate (SOFR / Risk-Free Yield) or zero benchmark (absolute return).
- **Sub-Books:**
  1. **Equity Tactical / Sniper:** Event-driven equity catalysts and breakout setups. Candidate execution venue: Webull Thailand (API integration gated).
  2. **Futures / Macro:** Direct macro exposure hedging and directional trades utilizing regulated CME Micro contracts (`MNQ`, `MES`, `MGC`, `MCL`, `M6E`).

### 2.3 The Non-Negotiable Book Firewall
1. **Zero Automatic Capital Contagion:** Trading book losses must **never** automatically pull liquidity or collateral from the Investment Book.
2. **Explicit Transfer Governance:** Moving capital between Investment and Trading requires an explicit, audited operator instruction (`CapitalTransferEvent`).
3. **Decoupled P&L Attribution:** High returns or deep drawdowns in tactical trading must not distort the Time-Weighted Return (TWR) of the core DCA portfolio.

---

## 3. Decision Support State Machine

The PPDS evaluation engine operates cyclically or on-demand, ingesting multi-asset market data, fundamentals, and portfolio state to emit discrete recommendations:

```text
               ┌────────────────────────┐
               │ Multi-Factor Evaluation│
               └───────────┬────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│BUY_CANDIDATE │    │     HOLD     │    │REDUCE_REVIEW │
└──────┬───────┘    └──────────────┘    └──────┬───────┘
       │                                       │
       └───────────────────┬───────────────────┘
                           ▼
               ┌───────────────────────┐
               │ Human Operator Review │
               └───────────┬───────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
         [ AUTHORIZE ]            [ REJECT / DISCARD ]
              │                         │
              ▼                         ▼
      Manual / Staged             State Logs Intact
      Order Staging               (Zero Execution)
```

### State Semantics:
- **`BUY_CANDIDATE`:** Target asset satisfies all book-specific fundamental/quantitative gates, allocation drift is below ceiling, and cash is available. Emits a candidate deployment envelope (sizing, stop level, execution venue).
- **`HOLD`:** Position remains within acceptable thesis bounds and risk tolerances. Zero action recommended.
- **`REDUCE_REVIEW`:** Thesis drift, fundamental deterioration, extreme valuation extension, or portfolio concentration breach detected. Flags position for operator reassessment.
- **`NO_ACTION`:** Market or asset is in an indeterminate state; transaction costs exceed expected edge.
- **`INSUFFICIENT_EVIDENCE`:** Data contract incomplete, missing regulatory filings, or unverified corporate action. Fails closed to zero action.

> **CRITICAL INVARIANT:** Recommendations are **decision surfaces**, never automated execution orders. The system enters a terminal wait state until the human operator signs or dismisses the proposal.

---

## 4. Central Risk Engine & Look-Through Exposure

The PPDS Risk Engine maintains real-time consolidated oversight across all custodians:

### 4.1 Portfolio-Level Risk Guardrails
- **Single-Name Concentration Ceiling:** Aggregate direct exposure to any single non-ETF entity (across Core, Satellite, and Tactical) must not exceed a frozen threshold $\theta_{\text{single}}$.
- **ETF Look-Through Overlap:** Ingests ETF constituent holdings to detect hidden concentration (e.g. `QQQM` + `VOO` + individual holdings sharing high aggregate exposure to megacap tech).
- **Currency Risk:** Tracks aggregate USD exposure versus base THB net worth, flagging unhedged FX volatility.
- **Liquidity Buffer:** Enforces an uninvestable cash floor to satisfy personal emergency reserve policies.

### 4.2 Futures Risk Discipline
- Sizing for CME Micro contracts is calculated strictly from **Dollar Risk at Invalidation**:
  $$\text{Contracts} = \left\lfloor \frac{\text{Risk Budget (\USD)}}{\text{Stop Distance (Points)} \times \text{Multiplier (\USD/Point)} + \text{Friction}} \right\rfloor$$
- **Prohibition on Day-Margin Sizing:** Sizing must **never** be based on broker intraday margin requirements (e.g. $50 day margin). Low margin is leverage, not safety.

---

## 5. Broker Roles & Software Abstraction Layer

PPDS decouples portfolio decision logic from custodian execution APIs:
1. **Dime! Adapter:** Custodian for existing US long-term equities and FCD cash. Operates initially via statement ingestion and manual reconciliation.
2. **Webull Thailand Adapter:** Target candidate for Equity Tactical / Sniper book. Utilizes official HTTPS REST queries, gRPC trade event streaming, and WebSocket market data (read-only in R0; credential integration gated).
3. **Futures FCM Adapter:** Future interface to regulated CME clearing broker (IBKR / NinjaTrader candidate).

---

## 6. Verification Ledger

- Architecture Status: DRAFT SPECIFICATION (V1 Complete)
- Governance Separation: STRICT FIREWALL CODIFIED
- Decision Model: EVIDENCE-FIRST / HUMAN-IN-THE-LOOP
- Holdings Classification: `ILLUSTRATIVE_EXISTING_HOLDING` / `BOOK_ASSIGNMENT_UNRATIFIED`
- Trading Strategy Authority: `NO_AUTHORIZED_TRADING_STRATEGY` (NO_TRADE)
- Runtime Implementation Status: `NOT_AUTHORIZED / NOT_IMPLEMENTED`
- Execution Authority: STRICTLY $0.00 / NO REAL ORDERS
