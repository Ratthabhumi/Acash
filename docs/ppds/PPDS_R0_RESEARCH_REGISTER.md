# ACASH PPDS R0 Research Register & Source Authority Ledger

**Document:** `docs/ppds/PPDS_R0_RESEARCH_REGISTER.md`
**System Module:** Personal Portfolio Decision Support (PPDS)
**Research Stage:** R0 Architecture & Broker Due Diligence (Hardening Pass #2)
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

### Strict Claim Classification Taxonomy:
- **`CONFIRMED_FACT`**: Verified against Tier 1, 2, or 3 primary source documentation.
- **`VOLATILE_EXTERNAL_PARAMETER`**: Factual parameter subject to external variation, broker discretion, or promotional calendar expiration.
- **`SOURCE_CONFLICT`**: Irreconcilable conflict across active official primary sources.
- **`MODEL_ASSUMPTION_NOT_CALIBRATED`**: Working hypothesis or engineering model parameter lacking empirical calibration.
- **`CANDIDATE_POLICY_UNRATIFIED`**: System design proposal awaiting operator review and ratification.
- **`HUMAN_INPUT_REQUIRED`**: Personal preference or capital parameter requiring operator decision.
- **`PROFESSIONAL_REVIEW_REQUIRED`**: Legal, tax, or accounting characterization requiring qualified external opinion.
- **`NOT_IMPLEMENTED`**: Architectural design invariant not yet implemented in production runtime.
- **`BLOCKED`**: Architectural path stopped due to missing security, compliance, or credential proofs.

---

## 2. Research Claims & Evidence Census

| Claim ID | Category | Proposition / Claim | Primary Authority & Evidence Link | Authority Tier | Status | Volatility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CLM-DIM-01** | Dime! Fees | Standard US equity commission is 0.15% (min USD 0.00 / no ticket fee) with first trade of calendar month free. | Dime! Official Fee Schedule & Customer Terms | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-DIM-02** | Dime! Promotion | Dime Club Sliding Commission 2026 applies monthly tiered buy commissions (<=5m: 0.15%, 5m-20m: 0.10%, >20m: 0.05%; sell 0.15%; benefits through Dec 2026). | Dime! Official Club Sliding Commission Terms (Sep 2026) | Tier 4 | **CONFIRMED_FACT** | **VOLATILE_EXTERNAL_PARAMETER** |
| **CLM-DIM-03** | Dime! Promotion | Dime Club Level 1 US Free Trade window is strictly 22:00–23:50 Thailand time (ICT) on designated campaign dates. | Dime! Club Official Article | Tier 4 | **CONFIRMED_FACT** | **VOLATILE_EXTERNAL_PARAMETER** |
| **CLM-DIM-04** | Dime! Friction | CAT fee reflects irreconcilable rates across active official pages ($0.000046 vs $0.000003 per share, retrieved 2026-09-28). | Dime! Support & Help Center Articles | Tier 4 | **SOURCE_CONFLICT** | **VOLATILE_EXTERNAL_PARAMETER** |
| **CLM-DIM-05** | Dime! Account | Dime! FCD - USD (KKP bank deposit) and Dime! USD (stock trading cash balance) are distinct account products with independent campaign terms. | Dime! Official FCD Product FAQ (2026) | Tier 4 | **CONFIRMED_FACT** | Low |
| **CLM-DIM-06** | Dime! Execution | Fixed spread estimates (VOO 1-2 bps, small thematic 50-100 bps) and FX drag (10-25 bps) are engineering heuristics. | ACASH Model Formulation | Internal | **MODEL_ASSUMPTION_NOT_CALIBRATED** | High |
| **CLM-SEC-01** | US Regulatory | SEC Section 31 Fee is 0.00206% ($20.60 per $1M covered sales) effective 2026-04-04. Stale FY2025 rates (~0.00278%) superseded. | SEC Fee Rate Advisory FY2026; Dime! Fee Schedule | Tier 1/3 | **CONFIRMED_FACT** | Moderate |
| **CLM-FIN-01** | US Regulatory | FINRA TAF rate is date-effective: $0.000195/share (max $9.79) through 2026-09-30; $0.00 from 2026-10-01 to 2026-12-31 per SR-FINRA-2026-021 pause. | SEC Rel. 34-106409 (SR-FINRA-2026-021); Dime! Disclosures | Tier 1/3 | **CONFIRMED_FACT** | **VOLATILE_EXTERNAL_PARAMETER** |
| **CLM-WEB-01** | Webull TH API | Webull Thailand offers an official Open API covering Trading REST, gRPC Trade Events, and WebSocket Market Data. | Webull Securities (Thailand) Developer Portal | Tier 3 | **CONFIRMED_FACT** | Low |
| **CLM-WEB-02** | Webull TH API | Webull Open API currently advertises no developer or API access fees. | Webull Open API Official Terms | Tier 3 | **CONFIRMED_FACT** | **VOLATILE_EXTERNAL_PARAMETER** |
| **CLM-WEB-03** | Webull Security | Primary-source proof of broker-enforced individual read-only API key lacking order-placement scope is unconfirmed. | Webull Open API Documentation & Console | Tier 3 | **BLOCKED** | Low |
| **CLM-WEB-04** | Webull Auth | Webull Thailand uses App Key/App Secret, signed requests (version/endpoint dependent), access tokens, and initial 2FA. | Webull Thailand Individual API Documentation | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-WEB-05** | Webull Test | Webull Thailand provides a UAT/test environment with isolated test tokens, documented but not authorized for ACASH use. | Webull Thailand API Environment Documentation | Tier 3 | **NOT_IMPLEMENTED** | Low |
| **CLM-WEB-06** | Webull Data | App market data subscriptions do not automatically confer OpenAPI market data entitlements (separate subscription required). | Webull Thailand Market Data API Documentation | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-IBK-01** | IBKR Futures | Thailand is explicitly listed on the official Interactive Brokers available account country list. | IBKR Official Account Opening Country List | Tier 3 | **CONFIRMED_FACT** | Low |
| **CLM-IBK-02** | IBKR Pricing | US Micro Futures (MES, MNQ, MCL, MGC) broker commission is USD 0.25/contract (Tiered $\le 1,000$ contracts/month) before exchange/regulatory fees. | IBKR Futures Commission & Fee Schedule | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-IBK-03** | IBKR API | IBKR Web API (Client Portal Gateway) throttled to 10 req/s or 50 req/min; TWS API paced by Lines/2; OAuth 2.0 direct restricted to institutional/FAs. | IBKR Official Web API & TWS Documentation | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-IBK-04** | IBKR Rail | Multi-currency wires and Wise account integration supported; local Thai bank partner rail is unconfirmed. | IBKR Funding Methods Portal | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-NT-01** | NinjaTrader | NinjaTrader Clearing LLC is a CFTC-registered FCM (NFA ID 0309379). | NFA BASIC Registry / NinjaTrader Disclosures | Tier 1/3 | **CONFIRMED_FACT** | Low |
| **CLM-NT-02** | NinjaTrader | Micro contract commission is USD 0.39/side (Free plan) before exchange/clearing/NFA fees. | NinjaTrader Official Pricing Schedule | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-NT-03** | NinjaTrader | Thai resident onboarding eligibility and KYC clearance for live funded trading is unconfirmed on official public whitelist. | NinjaTrader Account Application Requirements | Tier 3 | **BLOCKED** | **VOLATILE_EXTERNAL_PARAMETER** |
| **CLM-NT-04** | Tradovate API | Retail REST API access requires a funded LIVE account (> $1,000 equity), API Access subscription, and API key. | Tradovate Official API Documentation | Tier 3 | **CONFIRMED_FACT** | Moderate |
| **CLM-AMP-01** | AMP Futures | Thailand is not on AMP restricted countries list; Thai residents are eligible to apply subject to compliance KYC review. | AMP Futures Restricted Countries & International Policy | Tier 3 | **CONFIRMED_FACT** | Low |
| **CLM-TAX-01** | Thai Tax | Thai tax residency is determined by the 180-day physical presence test within a calendar tax year. | Thai Revenue Code § 41, RD Guide 2026 | Tier 1 | **CONFIRMED_FACT** | Low |
| **CLM-TAX-02** | Thai Tax | Foreign-source assessable income brought into Thailand by a Thai tax resident is subject to PIT under RD Order Paw 161/2566 & Paw 162/2566. | RD Order Paw 161/2566 & Paw 162/2566, Guide 2026 | Tier 1 | **CONFIRMED_FACT** | Moderate |
| **CLM-TAX-03** | Tax Treaty | Form W-8BEN claims US–Thailand DTA treaty benefits; Article 10 caps gross dividend withholding at 15% for qualifying individual beneficial owners. | US–Thailand DTA Article 10, IRS W-8BEN Instructions | Tier 1 | **CONFIRMED_FACT** | Low |
| **CLM-TAX-04** | Tax FX Rate | Foreign currency conversion under Thai Revenue Code § 9 allows commercial bank daily rate OR BOT daily reference rate, subject to consistency. | Thai Revenue Code § 9; MOF Notification on Exchange Rates | Tier 1 | **CONFIRMED_FACT** | Low |
| **CLM-TAX-05** | Tax Cost Basis | Selection of cost basis method (FIFO, weighted average, specific lot) for foreign individual equity gains requires tax professional determination. | Thai Revenue Department Practice / Tax Law Framework | Tier 1 | **PROFESSIONAL_REVIEW_REQUIRED** | Low |
| **CLM-TAX-06** | Remittance | Characterization of remitted capital vs foreign gains requires legal/accounting review; system preserves source lot evidence without deciding legal truth. | Thai Revenue Department Orders 161/162 | Tier 1 | **PROFESSIONAL_REVIEW_REQUIRED** | Low |
| **CLM-CME-01** | CME Futures | MNQ, MES, and MCL are Financially (Cash) Settled; MGC is Physically Deliverable (COMEX); M6E is Deliverable Currency (CME FX). | CME Group Official Contract Specifications | Tier 2 | **CONFIRMED_FACT** | Low |
| **CLM-CME-02** | CME Rollover | "Second Thursday" is an observed market volume convention, not an exchange rule. Continuous roll policy requires deterministic pre-registration. | CME Globex Trading Practices / Academic Literature | Tier 2 | **CANDIDATE_POLICY_UNRATIFIED** | Moderate |
| **CLM-CME-03** | CME Delivery | Software buffer (e.g. roll $N$ days before FND or termination) is an ACASH safety candidate policy, not an exchange rule. | ACASH Architectural Design | Internal | **CANDIDATE_POLICY_UNRATIFIED** | Low |
| **CLM-FUT-01** | Futures Cost | All-in round-turn futures costs vary across brokers, routing, exchange tiers, and data fees; cross-broker claims are not normalized. | FCM Pricing Schedules | Tier 3 | **MODEL_ASSUMPTION_NOT_CALIBRATED** | High |
| **CLM-FUT-02** | Futures Margin | Broker intraday day-margins ($50-$100) are volatile operational parameters; risk sizing decoupled from margin. | FCM Risk Disclosure Documents | Tier 3 | **VOLATILE_EXTERNAL_PARAMETER** | High |
| **CLM-ARC-01** | Architecture | Existing portfolio holdings (VOO, QQQM, TSM, PLTR, etc.) are illustrative examples, not ratified permanent book assignments. | Operator Working Portfolio | Internal | **HUMAN_INPUT_REQUIRED** | Low |
| **CLM-ARC-02** | Architecture | PPDS runtime implementation, automated reconciliation, and hash-chain audit ledgers are architectural draft invariants, not implemented code. | ACASH PPDS Repository State | Internal | **NOT_IMPLEMENTED** | Low |
| **CLM-ARC-03** | Architecture | Trading Book currently possesses zero authorized production trading strategies (NO_AUTHORIZED_TRADING_STRATEGY / NO_TRADE). | ACASH Governance Framework | Internal | **CONFIRMED_FACT** | Low |

---

## 3. Detailed Source Conflict & Reconciliation Ledger

### 3.1 `DIME_FCD_VS_DIME_USD`
- **Previous Status:** `NEEDS_PRIMARY_SOURCE_RECONCILIATION`.
- **Reconciliation Finding:** Re-examination of official Dime! FAQ and product disclosure documentation (2026) confirms that **Dime! FCD - USD** (bank foreign currency deposit account held with Kiatnakin Phatra Bank, earning deposit interest and supporting US stocks, options, and gold) and **Dime! USD** (securities trading cash balance supporting US stocks and options) are **distinct account products**.
- **Resolution:** **`RESOLVED_DISTINCT_PRODUCTS`**. Eligibility terms in one campaign that include Dime! FCD while another campaign excludes Dime! USD do not represent a contradiction. The PPDS data model preserves account product types independently.

### 3.2 `DIME_CAT_FEE`
- **Empirical Observation:** Active official Dime! pages retrieved 2026-09-28 reflect irreconcilable CAT fee rates ($0.000046 vs $0.000003 per share).
- **Status:** **`SOURCE_CONFLICT`**. Retained as floating parameterized cost.

### 3.3 `WEBULL_BROKER_SIDE_READ_ONLY_KEY`
- **Primary Source Finding:** Webull Thailand individual developer onboarding documentation confirms App Key/Secret generation, signed requests, access tokens, and initial 2FA verification. However, no primary documentation confirms broker-enforced read-only permission scoping for individual credentials.
- **Resolution:** **`WEBULL_BROKER_SIDE_READ_ONLY_KEY = NOT_PRIMARY_SOURCE_CONFIRMED`**; **`WEBULL_READ_ONLY_INTEGRATION = BLOCKED_PENDING_SECURITY_DESIGN`**.

---

## 4. Verification Ledger

- Research Register Status: AUDITED & HARDENED (Pass #2)
- Total Claims Censused: 37
- Confirmed Facts: 19
- Volatile Parameters: 7
- Uncalibrated Model Assumptions: 2
- Source Conflicts: 1 (`DIME_CAT_FEE`)
- Unratified Candidate Policies: 2
- Human Input Required: 2
- Professional Review Required: 2
- Not Implemented: 2
- Blocked Integration Paths: 2 (`WEBULL_READ_ONLY_INTEGRATION`, `THAI_RESIDENT_NINJATRADER`)
- Capital Authority: `$0.00` (NO REAL ORDERS)
