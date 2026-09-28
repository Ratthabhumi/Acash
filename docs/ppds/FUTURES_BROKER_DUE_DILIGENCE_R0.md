# ACASH Futures Broker Due Diligence R0 (CME Micro Contracts)

**Document:** `docs/ppds/FUTURES_BROKER_DUE_DILIGENCE_R0.md`
**System Module:** Broker Selection & Derivatives Infrastructure
**Target Book:** Futures / Macro Trading Book
**Stage:** R0 Due Diligence Matrix
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 1, 6, 8

---

## 1. Executive Summary & Selection Methodology

The **Futures / Macro Trading Book** evaluates broker candidates providing access to centrally cleared exchange-traded derivatives on the Chicago Mercantile Exchange (CME Group).

### Core Selection Axioms:
1. **Intraday Margin $\neq$ Economic Risk:** Position sizing must never be governed by broker intraday margin requirements (e.g. $50 or $100 retail day margin). Risk sizing is governed strictly by dollar loss at stop-loss invalidation. Margins are volatile external parameters determined by broker risk desks and exchange clearing houses.
2. **Thai Resident Eligibility is a Hard Prerequisite:** A broker offering low commissions or flexible APIs is unusable if onboarding of Thai residents cannot be verified by primary-source compliance documentation.
3. **Shadow-First Economics:** ACASH operates in simulation and shadow telemetry modes prior to live capital allocation. Pricing models that require recurring monthly fees or mandatory live-funded minimums for API telemetry require explicit cost budgeting.

---

## 2. Comparative Due-Diligence Matrix

| Due-Diligence Dimension | NinjaTrader / Tradovate | Interactive Brokers (IBKR) | Ironbeam | AMP Futures |
| :--- | :--- | :--- | :--- | :--- |
| **Thai Resident Eligibility** | **NOT_CONFIRMED** (Accepts select foreign clients; Thailand is not documented on an explicit public whitelist). | **CONFIRMED** (Thailand explicitly listed in official supported country directory). | **PARTIAL** (Accepts select foreign nationals; Thai individual KYC evaluated case-by-case). | **ELIGIBLE_TO_APPLY_SUBJECT_TO_COMPLIANCE** (Thailand not on published restricted list; subject to KYC approval). |
| **Regulatory Registration** | CFTC registered FCM; NFA ID `0309379`. | CFTC registered FCM, SEC registered BD; NFA ID `0001925`. | CFTC registered FCM; NFA ID `0265382`. | CFTC registered FCM; NFA ID `0412490`. |
| **Micro Commission (Base)** | $0.39 / side (Standard Plan) or $0.09 (Lifetime License) + exchange/NFA fees. | $0.25 / contract (Tiered $\le 1,000$ contracts) + exchange/regulatory/clearing fees. | $0.49 / side (Standard Plan) or tiered volume rates. | $0.30 - $0.40 / side depending on selected clearing route. |
| **All-In Micro Round-Turn** | `ALL_IN_COST = NOT_NORMALIZED` (Dependent on contract, data tier, routing, and membership). | `ALL_IN_COST = NOT_NORMALIZED` (Dependent on contract, tiered volume, and exchange pass-through). | `ALL_IN_COST = NOT_NORMALIZED` (Varies with volume and data feed). | `ALL_IN_COST = NOT_NORMALIZED` (Varies by clearing route: CQG, Rithmic, TT). |
| **Intraday Margin Status** | `VOLATILE_EXTERNAL_PARAMETER` (Retail day margins subject to unannounced revision). | `VOLATILE_EXTERNAL_PARAMETER` (Standard exchange margins or broker intraday maintenance policy). | `VOLATILE_EXTERNAL_PARAMETER` (Subject to FCM intraday risk policy). | `VOLATILE_EXTERNAL_PARAMETER` (Subject to FCM intraday risk policy). |
| **API & Telemetry Architecture** | Tradovate REST / WebSocket API + NinjaTrader SDK. | IBKR Client Portal Web API / TWS Socket API. Documented request pacing. | Dedicated Ironbeam API. | Third-party routing bridges (CQG Web API, Rithmic R|API+). |
| **API Commercial Cost** | **FUNDED ACCOUNT REQUIRED:** Requires live funded account (> $1,000 equity), API Access add-on, and API key. | No direct API access subscription fee for standard accounts; subject to pacing, auth, and market data costs. | Developer API fee (~$249/mo unless volume quota reached); simulation fee (~$99/mo). | Varies by routing bridge (data and platform add-on fees). |
| **Customer Risk Controls** | Trailing drawdown and daily loss lockouts configurable in platform. | Native portfolio margin, account-level liquidation triggers, order presets. | FCM-level risk liquidation engine. | **RESTRICTIVE:** Individual accounts cannot configure custom daily loss limits in portal; fixed defaults apply. |
| **TradingView Support** | Supported via Tradovate broker integration. | Supported via IBKR broker integration. | Supported via third-party bridges. | Supported via CQG routing bridge. |
| **Funding Rails (Thailand)** | International Bank Wire (USD). | International Bank Wire (USD), Wise integration. `IBKR_LOCAL_THAI_BANK_RAIL = NOT_CONFIRMED`. | International Bank Wire (USD). | International Bank Wire (USD). |

---

## 3. Futures Cost & Margin Normalization Standards

### 3.1 All-In Transaction Cost Normalization Standard
Because published marketing figures aggregate dissimilar fee schedules across varying plans, `ALL_IN_COST = NOT_NORMALIZED`. A future rigorous comparison requires evaluating identical standardized trades under contemporaneous schedules:

```text
Standardized 1-Round-Trip Comparison Template (Single Contract):
- Instrument: [1 MES | 1 MNQ | 1 MGC | 1 MCL | 1 M6E]
- Components:
  + Broker Commission (Buy + Sell)
  + CME Exchange Fee (Buy + Sell)
  + CME Clearing Fee (Buy + Sell)
  + NFA Regulatory Fee ($0.02 / contract side => $0.04 round trip)
  + Order Routing / Platform Transaction Fee
  + Contemporaneous Monthly Fixed Costs (Market Data, API access amortized over N trades)
- Effective Date Context & Plan Tier
```

### 3.2 Margin Normalization Standard
Broker intraday margins are volatile operational parameters set at broker discretion and do not represent exchange legal minimums:
- **Exchange Maintenance Margin:** Established by CME Clearing (SPAN / CME CORE margin models) based on market volatility.
- **Broker Day Trading Margin:** Promotional or risk-desk intraday leverage parameter that can be modified or revoked during volatility events without prior notice.
- **Rule:** `VOLATILE_EXTERNAL_PARAMETER`. ACASH never sizes positions or computes capital adequacy using broker intraday margins.

---

## 4. Deep-Dive Candidate Evaluations

### 4.1 Candidate Alpha: Interactive Brokers (IBKR)
- **Documented Properties:**
  - Thai resident eligibility confirmed via official country directory.
  - Base micro commission published at USD 0.25/contract (Tiered schedule) + exchange/clearing pass-through.
  - Multi-currency accounts with international bank wire and official Wise integration. Local Thai commercial bank direct partner rails are `NOT_CONFIRMED` by primary source.
  - API connectivity provided via Client Portal Web API (local gateway daemon required, interactive browser login) and TWS Socket API.
- **API Architecture & Constraints:**
  - Web API historical market data throttled to 10 req/s or 50 req/min. TWS API subject to pacing lines.
  - OAuth 2.0 direct API documented primarily for institutional/advisory entities, not standard retail accounts.
- **Classification:** `LEADING_CANDIDATE` (Subject to operator review; zero capital authorized).

### 4.2 Candidate Beta: NinjaTrader / Tradovate
- **Documented Properties:**
  - Modern REST/WebSocket telemetry natively integrated with TradingView.
  - Official retail API documentation requires a live funded account (> USD 1,000 equity) and active API Access subscription.
  - Primary-source whitelist confirmation for Thai resident onboarding remains unverified (`THAI_RESIDENT_NINJATRADER = NOT_CONFIRMED`).
- **Classification:** `CANDIDATE_ON_HOLD` pending primary-source Thai KYC verification and live-account API cost trade-off evaluation.

### 4.3 Candidate Gamma: Ironbeam
- **Documented Properties:** Registered FCM with proprietary API; developer API model imposes ~$249/mo fee for accounts not meeting high monthly volume thresholds.
- **Classification:** `REDUCED_FIT_CANDIDATE` due to commercial developer API friction during low-turnover research phases.

### 4.4 Candidate Delta: AMP Futures
- **Documented Properties:**
  - Thailand is not listed on AMP's published restricted countries list (`THAI_RESIDENT_AMP = ELIGIBLE_TO_APPLY_SUBJECT_TO_COMPLIANCE`).
  - Risk management policy strictly limits user-configurable account loss controls in portal.
- **Classification:** `REDUCED_FIT_CANDIDATE` due to restricted programmatic risk boundaries.

---

## 5. Candidate Status & Governance Boundaries

```text
GOVERNANCE INVARIANT:
FUTURES_BROKER = CANDIDATE_IDENTIFIED
IBKR = LEADING_CANDIDATE
THAI_RESIDENT_NINJATRADER = NOT_CONFIRMED
THAI_RESIDENT_AMP = ELIGIBLE_TO_APPLY_SUBJECT_TO_COMPLIANCE
IBKR_LOCAL_THAI_BANK_RAIL = NOT_CONFIRMED
ALL_IN_COST = NOT_NORMALIZED
MARGIN_STATUS = VOLATILE_EXTERNAL_PARAMETER
CAPITAL_AUTHORITY = $0.00
NO_REAL_ORDERS = true
```

No broker contract is executed, no account is opened, and no credentials exist.

---

## 6. Verification Ledger

- Candidate Matrix Completed: 4 US FCMs audited (IBKR, Tradovate, Ironbeam, AMP)
- Thai Residency Audit: IBKR (`CONFIRMED`) | NinjaTrader (`NOT_CONFIRMED`) | AMP (`ELIGIBLE_TO_APPLY_SUBJECT_TO_COMPLIANCE`)
- Tradovate Retail API: Live funded account (> $1,000 equity) + paid subscription required
- IBKR Pacing & Auth: Web API gateway pacing verified; local Thai bank rail unconfirmed
- Cost Normalization: `ALL_IN_COST = NOT_NORMALIZED` (Template established)
- Margin Discipline: Sizing strictly decoupled from volatile broker day margin
- Final Candidate Status: `FUTURES_BROKER = CANDIDATE_IDENTIFIED`
