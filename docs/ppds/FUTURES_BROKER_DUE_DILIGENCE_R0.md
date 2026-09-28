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
| **API & Telemetry Quality** | Tradovate REST / WebSocket API + NinjaTrader SDK. Excellent. | IBKR Web API / Client Portal API / TWS API. Industry benchmark. | Dedicated Ironbeam API. | Third-party routing APIs (CQG, Rithmic). |
| **API Commercial Cost** | Free simulation / developer access within platform tier. | Free API access with funded account ($0 monthly API fee). | **PROHIBITIVE:** ~$249/mo read-only API fee unless minimum trade quota met; $99 sim fee. | Varies by routing bridge (CQG/Rithmic data add-ons). |
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
  - Completely free, unthrottled API access (Web API / TWS API) without monthly minimum turnover penalties.
  - Easiest funding infrastructure from Thailand (direct Wise integration and established Swift routes).
- **Weaknesses:**
  - Intraday margin requirements are conservative (typically 50% of overnight initial margin, e.g. ~$1,000–$1,500 on equity micros vs $50 at specialty futures brokers).
  - Web API requires local gateway process (IB Gateway / TWS daemon) running locally.
- **Verdict:** **Strongest overall candidate for institutional robustness, API economics, and Thai residency certainty**.

### 3.2 Candidate Beta: NinjaTrader / Tradovate
- **Strengths:**
  - Purpose-built for futures scalping and active intraday trading.
  - Ultralow day margins (~$50 on MNQ/MES).
  - Modern Tradovate REST/WebSocket API natively integrated with TradingView.
- **Weaknesses:**
  - **Thai Resident KYC is NOT confirmed by primary source**. Attempting to open and fund an account carries onboarding rejection or bank transfer return risks.
  - Subscribing to non-professional CME market data requires active recurring card billing.
- **Verdict:** **Preferred tactical platform, but BLOCKED pending formal Thai resident onboarding confirmation**.

### 3.3 Candidate Gamma: Ironbeam
- **Strengths:** High-speed direct exchange connectivity, registered FCM with clearing sovereignty.
- **Weaknesses:** Imposes a ~$249/month developer API fee on accounts failing to meet heavy trading volume quotas. Disqualifies itself from ACASH's shadow-first, low-turnover research model.
- **Verdict:** **DISQUALIFIED due to anti-developer API economics**.

### 3.4 Candidate Delta: AMP Futures
- **Strengths:** Established discount futures broker, accepts international clients, competitive day margins.
- **Weaknesses:** Official risk policy explicitly restricts account holders from setting customized daily loss or maximum contract limits in the portal (enforces rigid FCM defaults).
- **Verdict:** **REDUCED FIT due to lack of customizable programmatic risk boundaries**.

---

## 4. Working Candidate Ordering for Future Implementation

Based on multi-factor scoring (Eligibility Certainty > API Economics > Risk Controls > Margins):

1. **Interactive Brokers (IBKR):** Ranked **#1 (Primary Operational Target)**. Meets all regulatory, Thai eligibility, funding, and cost requirements.
2. **NinjaTrader / Tradovate:** Ranked **#2 (Candidate on Hold)**. Re-evaluate if primary-source evidence proves seamless Thai individual KYC and funding.
3. **AMP Futures:** Ranked **#3 (Secondary Alternative)**.
4. **Ironbeam:** Ranked **#4 (Disqualified)**.

---

## 5. Verification Ledger

- Evaluation Status: COMPLETE (4 Major FCMs Analyzed)
- Primary Recommendation: INTERACTIVE BROKERS (IBKR)
- Thai Onboarding Proof: IBKR (CONFIRMED) | NinjaTrader (NOT CONFIRMED)
- Sizing Policy: Risk-at-invalidation strictly decoupled from broker day margin
