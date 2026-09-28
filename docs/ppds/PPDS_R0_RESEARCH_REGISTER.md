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
| **CLM-DIM-04** | Dime! Friction | CAT (Consolidated Audit Trail) fee varies across published official pages (ranging from negligible fraction to distinct per-share schedules). | Dime! Support & Help Center Articles | Tier 4 | **SOURCE_CONFLICT** | **VOLATILE** |
| **CLM-DIM-05** | Dime! Account | Account/wallet terminology diverges between "Dime! FCD" and "Dime! USD" in promotional eligibility clauses. | Dime! Payday Sep 2026 vs Club Terms | Tier 4 | **SOURCE_CONFLICT** | Low |
| **CLM-WEB-01** | Webull TH API | Webull Thailand offers an official Open API covering Trading, Market Data, Account, and WebSocket feeds. | Webull Securities (Thailand) Open API Portal | Tier 3 | **CONFIRMED** | Low |
| **CLM-WEB-02** | Webull TH API | Webull Open API currently advertises no developer or API access fees. | Webull Open API Official Terms | Tier 3 | **CONFIRMED** | **VOLATILE** |
| **CLM-WEB-03** | Webull Security| Technical isolation of order-writing capability at the API key generation layer (truly read-only credential without order submission permission). | Webull Open API Key Console Documentation | Tier 3 | **UNRESOLVED** | Low |
| **CLM-IBK-01** | IBKR Futures | Thailand is explicitly listed on the official Interactive Brokers available account country list. | IBKR Official Account Opening Country List | Tier 3 | **CONFIRMED** | Low |
| **CLM-IBK-02** | IBKR Pricing | US Micro Futures (MES, MNQ, MCL, MGC) broker commission is USD 0.25/contract (Tiered $\le 1,000$ contracts/month) before exchange/regulatory fees. | IBKR Futures Commission & Fee Schedule | Tier 3 | **CONFIRMED** | Moderate |
| **CLM-NT-01** | NinjaTrader | NinjaTrader Clearing LLC is a CFTC-registered FCM (NFA ID 0309379). | NFA BASIC Registry / NinjaTrader Disclosures | Tier 1/3 | **CONFIRMED** | Low |
| **CLM-NT-02** | NinjaTrader | Micro contract commission is USD 0.39/side (Free plan) before exchange/clearing/NFA fees. | NinjaTrader Official Pricing Schedule | Tier 3 | **CONFIRMED** | Moderate |
| **CLM-NT-03** | NinjaTrader | Thai resident onboarding eligibility and KYC clearance for live funded trading. | NinjaTrader Account Application Requirements | Tier 3 | **UNRESOLVED** | **VOLATILE** |
| **CLM-TAX-01** | Thai Tax | Thai tax residency is determined by the 180-day physical presence test within a calendar tax year. | Thai Revenue Code § 41, RD Guide 2026 | Tier 1 | **CONFIRMED** | Low |
| **CLM-TAX-02** | Thai Tax | Foreign-source assessable income brought into Thailand by a Thai tax resident is subject to personal income tax (PIT) under revised RD interpretation. | RD Order Paw 161/2566 & Paw 162/2566, Guide 2026 | Tier 1 | **CONFIRMED** | Moderate |
| **CLM-CME-01** | CME Futures | Micro E-mini Nasdaq-100 (MNQ) contract multiplier is $2.00 \times \text{Index}$, tick size 0.25 index points ($0.50/tick), cash-settled. | CME Group Official MNQ Contract Specs | Tier 2 | **CONFIRMED** | Low |

---

## 3. Detailed Source Conflict & Unresolved Findings

### 3.1 Conflict Alpha: `DIME_FCD_VS_DIME_USD`
- **Source A (Dime! Club Level 1 Article):** States that qualifying US Buy Market Orders may be funded in THB or in USD from "Dime! FCD".
- **Source B (Dime! Payday September 2026 Campaign Terms):** Explicitly states: *"Transactions funded via Dime! USD are excluded from campaign benefits."*
- **Reconciliation Status:** **`NEEDS_PRIMARY_SOURCE_RECONCILIATION`**. It is currently unverified whether "Dime! USD" represents an older legacy product name, an internal multi-currency wallet distinct from the KKP Foreign Currency Deposit (FCD) account, or a promotional restriction. In R0, the data model will preserve broker-native wallet strings without conflation.

### 3.2 Conflict Beta: `DIME_CAT_FEE`
- **Empirical Observation:** Crawlers and cached legal disclosures have reflected inconsistent fee entries for the Consolidated Audit Trail (CAT) regulatory fee, ranging from omitted/subsidized to specific per-share fractions.
- **Reconciliation Status:** **`SOURCE_CONFLICT`**. In the PPDS execution cost optimizer, CAT fee will be parameterized as a configurable floating fee parameter rather than hardcoded.

### 3.3 Unresolved Finding Gamma: `THAI_RESIDENT_NINJATRADER`
- **Current Evidence:** NinjaTrader discloses support for international clients and outlines foreign bank wire procedures. However, Thailand does not appear on an unambiguous, publicly accessible white-list document comparable to IBKR's published country directory.
- **Reconciliation Status:** **`NOT_CONFIRMED`**. The broker due diligence report will flag NinjaTrader as requiring direct compliance/onboarding verification before any capital transfer is contemplated.

---

## 4. Volatility Tracking & Expiration Policy

Promotional parameters, broker commission discounts, and intraday margin schedules are inherently volatile:
1. **Promotional Calendar Bounds:** The Dime Club Level 1 Free Trade Day calendar is verified through **30 September 2026**. It must **never** be assumed to automatically recur on the 15th and 30th of future months without active primary-source verification.
2. **Futures Margin Volatility:** Intraday margins (e.g. $50 micro day-margin) are discretionary broker risk parameters subject to doubling or tripling during geopolitical, economic release, or market volatility spikes.

---

## 5. Verification Ledger

- Implementation Status: COMPLETE
- Total Claims Censused: 16
- Confirmed Claims: 12
- Source Conflicts Preserved: 2 (`DIME_FCD_VS_DIME_USD`, `DIME_CAT_FEE`)
- Unresolved Resident KYC: 1 (`THAI_RESIDENT_NINJATRADER`)
- Unresolved Technical Security: 1 (`WEBULL_READ_ONLY_INTEGRATION`)
- Governance Contract: STRICT FAIL-CLOSED PRESERVED
