# ACASH PPDS Session Handoff (R0 Architecture & Research Complete)

**Document:** `docs/ppds/SESSION_HANDOFF.md`
**System Module:** Personal Portfolio Decision Support (PPDS)
**Research Stage:** R0 Architecture, Due Diligence & Data Contracts (Evidence-Hardened)
**Branch:** `research/ppds-r0-capital-broker-architecture-20260928`
**Base Canonical Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda)

---

## Authoritative Current State After R0 Evidence Hardening

```text
PPDS_R0_EVIDENCE_AUDIT             = PASS_WITH_UNRESOLVED_GATES
PPDS_RUNTIME_IMPLEMENTATION        = NOT_AUTHORIZED / NOT_IMPLEMENTED
PPDS_R0_RESEARCH_CHURN             = STOP
PERSONAL_CAPITAL_ALLOCATION_POLICY = UNRESOLVED
CURRENT_HOLDINGS_BOOK_ASSIGNMENT   = UNRATIFIED
NO_AUTHORIZED_TRADING_STRATEGY     = true
DIME_FCD_VS_DIME_USD               = RESOLVED_DISTINCT_PRODUCTS
DIME_CAT_FEE                       = SOURCE_CONFLICT
DIME_COMMISSION_MODEL              = EFFECTIVE_DATED_ACCOUNT_SPECIFIC
DIME_EXECUTION_SPREAD_MODEL        = NOT_CALIBRATED
WEBULL_BROKER_SIDE_READ_ONLY_KEY   = NOT_PRIMARY_SOURCE_CONFIRMED
WEBULL_READ_ONLY_INTEGRATION       = BLOCKED_PENDING_SECURITY_DESIGN
WEBULL_UAT                         = DOCUMENTED_NOT_AUTHORIZED_FOR_USE
TAX_FX_METHOD                      = HUMAN_PROFESSIONAL_POLICY_REQUIRED
TAX_COST_BASIS_METHOD              = HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED
TAX_REMITTANCE_CHARACTERIZATION    = HUMAN_PROFESSIONAL_REVIEW_REQUIRED
FUTURES_CONTINUOUS_ROLL_POLICY     = UNRESOLVED
DELIVERY_RISK_BUFFER_POLICY        = UNRATIFIED
FUTURES_BROKER                     = CANDIDATE_IDENTIFIED
IBKR                               = LEADING_CANDIDATE_NOT_AUTHORIZED
THAI_RESIDENT_NINJATRADER          = NOT_CONFIRMED
REAL_ORDER_AUTHORITY               = NONE
PAPER_TRADING_AUTHORITY            = NONE
LIVE_TRADING_AUTHORITY             = NONE
CAPITAL_AUTHORITY                  = $0.00
MAIN_MODIFIED                      = false
HYP011_EXECUTION_PATH_MODIFIED     = false
HOMELAB_TOUCHED                    = false
WAIT_FOR_HYP011_OBSERVATION_0001   = true
MERGE_STATUS                       = HOLD
```

---

## 1. Governance & Strict Authority Boundaries

In strict compliance with the ACASH Operator Decision Charter:
```text
REAL_ORDER_AUTHORITY     = NONE
PAPER_TRADING_AUTHORITY = NONE
LIVE_TRADING_AUTHORITY  = NONE
CAPITAL_AUTHORITY       = $0.00
NO_REAL_ORDERS          = true
```
All portfolio and sizing models drafted in this research phase represent target architectural specifications, accounting normalization standards, and simulation logic only (`PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED`). The system has zero real trading authority, zero broker order placement capability, and zero live execution access.

---

## 2. Canonical Repository State & Pre-Observation Freeze

- **Canonical Main Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (Verified unchanged on `origin/main`).
- **HYP_011 Observation #0001 Integrity:** Completely frozen and untouched.
  - Target Session: `2026-09-28` (NYSE Regular Session).
  - Eligibility Cutoff: Strictly after `20:00:00 UTC` (`2026-09-28T20:00:00Z`).
  - Automated Timer: `acash-hyp011-observation-0001.timer` scheduled for ~`03:10 ICT` on `2026-09-29`.
  - Zero modification to homelab, service, wrapper, timer, prospective state files, or live broker configurations.
  - Invariant: `WAIT_FOR_HYP011_OBSERVATION_0001 = true`.

---

## 3. PPDS Mission & Core Philosophy

ACASH is expanding conceptually into a sovereign, broker-neutral **Capital Allocator and Decision Support System** (target architecture only; not implemented code).
- **Not an automated stock picker:** It does not blindly generate buy signals or force capital deployment.
- **Core Decision Mandate:** Answers whether new capital should remain `CASH` or be allocated into specific books.
- **First-Class Cash Allocation:** `NO_QUALIFIED_OPPORTUNITY -> HOLD_CASH` is a prioritized, fully valid system state.
- **Implementation Demarcation:** All data contracts, serialization invariants, hash chains, and gateway firewalls are `TARGET_DESIGN_INVARIANT` and `NOT_YET_IMPLEMENTED`.

---

## 4. Working Personal Portfolio Inventory (Non-Canonical Baseline)

*Notice: Ingested from operator descriptions and UI screenshots. Real cost-basis lots require official broker statement exports. All existing holdings are illustrative examples, not ratified book assignments (`CURRENT_HOLDINGS_BOOK_ASSIGNMENT = UNRATIFIED`).*

| Portfolio Segment | Observed Holdings | Classification Status | Custodian |
| :--- | :--- | :--- | :--- |
| **Long-Term / Growth** | `QQQM`, `VOO`, `PLTR`, `TSM`, `SOFI`, `NOW` | `ILLUSTRATIVE_EXISTING_HOLDING` / `BOOK_ASSIGNMENT_UNRATIFIED` | Dime! (KKP) |
| **Thematic / Space** | `SATL`, `RKLB`, `RDW`, `ITA`, `NASA`, `SIDU` | `ILLUSTRATIVE_EXISTING_HOLDING` / `BOOK_ASSIGNMENT_UNRATIFIED` | Dime! (KKP) |
| **Observed Bucket Labels** | "long-term growth", "space/thematic", "Sniper", "Trump Buy", "NBIS" | Historical / user bucket labels (not PPDS-ratified classifications) | Dime! (KKP) |
| **Dime FCD Cash** | USD balance in Dime! FCD | Foreign Currency Deposit cash balance (KKP Bank) | Dime! (KKP) |
| **Liquid THB Cash** | THB cash balance | Transaction cash balance | Dime! (KKP) / Bank |

*Rule:* Existing holdings (e.g. `PLTR`, `TSM`, `NOW`, `VOO`, `QQQM`) must never be described as "quality", "conviction", "core", or "satellite" as scientific facts; these are historical working labels awaiting formal PPDS qualification.

---

## 5. Multi-Book Architecture Summary

### 5.1 Target Book Architecture vs Current Holding Classification

The system defines a target structural taxonomy for capital allocation:
```text
TARGET CAPITAL STRUCTURE
├── INVESTMENT BOOK (Target container for long-horizon investments; unratified)
│   ├── CORE / DCA (Candidate target for broad factor/index allocations; holdings unratified)
│   ├── SATELLITE / CONVICTION (Candidate target for verified individual theses; holdings unratified)
│   └── SPECULATIVE / THEMATIC (Candidate target for narrative/early themes; bounded cap)
└── TRADING BOOK (Architectural container for separately researched and authorized strategies)
    ├── EQUITY TACTICAL / SNIPER (Candidate container for tactical equity models; Webull candidate)
    └── FUTURES / MACRO (Candidate container for CME Micro derivatives; FCM candidate identified)
```

### 5.2 Unratified Investment & Trading Objectives
- Long-term investment objectives ("generational wealth", "3–10+ year horizon") and performance benchmarks (ACWI, S&P 500, blended 80/20, SOFR) remain **`CANDIDATE_POLICY_UNRATIFIED`**.
- Personal capital split between Investment and Trading remains formally **`PERSONAL_CAPITAL_ALLOCATION_POLICY = UNRESOLVED`**. No allocation ratio (e.g. 80/20, 70/30) is authorized.

### 5.3 Trading Book Strategy Baseline
- The Trading Book possesses **zero active production trading strategies**:
  - `NO_AUTHORIZED_TRADING_STRATEGY = true`
  - `NO_TRADE = valid current state`
- The system assumes no active microstructure, momentum, volatility-dislocation, macro, or event-driven alpha edge. Strategies require separate formal preregistration and qualification.

### 5.4 Anti-Contagion Rules (Target Design):
- Investment and Trading ledgers are completely decoupled.
- Trading drawdowns never draw capital or margin from the Investment Book.
- Inter-book capital transfers require explicit operator authorization records.

---

## 6. Dime! (KKP) Research & Execution Model

The Dime cost model is account-specific, effective-dated, and promotion-aware (`DIME_COMMISSION_MODEL = EFFECTIVE_DATED_ACCOUNT_SPECIFIC`; `DIME_EFFECTIVE_COMMISSION_RATE = ACCOUNT_STATE_REQUIRED`):

1. **Baseline / Ordinary Commission:** 0.15% commission (USD 0.00 minimum ticket fee) + 7% VAT on commission.
2. **Monthly Free Trade:** First qualifying trade of each calendar month is commission-free.
3. **Dime Club Level 1 Free Trade Day:**
   - Promotional campaign verified through **30 September 2026** (dynamic calendar; does not recur automatically).
   - US trading window: strictly **22:00 – 23:50 ICT**.
   - Eligible orders: BUY Market Orders specifying THB or USD amount (funded from THB or Dime! FCD).
4. **Dime Club Sliding Commission 2026:**
   - Under current official Dime Club campaign terms, prior-month cumulative US trading volume determines BUY commission in the following month:
     - Prior-month volume $\le$ THB 5,000,000: BUY commission = **0.15%**
     - Prior-month volume THB 5,000,001 – 20,000,000: BUY commission = **0.10%**
     - Prior-month volume > THB 20,000,000: BUY commission = **0.05%**
     - US stock SELL commission remains fixed at **0.15%**.
     - Benefit schedule runs through December 2026.
     - *Constraint:* ACASH does not assume the operator qualifies for reduced tiers without explicit broker account evidence.
5. **US Regulatory Fees:**
   - **SEC Section 31 Fee:** 0.00206% ($20.60 per $1M covered sales) effective 2026-04-04 per SEC Fee Rate Advisory FY2026 (Order 2026-2). Stale FY2025 rate (~0.00278%) superseded.
   - **FINRA TAF Fee (Date-Effective Schedule):** $0.000195/share (max $9.79) through 2026-09-30; **$0.00** from 2026-10-01 through 2026-12-31 per statutory pause (SEC Rel. 34-106409 / SR-FINRA-2026-021). Post-2026-12-31 is volatile.
   - **CAT Fee:** `SOURCE_CONFLICT` preserved ($0.000046 vs $0.000003 per share on official Dime pages). Modeled as floating parameter.
6. **Execution Friction & Timing Demotion:**
   - Spread, slippage, and FX conversion friction (VOO 1–2 bps, thematic 50–100 bps, FX drag 10–25 bps) are classified as **`DIME_EXECUTION_SPREAD_MODEL = NOT_CALIBRATED`**.
   - *Policy:* Execution timing optimization remains a research/design requirement. PPDS must not recommend delaying or accelerating an investment merely to capture commission savings until spread, liquidity, FX, and timing cost models are empirically calibrated. No execution recommendation is authorized.
7. **Dime FCD vs Dime USD Reconciliation:**
   - `DIME_FCD_VS_DIME_USD = RESOLVED_DISTINCT_PRODUCTS`.
   - Primary evidence confirms Dime! FCD - USD is a bank foreign currency deposit account (KKP Bank; earns deposit interest; funds US equities, options, gold), whereas Dime! USD is a securities trading cash wallet. Campaign eligibility variations across campaigns reflect distinct products, not an empirical conflict.

---

## 7. Webull Securities (Thailand) Open API Research

- **Transport Architecture:**
  - REST HTTPS: Account list (`/trading/accounts/list`), asset balances (`/trading/assets/balances/get`), order operations (`/trading/orders/...`). Historical order query horizon noted as limited (e.g. past 7 days).
  - Server-Streaming **gRPC**: Trade event notifications (`TradeEvent` streaming).
  - WebSocket: Market data feeds.
- **Authentication & Security:**
  - Official Thailand flow: App Key, App Secret, signed requests (version/endpoint dependent), access tokens (not JWT), and initial production 2FA.
  - OpenAPI market data requires a separate subscription/permission independent of standard app/desktop market data entitlements (`WEBULL_OPENAPI_MARKET_DATA_ENTITLEMENT = SEPARATE_SUBSCRIPTION_OR_PERMISSION_REQUIRED`).
- **Security & Authorization Blocker:**
  - `WEBULL_BROKER_SIDE_READ_ONLY_KEY = NOT_PRIMARY_SOURCE_CONFIRMED`.
  - `WEBULL_READ_ONLY_INTEGRATION = BLOCKED_PENDING_SECURITY_DESIGN`.
  - Ingestion of Webull credentials into ACASH is strictly blocked until primary-source proof confirms that an API key can be generated with order-writing privileges technically disabled at the broker gateway.
  - `WEBULL_UAT = DOCUMENTED_NOT_AUTHORIZED_FOR_USE`.
  - Zero broker credentials exist or are stored in ACASH.

---

## 8. Futures Broker Due Diligence & CME Micro Universe

### 8.1 CME Micro Instrument Specifications (Verified CME Group Authority)
- **`MNQ` (Micro Nasdaq-100):** $2.00/pt, tick 0.25 pt ($0.50/tick), **Financial (Cash)** settlement.
- **`MES` (Micro S&P 500):** $5.00/pt, tick 0.25 pt ($1.25/tick), **Financial (Cash)** settlement.
- **`MCL` (Micro WTI Crude):** 100 bbl, tick $0.01 ($1.00/tick), **Financial (Cash)** settlement (NYMEX cash-settled against Light Sweet Crude).
- **`MGC` (Micro Gold):** 10 troy oz, tick $0.10 ($1.00/tick), **Physical Delivery** (COMEX-approved depositories).
- **`M6E` (Micro EUR/USD):** 12,500 EUR, tick 0.0001 ($1.25/tick), **Deliverable Currency** (CME FX delivery schedule).

### 8.2 Operational Delivery & Roll Boundaries
- **Delivery Risk Buffer:** `DELIVERY_RISK_BUFFER_POLICY = UNRATIFIED`. A software-enforced liquidation/roll buffer ahead of exchange delivery cutoffs is a proposed ACASH safety candidate policy, not an exchange rule. No fixed "3 business days" rule is ratified.
- **Continuous Roll Policy:** `FUTURES_CONTINUOUS_ROLL_POLICY = UNRESOLVED`. The "second Thursday" equity roll is an observed volume convention, not an exchange mandate. Backtests require an explicit pre-registered deterministic roll rule.
- **Cost & Margin Normalization:** `ALL_IN_COST = NOT_NORMALIZED`. Broker intraday day-margins ($50–$100) are volatile external parameters (`MARGIN_STATUS = VOLATILE_EXTERNAL_PARAMETER`); risk sizing is strictly decoupled from margin requirements.

### 8.3 Broker Candidate Classifications:
1. **Interactive Brokers (IBKR):** `LEADING_CANDIDATE_NOT_AUTHORIZED` — Thailand confirmed on official country directory; base micro commission $0.25/contract (Tiered schedule); no separate API access fee for standard accounts; subject to auth, market data, and gateway pacing limits (Web API 10 req/s or 50 req/min; TWS Lines/2 pacing). Retail Web API uses Client Portal Gateway; OAuth 2.0 direct API applies to licensed orgs/FAs; TWS API uses TWS/IB Gateway. Multi-currency wire and Wise integration supported; local Thai bank partner deposit rail is unconfirmed (`IBKR_LOCAL_THAI_BANK_RAIL = NOT_CONFIRMED`). Zero capital authorized.
2. **NinjaTrader / Tradovate:** `CANDIDATE_ON_HOLD` — Purpose-built futures scalper with ~$50 day margins and $0.39 micro commission, but **Thai resident onboarding is NOT confirmed by primary source** (`THAI_RESIDENT_NINJATRADER = NOT_CONFIRMED`) and retail REST API requires a funded LIVE account (> $1,000 equity) + paid API Access subscription (`TRADOVATE_RETAIL_API_ACCESS = FUNDED_LIVE_ACCOUNT_REQUIRED`).
3. **AMP Futures:** `REDUCED_FIT_CANDIDATE` — Dedicated discount FCM; Thailand is not on restricted list (`THAI_RESIDENT_AMP = ELIGIBLE_TO_APPLY_SUBJECT_TO_COMPLIANCE`). Reduced fit due to rigid broker risk policy prohibiting custom client-side daily loss limits in portal.
4. **Ironbeam:** `REDUCED_FIT_CANDIDATE` — Prohibitive $249/mo developer API fee on low-volume accounts (unattractive for shadow/read-only research; not a terminal governance disqualification).

> **GOVERNANCE INVARIANT:**
> `FUTURES_BROKER = CANDIDATE_IDENTIFIED`
> `IBKR = LEADING_CANDIDATE_NOT_AUTHORIZED`
> No broker is selected, authorized, or funded. Capital authority remains `$0.00`.

---

## 9. Thai Tax Evidence Ledger (2026 Guidelines)

- **Statutory Foundation:** Thai Revenue Code Section 41 Paragraph 3 (180-day residency test) + Departmental Orders Paw 161/2566 & Paw 162/2566.
- **Tax Liability Principle:** Foreign assessable income (realized capital gains, dividends) remitted into Thailand by a Thai tax resident is subject to Personal Income Tax (PIT). Form W-8BEN establishes foreign status to claim treaty benefit under US–Thailand DTA Article 10, which generally caps US gross dividend withholding at 15% for qualifying individual beneficial owners (and RIC distributions per para 3). W-8BEN is documentation, not a tax levy itself.
- **FX Valuation Method:** Thai Revenue Code Section 9 and MOF Notification allow commercial bank daily rate OR Bank of Thailand daily reference rate, subject to consistency requirements. Classified as **`TAX_FX_METHOD = HUMAN_PROFESSIONAL_POLICY_REQUIRED`**.
- **Cost Basis Determination:** Selection of FIFO, average cost, or specific lot accounting for foreign individual US equities requires qualified tax determination. Classified as **`TAX_COST_BASIS_METHOD = HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED`**. Full lot-level purchase and sale evidence is preserved.
- **Remittance Characterization:** Characterization of remitted capital vs assessable income requires legal/accounting review. The system preserves cash event and lot linkages via `RemittanceEvidenceLink` without asserting legal conclusions (`TAX_REMITTANCE_CHARACTERIZATION = HUMAN_PROFESSIONAL_REVIEW_REQUIRED`).
- **System Scope:** The PPDS tax module functions as an **EVIDENCE LEDGER ONLY**, not an autonomous tax engine.

---

## 10. Formally Preserved Source Conflicts & Resolved Items

1. **`DIME_FCD_VS_DIME_USD`:** Resolved as distinct account products (`RESOLVED_DISTINCT_PRODUCTS`). *(Pre-hardening state labeled as conflict is SUPERSEDED BY PASS #2).*
2. **`DIME_CAT_FEE`:** Conflicting CAT regulatory fee entries across published official Dime pages ($0.000046 vs $0.000003 per share, retrieved 2026-09-28). Maintained as `SOURCE_CONFLICT` and parameterized dynamically.
3. **`THAI_RESIDENT_NINJATRADER`:** Foreign clients accepted generally, but Thailand-specific KYC whitelist remains unverified (`NOT_CONFIRMED`).
4. **`TRADOVATE_RETAIL_API_ACCESS`:** Official Tradovate API docs require a funded LIVE account (> $1,000 equity) + API Access subscription (`FUNDED_LIVE_ACCOUNT_REQUIRED`). Free retail developer/simulation API access does not exist for un-funded retail accounts.
5. **`S2_GOVERNANCE_SEMANTICS`:** Stage S2 60 observed vs 60 contiguous calendar sessions remains on formal **HOLD**.

---

## 11. Human Policy Inputs Still Required

The personal capital split between Investment and Trading remains formally `UNRESOLVED` pending operator inputs:
- Total personal liquid net worth & untouchable emergency cash reserve floor.
- Capital commitments within 12, 24, and 36 months.
- Maximum acceptable Investment drawdown.
- Maximum Trading Book capital ceiling, daily loss stop, and maximum risk per trade.
- Futures overnight holding policy.
- Planned recurring monthly savings and remittance timelines.

---

## 12. Complete Files Created in this R0 Research Pack

All files authored under `docs/ppds/` on isolated branch `research/ppds-r0-capital-broker-architecture-20260928`:
1. `docs/ppds/SESSION_HANDOFF.md` (This master handoff)
2. `docs/ppds/PPDS_R0_RESEARCH_REGISTER.md` (Master claims, source tiers, conflict register)
3. `docs/ppds/PPDS_ARCHITECTURE_V1_DRAFT.md` (System architecture, multi-book model, state machine)
4. `docs/ppds/PERSONAL_CAPITAL_GOVERNANCE_V1_DRAFT.md` (Capital governance, human input ledger)
5. `docs/ppds/BROKER_ADAPTER_CONTRACT_V1_DRAFT.md` (Broker-neutral software interface, read-only gating)
6. `docs/ppds/DIME_2026_EXECUTION_AND_FEE_MODEL.md` (Dime fee schedule, Club Level 1, sliding commission, friction waterfall)
7. `docs/ppds/WEBULL_OPEN_API_FEASIBILITY_R0.md` (Webull Thailand Open API study, credential security)
8. `docs/ppds/FUTURES_BROKER_DUE_DILIGENCE_R0.md` (4-broker due diligence matrix, IBKR vs NinjaTrader)
9. `docs/ppds/FUTURES_INSTRUMENT_UNIVERSE_R0.md` (CME Micro specs, roll calendar, delivery prevention)
10. `docs/ppds/THAI_TAX_LEDGER_REQUIREMENTS_2026.md` (Thai RD 2026 guidelines, remittance engine, FX options)
11. `docs/ppds/PPDS_DATA_CONTRACT_V1_DRAFT.md` (Canonical domain entities, DTOs, double-entry schemas)
12. `docs/ppds/PPDS_R0_INDEPENDENT_EVIDENCE_AUDIT_20260928.md` (Independent evidence & semantic boundary audit)

---

## 13. Git Branch & Commit Ledger

- **Branch Name:** `research/ppds-r0-capital-broker-architecture-20260928`
- **Initial Handoff Commit SHA:** `f59b0d4578eafc69a52309c3de952c0e74fd95c4`
- **Initial R0 Research Commit SHA:** `5f99dedca90ef0b8f815402364e763507c3dfefd`
- **Corrective Commit Pass #1 SHA:** `59a8fb2c3b8e672f3bd036674cfb53a731fd2ff7`
- **Hardening Pass #2 Commit SHA:** `cd45b6afe8450b485bd6615eca597e2b0514ca55`
- **Lineage-Record Commit SHA:** `9c2610a5fbc423fa259df441033e11364975c959`
- **Base Tree:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (`origin/main`)
- **Merge Status:** **HOLD** (Zero PRs, zero merges into `main`).

---

## 14. Exact Next Human Actions

1. Await automated execution and sealing of **HYP_011 Observation #0001** (~03:10 ICT on 2026-09-29).
2. Execute the independent, read-only post-run audit via `docs/governance/preobs_audit_20260928/OBSERVATION_0001_POST_RUN_AUDIT_CHECKLIST.md`.
3. Review the 14 parameter inputs in `docs/ppds/PERSONAL_CAPITAL_GOVERNANCE_V1_DRAFT.md` to establish the personal capital ceiling and risk boundaries.
4. Adjudicate Stage S2 semantics (60 observed vs 60 contiguous calendar sessions).
5. Post-Observation: authorize merge of `docs/readme-math-render-fix-preobs-20260928` and evaluate Phase A repository ruleset activation.

---

## 15. R0 Corrective Audit Pass #1 — 2026-09-28 (Historical Record)

- **Starting Branch HEAD:** `5f99dedca90ef0b8f815402364e763507c3dfefd`
- **Corrective Commit SHA:** `59a8fb2c3b8e672f3bd036674cfb53a731fd2ff7`
- **Corrected Claims & Sourced Revisions (Historical Baseline):**
  1. **SEC Section 31 Fee:** Updated to statutory rate of **0.00206%** (USD 20.60 per USD 1,000,000 covered sales) effective 2026-04-04 per SEC Fee Rate Advisory FY2026 (Order 2026-2). Removed stale FY2025 rate (~0.00278%).
  2. **FINRA TAF Fee (Date-Effective Policy Model):** Codified as a date-effective schedule: $0.000195 through 2026-09-30; $0.00 from 2026-10-01 through 2026-12-31 (SEC Rel. 34-106409 / SR-FINRA-2026-021).
  3. **Dime CAT Fee:** Formalized as `SOURCE_CONFLICT` ($0.000046 vs $0.000003).
  4. **Tradovate / NinjaTrader API Economics:** Codified `TRADOVATE_RETAIL_API_ACCESS = FUNDED_LIVE_ACCOUNT_REQUIRED` (> $1,000 equity).
  5. **IBKR API Pacing & Gateway Distinctions:** Pacing limits documented (10 req/s, 50 req/min; Lines/2); Client Portal Gateway vs OAuth 2.0 vs TWS API delineated.
  6. **Tax Terminology (W-8BEN & US–Thailand Treaty):** W-8BEN documented as documentation claiming treaty benefits; Article 10 caps gross dividend withholding at 15%.
  7. **Broker Candidate Statuses:** Initial candidate classifications established.

---

## 16. Independent Evidence Hardening Pass #2 — 2026-09-28 (Authoritative Hardened State)

- **Starting Branch HEAD:** `59a8fb2c3b8e672f3bd036674cfb53a731fd2ff7`
- **Hardening Commit SHA:** `cd45b6afe8450b485bd6615eca597e2b0514ca55`
- **Audit Reference:** `docs/ppds/PPDS_R0_INDEPENDENT_EVIDENCE_AUDIT_20260928.md`
- **Research Churn Policy:** **`PPDS_R0_RESEARCH_CHURN = STOP`**
- **Exact Hardened Boundaries & Sourced Revisions:**
  1. **Dime FCD vs Dime USD Reconciled:** Replaced `SOURCE_CONFLICT` with `RESOLVED_DISTINCT_PRODUCTS`. Verified from official Dime documentation that Dime! FCD - USD is a bank foreign currency deposit account (KKP Bank, deposit interest, gold/US assets), whereas Dime! USD is a securities trading cash balance. Promotional eligibility variations across campaigns reflect distinct products, not a factual conflict.
  2. **Dime Sliding Commission 2026:** Modeled dynamic account-aware fee schedule per official Dime Club 2026 terms. US stock buy commissions are determined by prior-month cumulative trading value:
     - $\le$ THB 5,000,000: 0.15%
     - THB 5,000,001 – 20,000,000: 0.10%
     - > THB 20,000,000: 0.05%
     - US stock sell commission remains 0.15%; campaign benefits effective through December 2026.
     - Classified as `DIME_COMMISSION_MODEL = EFFECTIVE_DATED_ACCOUNT_SPECIFIC` and `DIME_EFFECTIVE_COMMISSION_RATE = ACCOUNT_STATE_REQUIRED`.
  3. **Dime Execution Assumptions Demoted:** Removed false precision from execution friction estimates (VOO 1-2 bps, small thematic 50-100 bps, FX drag 10-25 bps). Reclassified as `MODEL_ASSUMPTION_NOT_CALIBRATED`. Parameterized execution model without uncensored trend forecasts.
  4. **Webull Thailand Authentication & Transport:** Corrected authentication terminology to official App Key/App Secret, signed requests (version/endpoint dependent), access tokens (not JWT), and initial production 2FA. Corrected transport architecture: REST endpoints (`/trading/accounts/list`, `/trading/orders/...`), server-streaming **gRPC** for trade event updates, and WebSocket for market data. Codified separate market-data entitlement requirements.
  5. **Webull Read-Only Key & UAT:** Confirmed `WEBULL_BROKER_SIDE_READ_ONLY_KEY = NOT_PRIMARY_SOURCE_CONFIRMED`; retained `WEBULL_READ_ONLY_INTEGRATION = BLOCKED_PENDING_SECURITY_DESIGN`. Documented Webull Thailand UAT environment but classified `WEBULL_UAT = DOCUMENTED_NOT_AUTHORIZED_FOR_USE`.
  6. **Thai Tax Valuation Options:** Removed BOT-only hardcoding. Codified statutory options under Thai Revenue Code Section 9 and MOF notification: commercial bank daily rate OR Bank of Thailand daily reference rate, subject to consistency. Classified `TAX_FX_METHOD = HUMAN_PROFESSIONAL_POLICY_REQUIRED`.
  7. **Tax Cost Basis & Remittance Matching:** Decoupled FIFO / average cost assertions from statutory foreign equity tax law (`TAX_COST_BASIS_METHOD = HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED`; full lot lineage preserved). Replaced legal remittance claims with `RemittanceEvidenceLink` preserving empirical cash/lot events without asserting binding legal truth (`TAX_REMITTANCE_CHARACTERIZATION = HUMAN_PROFESSIONAL_REVIEW_REQUIRED`).
  8. **Data Contract Design Intent vs Runtime Truth:** Clarified that serialization, hash chains, and fail-closed runtime behaviors are design invariants, not implemented code (`PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED`). Split `RecommendationSnapshot` into `InvestmentRecommendationDTO` (thesis & fundamental reviews, no price stops) and `TradingRecommendationDTO` (entry, price stops, dollar risk).
  9. **Portfolio Classification Neutrality:** Reclassified existing portfolio holdings (VOO, QQQM, TSM, PLTR, NOW, RKLB, RDW, SATL) as `ILLUSTRATIVE_EXISTING_HOLDING` / `BOOK_ASSIGNMENT_UNRATIFIED`. Labeled multi-year horizons and benchmarks as `CANDIDATE_POLICY_UNRATIFIED`. Enforced baseline `NO_AUTHORIZED_TRADING_STRATEGY` / `NO_TRADE` for the Trading Book.
  10. **Futures Market Structure & Settlement:** Rewrote CFD comparison to objective market-structure differences (clearing house vs bilateral OTC; broker credit/custody risk acknowledged). Reverified CME micro contract specifications: `MNQ`, `MES`, and `MCL` are **Financial (Cash)** settled; `MGC` is Physical Delivery (COMEX); `M6E` is Deliverable Currency (CME FX).
  11. **Futures Delivery Buffer & Roll Conventions:** Separated CME exchange notice/delivery rules from proposed ACASH safety buffers (`DELIVERY_RISK_BUFFER_POLICY = UNRATIFIED`). Decoupled "second Thursday" volume convention from continuous roll policy (`FUTURES_CONTINUOUS_ROLL_POLICY = UNRESOLVED`).
  12. **Futures Broker Costs & Margins:** Replaced cross-broker all-in costs with `ALL_IN_COST = NOT_NORMALIZED` and established standardized round-trip comparison template. Classified broker day margins as `MARGIN_STATUS = VOLATILE_EXTERNAL_PARAMETER` (sizing strictly decoupled from day-margin). Classified `IBKR_LOCAL_THAI_BANK_RAIL = NOT_CONFIRMED`. Clarified `THAI_RESIDENT_AMP = ELIGIBLE_TO_APPLY_SUBJECT_TO_COMPLIANCE`. Removed marketing adjectives.
