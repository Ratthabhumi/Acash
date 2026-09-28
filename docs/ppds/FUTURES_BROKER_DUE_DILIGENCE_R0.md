# ACASH Futures Broker Due Diligence R0 (CME Micro Contracts)

**Document:** `docs/ppds/FUTURES_BROKER_DUE_DILIGENCE_R0.md`
**System Module:** Broker Selection & Derivatives Infrastructure
**Target Book:** Futures / Macro Trading Book
**Stage:** R0 Due Diligence Matrix
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 1, 6, 8

---

## 1. Executive Summary & Selection Philosophy

The **Futures / Macro Trading Book** requires access to regulated, centralized exchange-traded derivatives on the Chicago Mercantile Exchange (CME Group).

### Core Selection Axioms
1. **Low Margin $\neq$ Low Economic Risk:** Sizing positions based on broker intraday margin (e.g. $50 day margin on MNQ) is financial recklessness. Sizing is governed strictly by dollar loss at stop-loss invalidation.
2. **Thai Resident Eligibility is a Hard Prerequisite:** A broker offering the lowest commission or best API is completely disqualified if onboarding of Thai residents cannot be verified by primary-source compliance evidence.
3. **Shadow-First Economics:** ACASH develops in simulation/shadow mode prior to capital commitment. Broker pricing models that impose recurring monthly API access penalties on inactive or read-only accounts violate ACASH development economics.

---

## 2. Comparative Due-Diligence Matrix

| Due-Diligence Dimension | NinjaTrader / Tradovate | Interactive Brokers (IBKR) | Ironbeam | AMP Futures |
| :--- | :--- | :--- | :--- | :--- |
| **Thai Resident Eligibility** | **UNVERIFIED / NOT CONFIRMED** (Discloses foreign clients generally; no primary whitelist for Thailand). | **CONFIRMED** (Thailand explicitly listed in official supported country directory). | **PARTIAL** (Accepts select foreign nationals; individual Thai KYC case-by-case). | **CONFIRMED** (Broad international individual onboarding supported). |
| **Regulatory Standing** | CFTC registered FCM; NFA ID `0309379`. High custody security. | CFTC / SEC / FINRA / Global multi-jurisdiction giant. | CFTC registered FCM; NFA ID `0265382`. Long-standing US clearing broker. | CFTC registered FCM; NFA ID `0412490`. Dedicated retail futures broker. |
| **Micro Commission (Base)** | **$0.39 / side** (Free Plan) or $0.09 (Lifetime License) + fees. | **$0.25 / contract** (Tiered $\le 1,000$ contracts) + fees. | **$0.49 / side** (Standard) or tiered volume rates. | **$0.30 - $0.40 / side** depending on clearing route. |
| **All-In Micro Round-Turn** | ~$1.20 – $1.40 / contract (includes CME clearing & NFA). | ~$1.00 – $1.20 / contract (all-in pass-through). | ~$1.30 – $1.50 / contract. | ~$1.20 – $1.40 / contract. |
| **Intraday Margin (Micros)**| **~$50 / contract** (Aggressive retail day margin). | **Standard Exchange Margins** (or moderate intraday discount ~50% of initial). | **~$50 - $100 / contract** (Retail day margin). | **~$50 / contract** (Competitive day margin). |
| **API & Telemetry Quality** | Tradovate REST / WebSocket API + NinjaTrader SDK. Excellent. | IBKR Web API (Client Portal Gateway) / TWS API / IB Gateway. Subject to documented pacing. | Dedicated Ironbeam API. | Third-party routing APIs (CQG, Rithmic). |
| **API Commercial Cost** | **FUNDED ACCOUNT REQUIRED:** Official Tradovate API docs require LIVE account (> $1,000 equity), API Access subscription, and API key. No free retail dev API. | No separate API usage fee for supported accounts, but subject to auth, account, market-data entitlement, session, and pacing limits. | **PROHIBITIVE:** ~$249/mo developer API fee unless minimum trade quota met; $99 sim fee. Unattractive for shadow-first phase. | Varies by routing bridge (CQG/Rithmic data add-ons). |
| **Customer Risk Controls** | Robust broker-side trailing drawdown and daily loss lockouts. | Native portfolio margin, liquidation triggers, order presets. | Standard FCM risk liquidation engine. | **RESTRICTIVE:** Customers *cannot* set custom daily loss limits; fixed broker defaults apply. |
| **TradingView Support** | Native integration via Tradovate credential. | Native integration via IBKR broker login. | Supported through third-party bridges. | Native integration via CQG routing. |
| **Funding from Thailand** | International Bank Wire (USD). | International Wire, Local Thai Bank via partner rails, Wise integration. | International Bank Wire (USD). | International Bank Wire (USD). |

---

## 3. Deep-Dive Broker Candidate Evaluations

### 3.1 Candidate Alpha: Interactive Brokers (IBKR)
- **Strengths:**
  - Absolute certainty on Thai resident eligibility (Thailand on official primary country list).
  - Unmatched global financial strength and segregated customer asset protection.
  - Micro commission of **USD 0.25/contract** is the lowest base commission in the group.
  - No separate API access fee for ordinary supported account access (subject to account, market-data, and pacing constraints).
  - Established funding infrastructure from Thailand (direct Wise integration and swift wire routes).
- **API Architecture & Pacing Limits:**
  - **Pacing / Rate Limits:** Web API historical market data (`/iserver/marketdata/history`) is throttled to a maximum of 10 requests per second OR 50 requests per minute. TWS API has separate message pacing semantics based on account-provisioned Market Data Lines (including dynamic Lines / 2 models). Not unthrottled.
  - **Authentication Modes Must Be Distinguished:**
    - *Retail Web API:* Requires local execution of Client Portal Gateway (browser-based authentication, daily session reauthentication; does not support fully headless background login).
    - *OAuth 2.0 Direct API:* Allows direct calls to `api.ibkr.com` without Client Portal Gateway, but official documentation restricts OAuth 2.0 to licensed Organizations, Financial Advisors, and IBrokers (not generally provisioned for individual retail accounts).
    - *TWS API:* Socket API connecting via Trader Workstation (TWS) or IB Gateway (a lightweight daemon distinct from Client Portal Gateway).
- **Weaknesses:**
  - Intraday margin requirements are conservative (typically 50% of overnight initial margin, e.g. ~$1,000–$1,500 on equity micros vs $50 at specialty futures brokers).
  - Retail Web API requires the Client Portal Gateway process running locally with interactive browser authentication.
- **Verdict:** **LEADING_CANDIDATE** for institutional robustness, verified Thai residency, and API telemetry (pending human operator authorization; no capital authorized).

### 3.2 Candidate Beta: NinjaTrader / Tradovate
- **Strengths:**
  - Purpose-built for futures scalping and active intraday trading.
  - Ultralow day margins (~$50 on MNQ/MES).
  - Modern Tradovate REST/WebSocket API natively integrated with TradingView.
- **API Economics & Onboarding Friction:**
  - **Retail API Access Requirements:** Official Tradovate API documentation explicitly specifies that retail REST API access requires:
    1. A LIVE account (not demo-only).
    2. Minimum account equity greater than USD 1,000.
    3. Active subscription to API Access.
    4. Generation of an API Key.
    - ACASH cannot assume a free, un-funded developer or simulation API environment (`TRADOVATE_RETAIL_API_ACCESS = FUNDED_LIVE_ACCOUNT_REQUIRED`; `SHADOW_FIRST_API_ECONOMICS = REDUCED_FIT`).
  - **Thai Resident KYC is NOT confirmed by primary source:** Discloses international client support in general terms, but Thailand does not appear on an official public whitelist.
- **Verdict:** **CANDIDATE_ON_HOLD** pending primary-source Thai onboarding confirmation and live-account API cost trade-off evaluation.

### 3.3 Candidate Gamma: Ironbeam
- **Strengths:** High-speed direct exchange connectivity, registered FCM with clearing sovereignty.
- **Weaknesses:** Imposes a ~$249/month developer API fee on accounts failing to meet heavy trading volume quotas. Unattractive for ACASH's shadow-first, low-turnover research model.
- **Verdict:** **REDUCED_FIT_CANDIDATE** due to anti-developer API economics for low-turnover/shadow phases. Not permanently disqualified by immutable charter rule, but economically unattractive for R0.

### 3.4 Candidate Delta: AMP Futures
- **Strengths:** Established discount futures broker, accepts international clients, competitive day margins.
- **Weaknesses:** Official risk policy explicitly restricts account holders from setting customized daily loss or maximum contract limits in the portal (enforces rigid FCM defaults).
- **Verdict:** **REDUCED_FIT_CANDIDATE** due to lack of customizable programmatic client-side risk boundaries.

---

## 4. Working Candidate Classifications for Future Implementation

Based on multi-factor evaluation (Eligibility Certainty > API Economics > Risk Controls > Margins):

1. **Interactive Brokers (IBKR):** `LEADING_CANDIDATE` (Meets regulatory, Thai eligibility, funding, and cost requirements; subject to auth/pacing constraints).
2. **NinjaTrader / Tradovate:** `CANDIDATE_ON_HOLD` (Re-evaluate if primary-source evidence proves seamless Thai individual KYC and retail API economics align).
3. **AMP Futures:** `REDUCED_FIT_CANDIDATE` (Restricted client-side loss limit controls).
4. **Ironbeam:** `REDUCED_FIT_CANDIDATE` (Prohibitive monthly developer API fee for low-volume/shadow phase).

> **GOVERNANCE INVARIANT:**
> `FUTURES_BROKER = CANDIDATE_IDENTIFIED`
> No broker is authorized, selected, or funded for capital deployment. Capital authority remains `$0.00`.

---

## 5. Verification Ledger

- Evaluation Status: COMPLETE (4 Major FCMs Analyzed)
- Candidate Classification:
  - IBKR: `LEADING_CANDIDATE`
  - NinjaTrader / Tradovate: `CANDIDATE_ON_HOLD`
  - AMP Futures: `REDUCED_FIT_CANDIDATE`
  - Ironbeam: `REDUCED_FIT_CANDIDATE`
- Overall Broker Status: `FUTURES_BROKER = CANDIDATE_IDENTIFIED`
- Thai Onboarding Proof: IBKR (`CONFIRMED`) | NinjaTrader (`NOT_CONFIRMED`)
- Tradovate Retail API: `FUNDED_LIVE_ACCOUNT_REQUIRED` (> $1,000 equity + subscription)
- IBKR Pacing Limits: DOCUMENTED (Web API 10 req/s or 50 req/min; TWS lines/2 pacing)
- Sizing Policy: Risk-at-invalidation strictly decoupled from broker day margin
- Capital Authority: `$0.00` / NO REAL ORDERS
