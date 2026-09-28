# ACASH PPDS R0 Research Register & Source Authority Ledger

**Document:** `docs/ppds/PPDS_R0_RESEARCH_REGISTER.md`
**System Module:** Personal Portfolio Decision Support (PPDS)
**Research Stage:** R0 Architecture & Broker Due Diligence
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 1, 3, 6

---

## 1. Primary Source Hierarchy & Evidence Classification

In strict adherence to the Operator Decision Charter, PPDS R0 enforces a non-negotiable source authority precedence:
1. **Tier 1 — Statutory / Regulatory / Government Authorities:**
   - Thai Revenue Department (RD), SEC Thailand, Bank of Thailand (BOT).
   - US Securities and Exchange Commission (SEC), Financial Industry Regulatory Authority (FINRA), Commodity Futures Trading Commission (CFTC), National Futures Association (NFA).
2. **Tier 2 — Regulated Exchanges & Central Clearing Houses:**
   - Chicago Mercantile Exchange (CME Group: CME, CBOT, NYMEX, COMEX), NYSE, NASDAQ, Options Clearing Corporation (OCC).
3. **Tier 3 — Regulated Broker Legal Agreements & Official Pricing Disclosures:**
   - Official product disclosure statements, fee schedules, customer agreements, and official developer API contracts.
4. **Tier 4 — Broker Help Centers & Verified FAQ Portals:**
   - Operational help articles, campaign qualification terms, and knowledge base documentation.
5. **Tier 5 — Secondary Corroboration (Discovery Only):**
   - Independent developer forums, third-party platform reviews, user experience reports. *Rule:* Never use Tier 5 as sole authority for fee, regulatory, or execution claims.

---

## 2. Research Claims & Evidence Census

| Claim ID | Category | Proposition / Claim | Primary Source & Evidence Link | Authority Tier | Status | Volatility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CLM-DIM-01** | Dime! Fees | Standard US equity commission is 0.15% (min USD 0.00 / no minimum ticket charge) with first trade of calendar month free. | Dime! Official Fee Schedule & Customer Terms | Tier 3 | **CONFIRMED** | Moderate |
| **CLM-DIM-02** | Dime! Promotion | Dime Club Level 1 Free Trade Day applies to qualifying US stock/ETF BUY Market Orders funded in THB or from Dime! FCD. | Dime! Club Level 1 Official Article (Sep 2026) | Tier 4 | **CONFIRMED** | **VOLATILE** (Valid through 2026-09-30) |
| **CLM-DIM-03** | Dime! Promotion | Dime Club Level 1 US Free Trade window is strictly 22:00–23:50 Thailand time (ICT). | Dime! Club Official Article | Tier 4 | **CONFIRMED** | **VOLATILE** |
| **CLM-DIM-04** | Dime! Friction | CAT fee reflects irreconcilable rates across active official pages ($0.000046 vs $0.000003 per share, retrieved 2026-09-28). | Dime! Support & Help Center Articles | Tier 4 | **SOURCE_CONFLICT** | **VOLATILE** |
| **CLM-DIM-05** | Dime! Account | Account/wallet terminology diverges between "Dime! FCD" and "Dime! USD" in promotional eligibility clauses. | Dime! Payday Sep 2026 vs Club Terms | Tier 4 | **SOURCE_CONFLICT** | Low |
| **CLM-SEC-01** | US Regulatory | SEC Section 31 Fee is 0.00206% ($20.60 per $1M covered sales) effective 2026-04-04. Stale FY2025 rates (~0.00278%) superseded. | SEC Fee Rate Advisory FY2026; Dime! Fee Schedule | Tier 1/3 | **CONFIRMED** | Moderate |
| **CLM-FIN-01** | US Regulatory | FINRA TAF rate is date-effective: $0.000195/share (max $9.79) through 2026-09-30; $0.00 from 2026-10-01 to 2026-12-31 per SR-FINRA-2026-021 pause. | SEC Rel. 34-106409 (SR-FINRA-2026-021); Dime! Disclosures | Tier 1/3 | **CONFIRMED** | **VOLATILE** |
| **CLM-WEB-01** | Webull TH API | Webull Thailand offers an official Open API covering Trading, Market Data, Account, and WebSocket feeds. | Webull Securities (Thailand) Open API Portal | Tier 3 | **CONFIRMED** | Low |
| **CLM-WEB-02** | Webull TH API | Webull Open API currently advertises no developer or API access fees. | Webull Open API Official Terms | Tier 3 | **CONFIRMED** | **VOLATILE** |
| **CLM-WEB-03** | Webull Security| Technical isolation of order-writing capability at the API key generation layer (truly read-only credential without order submission permission). | Webull Open API Key Console Documentation | Tier 3 | **UNRESOLVED** | Low |
| **CLM-IBK-01** | IBKR Futures | Thailand is explicitly listed on the official Interactive Brokers available account country list. | IBKR Official Account Opening Country List | Tier 3 | **CONFIRMED** | Low |
| **CLM-IBK-02** | IBKR Pricing | US Micro Futures (MES, MNQ, MCL, MGC) broker commission is USD 0.25/contract (Tiered $\le 1,000$ contracts/month) before exchange/regulatory fees. | IBKR Futures Commission & Fee Schedule | Tier 3 | **CONFIRMED** | Moderate |
| **CLM-IBK-03** | IBKR API | IBKR APIs have no separate API access fee but are subject to account/auth/pacing limits (Web API historical 10 req/s or 50 req/min; TWS Lines/2 pacing). Retail Web API uses Client Portal Gateway; OAuth 2.0 direct API is restricted to licensed orgs/FAs; TWS API uses TWS/IB Gateway. | IBKR Official Web API & TWS Documentation | Tier 3 | **CONFIRMED** | Moderate |
| **CLM-NT-01** | NinjaTrader | NinjaTrader Clearing LLC is a CFTC-registered FCM (NFA ID 0309379). | NFA BASIC Registry / NinjaTrader Disclosures | Tier 1/3 | **CONFIRMED** | Low |
| **CLM-NT-02** | NinjaTrader | Micro contract commission is USD 0.39/side (Free plan) before exchange/clearing/NFA fees. | NinjaTrader Official Pricing Schedule | Tier 3 | **CONFIRMED** | Moderate |
| **CLM-NT-03** | NinjaTrader | Thai resident onboarding eligibility and KYC clearance for live funded trading. | NinjaTrader Account Application Requirements | Tier 3 | **UNRESOLVED** | **VOLATILE** |
| **CLM-NT-04** | Tradovate API | Retail REST API access requires a funded LIVE account (> $1,000 equity), API Access subscription, and API key. No free retail dev/sim access. | Tradovate Official API Documentation | Tier 3 | **CONFIRMED** | Moderate |
| **CLM-TAX-01** | Thai Tax | Thai tax residency is determined by the 180-day physical presence test within a calendar tax year. | Thai Revenue Code § 41, RD Guide 2026 | Tier 1 | **CONFIRMED** | Low |
| **CLM-TAX-02** | Thai Tax | Foreign-source assessable income brought into Thailand by a Thai tax resident is subject to personal income tax (PIT) under revised RD interpretation. | RD Order Paw 161/2566 & Paw 162/2566, Guide 2026 | Tier 1 | **CONFIRMED** | Moderate |
| **CLM-TAX-03** | Tax Treaty | Form W-8BEN is documentation claiming US–Thailand DTA treaty benefits; Article 10 caps gross dividend withholding at 15% for qualifying individual beneficial owners (RICs per para 3). | US–Thailand DTA Article 10, IRS W-8BEN Instructions | Tier 1 | **CONFIRMED** | Low |
| **CLM-CME-01** | CME Futures | Micro E-mini Nasdaq-100 (MNQ) contract multiplier is $2.00 \times \text{Index}$, tick size 0.25 index points ($0.50/tick), cash-settled. | CME Group Official MNQ Contract Specs | Tier 2 | **CONFIRMED** | Low |
| **CLM-FUT-01** | Futures Selection | Candidate classification: IBKR = LEADING_CANDIDATE, NinjaTrader = CANDIDATE_ON_HOLD, AMP/Ironbeam = REDUCED_FIT_CANDIDATE. Overall FUTURES_BROKER = CANDIDATE_IDENTIFIED; zero capital authorized. | ACASH Due Diligence Matrix (`FUTURES_BROKER_DUE_DILIGENCE_R0.md`) | Tier 3 | **CONFIRMED** | Low |

---

## 3. Detailed Source Conflict & Unresolved Findings

### 3.1 Conflict Alpha: `DIME_FCD_VS_DIME_USD`
- **Source A (Dime! Club Level 1 Article):** States that qualifying US Buy Market Orders may be funded in THB or in USD from "Dime! FCD".
- **Source B (Dime! Payday September 2026 Campaign Terms):** Explicitly states: *"Transactions funded via Dime! USD are excluded from campaign benefits."*
- **Reconciliation Status:** **`NEEDS_PRIMARY_SOURCE_RECONCILIATION`**. It is currently unverified whether "Dime! USD" represents an older legacy product name, an internal multi-currency wallet distinct from the KKP Foreign Currency Deposit (FCD) account, or a promotional restriction. In R0, the data model preserves broker-native wallet strings without conflation.

### 3.2 Conflict Beta: `DIME_CAT_FEE`
- **Empirical Observation:** Active official Dime! pages retrieved 2026-09-28 reflect irreconcilable CAT fee rates:
  - Page Rendering 1: **$0.000046 per share**.
  - Page Rendering 2: **$0.000003 per share**.
- **Reconciliation Status:** **`SOURCE_CONFLICT`**. In the PPDS execution cost optimizer, CAT fee is parameterized as a configurable floating fee parameter rather than hardcoded.

### 3.3 Unresolved Finding Gamma: `THAI_RESIDENT_NINJATRADER`
- **Current Evidence:** NinjaTrader discloses support for international clients and outlines foreign bank wire procedures. However, Thailand does not appear on an unambiguous, publicly accessible white-list document comparable to IBKR's published country directory.
- **Reconciliation Status:** **`NOT_CONFIRMED`**. The broker due diligence report flags NinjaTrader as requiring direct compliance/onboarding verification before any capital transfer is contemplated.

### 3.4 Economic Finding Delta: `TRADOVATE_RETAIL_API_ACCESS`
- **Current Evidence:** Official Tradovate API documentation explicitly specifies that retail REST API access requires a live account with > $1,000 equity, active API Access subscription, and API key.
- **Status:** **`FUNDED_LIVE_ACCOUNT_REQUIRED`**. Free retail simulation/developer access does not exist for un-funded retail accounts (`SHADOW_FIRST_API_ECONOMICS = REDUCED_FIT`).

### 3.5 Architectural Finding Epsilon: `IBKR_API_AUTHENTICATION_AND_PACING`
- **Current Evidence:** Official IBKR documentation proves that API access is subject to pacing limits (e.g. `/iserver/marketdata/history` capped at 10 req/s or 50 req/min; TWS message pacing tied to Market Data Lines / 2). Retail Web API requires local execution of Client Portal Gateway with browser-based session authentication; OAuth 2.0 direct API applies to licensed Organizations and Financial Advisors; TWS API connects via TWS or IB Gateway (distinct daemon from Client Portal Gateway).
- **Status:** **`CONFIRMED`** (pacing limits and gateway requirements codified).

### 3.6 Tax Finding Zeta: `W8BEN_TREATY_BENEFIT_DISTINCTION`
- **Current Evidence:** Form W-8BEN is statutory documentation used by foreign beneficial owners to claim applicable tax treaty treatment. Under Article 10 of the US–Thailand Income Tax Treaty, US dividend withholding is capped at 15% for qualifying individual beneficial owners (and RIC distributions per para 3).
- **Status:** **`CONFIRMED`** (`TAX_INTERPRETATION_REQUIRES_HUMAN/PROFESSIONAL_REVIEW = true`).

---

## 4. Volatility Tracking & Expiration Policy

Promotional parameters, broker commission discounts, and intraday margin schedules are inherently volatile:
1. **Promotional Calendar Bounds:** The Dime Club Level 1 Free Trade Day calendar is verified through **30 September 2026**. It must **never** be assumed to automatically recur on the 15th and 30th of future months without active primary-source verification.
2. **FINRA TAF Temporary Pause:** The statutory pause on FINRA TAF assessment under SR-FINRA-2026-021 is bounded to **2026-10-01 through 2026-12-31 inclusive**. It must **never** be extrapolated into 2027 without a new SRO/SEC filing.
3. **Futures Margin Volatility:** Intraday margins (e.g. $50 micro day-margin) are discretionary broker risk parameters subject to doubling or tripling during geopolitical, economic release, or market volatility spikes.

---

## 5. Verification Ledger

- Implementation Status: COMPLETE
- Total Claims Censused: 22
- Confirmed Claims: 18
- Source Conflicts Preserved: 2 (`DIME_FCD_VS_DIME_USD`, `DIME_CAT_FEE`: $0.000046 vs $0.000003)
- Unresolved Resident KYC: 1 (`THAI_RESIDENT_NINJATRADER`)
- Unresolved Technical Security: 1 (`WEBULL_READ_ONLY_INTEGRATION`)
- Broker Selection Status: IBKR (`LEADING_CANDIDATE`), FUTURES_BROKER (`CANDIDATE_IDENTIFIED`)
- Capital Authority: `$0.00` (NO REAL ORDERS)
- Governance Contract: STRICT FAIL-CLOSED PRESERVED
