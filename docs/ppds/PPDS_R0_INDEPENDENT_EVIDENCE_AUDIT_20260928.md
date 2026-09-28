# ACASH PPDS R0 Independent Evidence & Semantic Boundary Audit (Pass #2)

**Document:** `docs/ppds/PPDS_R0_INDEPENDENT_EVIDENCE_AUDIT_20260928.md`
**System Module:** Personal Portfolio Decision Support (PPDS)
**Audit Type:** Independent Evidence Hardening & Semantic Demarcation Audit
**Stage:** R0 Architecture & Broker Due Diligence
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda)

---

## 1. Audit Base & Environment Boundary

- **Canonical Main Reference SHA:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`
- **Branch Start HEAD (Pre-Pass #2):** `59a8fb2c3b8e672f3bd036674cfb53a731fd2ff7`
- **Branch Tracking:** `research/ppds-r0-capital-broker-architecture-20260928`
- **Isolation Scope:** `docs/ppds/**` ONLY
- **Capital & Trading Authority:**
  - `REAL_ORDER_AUTHORITY = NONE`
  - `PAPER_TRADING_AUTHORITY = NONE`
  - `LIVE_TRADING_AUTHORITY = NONE`
  - `CAPITAL_AUTHORITY = $0.00`
  - `NO_REAL_ORDERS = true`
- **Target Invariant:** Zero mutation to `src/**`, `tests/**`, `HYP_011`, homelab, systemd, or live production state.

---

## 2. Documents Audited (All 11 PPDS Documents)

1. `docs/ppds/PPDS_CHARTER_AND_SCOPE_R0.md`
2. `docs/ppds/PPDS_ARCHITECTURE_V1_DRAFT.md`
3. `docs/ppds/PPDS_DATA_CONTRACT_V1_DRAFT.md`
4. `docs/ppds/BROKER_ADAPTER_CONTRACT_V1_DRAFT.md`
5. `docs/ppds/DIME_2026_EXECUTION_AND_FEE_MODEL.md`
6. `docs/ppds/WEBULL_OPEN_API_FEASIBILITY_R0.md`
7. `docs/ppds/FUTURES_BROKER_DUE_DILIGENCE_R0.md`
8. `docs/ppds/FUTURES_INSTRUMENT_UNIVERSE_R0.md`
9. `docs/ppds/THAI_TAX_LEDGER_REQUIREMENTS_2026.md`
10. `docs/ppds/PPDS_R0_RESEARCH_REGISTER.md`
11. `docs/ppds/SESSION_HANDOFF.md`

---

## 3. Findings Ledger

| Finding ID | Severity | File | Specific Claim / Issue | Primary Authority | Status Pre-Pass #2 | Resolution in Pass #2 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FND-01** | MEDIUM | `DIME_2026_EXECUTION_AND_FEE_MODEL.md` | "Dime! FCD vs Dime! USD" labeled as an irreconcilable source conflict. | Dime! Official Product Disclosures (2026) | `SOURCE_CONFLICT` | **RESOLVED**: Verified as distinct account products (bank FCD deposit account vs securities trading wallet). Reconciled without conflict. |
| **FND-02** | HIGH | `DIME_2026_EXECUTION_AND_FEE_MODEL.md` | Flat 0.15% commission assumed without modeling official Dime Club Sliding Commission 2026. | Dime! Official Dime Club Sliding Commission Rules | Unmodeled | **CORRECTED**: Codified monthly volume-based tiered BUY commissions (<=5m: 0.15%, 5m-20m: 0.10%, >20m: 0.05%; sell 0.15%; effective through Dec 2026). Parameterized as `DIME_EFFECTIVE_COMMISSION_RATE = ACCOUNT_STATE_REQUIRED`. |
| **FND-03** | MEDIUM | `DIME_2026_EXECUTION_AND_FEE_MODEL.md` | Static bid/ask spread estimates (1-2 bps, 50-100 bps) and FX drag (10-25 bps) presented as empirical facts. | None (Engineering heuristic) | Presented as fact | **DEMOTED**: Classified as `MODEL_ASSUMPTION_NOT_CALIBRATED`. False precision removed; execution optimizer parameterized. |
| **FND-04** | HIGH | `WEBULL_OPEN_API_FEASIBILITY_R0.md` | Inaccurate auth terminology ("dynamic JWT") and missing Thailand-specific onboarding workflow. | Webull Securities (Thailand) Developer Portal | Inaccurate | **CORRECTED**: Detailed Thailand App Key/App Secret, signed requests, access tokens (not JWT), and initial production 2FA requirement. |
| **FND-05** | MEDIUM | `WEBULL_OPEN_API_FEASIBILITY_R0.md` | Hardcoded signature algorithm as HMAC-SHA256 across all endpoints. | Webull Thailand Developer Docs | Hardcoded | **PARAMETERIZED**: Classified as `WEBULL_SIGNATURE_ALGORITHM = VERSION_OR_ENDPOINT_DEPENDENT`. |
| **FND-06** | HIGH | `WEBULL_OPEN_API_FEASIBILITY_R0.md` | Real-time communication labeled entirely as WebSocket; order paths generic. | Webull Thailand API Specs | Inaccurate transport | **CORRECTED**: Delineated REST endpoints (`/trading/accounts/list`, `/trading/orders/...`), server-streaming **gRPC** for trade events, and WebSocket for market data. |
| **FND-07** | MEDIUM | `WEBULL_OPEN_API_FEASIBILITY_R0.md` | App market data assumed identical to OpenAPI market data. | Webull Thailand Market Data Policy | Conflated | **DISENTANGLED**: Added `WEBULL_OPENAPI_MARKET_DATA_ENTITLEMENT = SEPARATE_SUBSCRIPTION_OR_PERMISSION_REQUIRED`. |
| **FND-08** | CRITICAL | `WEBULL_OPEN_API_FEASIBILITY_R0.md` | Lack of primary-source proof for individual broker-side read-only permission scoping. | Webull Thailand Developer Portal | Ambiguous | **HARDENED GATE**: Confirmed `WEBULL_BROKER_SIDE_READ_ONLY_KEY = NOT_PRIMARY_SOURCE_CONFIRMED`; retained `WEBULL_READ_ONLY_INTEGRATION = BLOCKED_PENDING_SECURITY_DESIGN`. |
| **FND-09** | MEDIUM | `WEBULL_OPEN_API_FEASIBILITY_R0.md` | UAT/test environment referenced ambiguously. | Webull Thailand UAT Docs | Ambiguous | **DOCUMENTED**: Codified UAT specs and classified `WEBULL_UAT = DOCUMENTED_NOT_AUTHORIZED_FOR_USE`. |
| **FND-10** | HIGH | `THAI_TAX_LEDGER_REQUIREMENTS_2026.md` | Thai tax FX conversion hardcoded exclusively to Bank of Thailand reference rate. | Thai Revenue Code § 9; MOF Notification on Exchange Rates | Hardcoded | **CORRECTED**: Codified statutory options (commercial bank daily rate vs BOT daily reference rate) with consistency requirement. `TAX_FX_METHOD = HUMAN_PROFESSIONAL_POLICY_REQUIRED`. |
| **FND-11** | HIGH | `THAI_TAX_LEDGER_REQUIREMENTS_2026.md` | FIFO / Average Cost implied as mandatory statutory tax methods for foreign US equities. | Thai Revenue Department Practice | Asserted as rule | **DECOUPLED**: Clarified absence of explicit statutory mandate for foreign individual stocks; classified `TAX_COST_BASIS_METHOD = HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED`. Full lot lineage preserved. |
| **FND-12** | HIGH | `THAI_TAX_LEDGER_REQUIREMENTS_2026.md` | Pro-Rata / Specific Identification presented as legally ratified remittance allocation methods. | Thai Revenue Department Orders 161/162 | Asserted as rule | **REFRAMED**: Established `RemittanceEvidenceLink` to preserve empirical event lineage without asserting binding legal truth; `TAX_REMITTANCE_CHARACTERIZATION = HUMAN_PROFESSIONAL_REVIEW_REQUIRED`. |
| **FND-13** | HIGH | `PPDS_DATA_CONTRACT_V1_DRAFT.md` | Runtime implementation claims written as active reality ("DTOs serialize deterministically", etc.). | Repository State | Active claim | **CORRECTED**: Labeled as `TARGET_DESIGN_INVARIANT` and explicit `PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED`. |
| **FND-14** | MEDIUM | `PPDS_DATA_CONTRACT_V1_DRAFT.md` | RecommendationSnapshot enforced trading-centric price stops for long-term investments. | Financial Domain Separation | Over-constrained | **SPLIT**: Partitioned into `InvestmentRecommendationDTO` (thesis, fundamental review triggers, allocation envelopes) and `TradingRecommendationDTO` (entry, price invalidation, dollar risk). |
| **FND-15** | MEDIUM | `PPDS_ARCHITECTURE_V1_DRAFT.md` | Existing portfolio holdings (VOO, QQQM, TSM, PLTR, etc.) written as ratified book assignments. | Operator Working Portfolio | Conflated | **DECOUPLED**: Labeled as `ILLUSTRATIVE_EXISTING_HOLDING` / `BOOK_ASSIGNMENT_UNRATIFIED` to prevent confirmation bias. |
| **FND-16** | MEDIUM | `PPDS_ARCHITECTURE_V1_DRAFT.md` | Candidate investment horizons (3-10+ yrs) and benchmarks (ACWI, S&P 500) written as active policy. | Operator Decision Charter | Candidate written as active | **CORRECTED**: Explicitly marked `CANDIDATE_POLICY_UNRATIFIED`. Capital allocation policy remains `UNRESOLVED`. |
| **FND-17** | HIGH | `PPDS_ARCHITECTURE_V1_DRAFT.md` | Trading Book described as possessing active alpha/inefficiency exploitation edges. | Hypotheses Framework | Unsubstantiated assertion | **CORRECTED**: Enforced baseline `NO_AUTHORIZED_TRADING_STRATEGY` / `NO_TRADE`. |
| **FND-18** | HIGH | `FUTURES_INSTRUMENT_UNIVERSE_R0.md` | Categorical claims against CFDs ("always B-books", "zero broker credit risk for CME"). | Market Structure Reality | Categorical | **NEUTRALIZED**: Rewritten to objective market-structure comparisons (central clearing vs bilateral contracts; solvency/custody risk acknowledged). |
| **FND-19** | HIGH | `FUTURES_INSTRUMENT_UNIVERSE_R0.md` | Micro Crude (`MCL`) described alongside physically delivered contracts. | CME NYMEX Rulebook | Inaccurate settlement | **CORRECTED**: Verified `MCL` as **Financial (Cash)** settlement. `MGC` verified as Physical Delivery (COMEX) and `M6E` as Deliverable Currency (CME FX). |
| **FND-20** | MEDIUM | `FUTURES_INSTRUMENT_UNIVERSE_R0.md` | Operational cutoff ("3 business days before FND") written as exchange contract law. | ACASH System Design | Asserted as law | **DECOUPLED**: Separated CME exchange notice/delivery rules from proposed system buffer (`DELIVERY_RISK_BUFFER_POLICY = UNRATIFIED`). |
| **FND-21** | MEDIUM | `FUTURES_INSTRUMENT_UNIVERSE_R0.md` | "Roll second Thursday" asserted as universal contract rule. | Market Practice | Asserted as rule | **PARAMETERIZED**: Market volume convention decoupled from policy (`FUTURES_CONTINUOUS_ROLL_POLICY = UNRESOLVED`). |
| **FND-22** | LOW | `FUTURES_INSTRUMENT_UNIVERSE_R0.md` | Static notional dollar figures ($400k, $40k) written as fixed contract properties. | CME Contract Formulas | Static constant | **CORRECTED**: Defined as dynamic function `Notional = Price × Multiplier` with snapshot timestamps. |
| **FND-23** | MEDIUM | `FUTURES_BROKER_DUE_DILIGENCE_R0.md` | Cross-broker all-in round-turn costs ($1.00-$1.20, etc.) presented as comparable facts. | FCM Pricing Schedules | Un-normalized | **CORRECTED**: Classified `ALL_IN_COST = NOT_NORMALIZED`. Standardized round-trip evaluation template established. |
| **FND-24** | MEDIUM | `FUTURES_BROKER_DUE_DILIGENCE_R0.md` | Intraday day margins ($50, $100) presented as static risk parameters. | FCM Margin Disclosures | Static constant | **PARAMETERIZED**: Classified `MARGIN_STATUS = VOLATILE_EXTERNAL_PARAMETER`. Sizing decoupled from broker day-margin. |
| **FND-25** | MEDIUM | `FUTURES_BROKER_DUE_DILIGENCE_R0.md` | "Local Thai Bank via partner rails" claimed for IBKR funding. | IBKR Official Help Center | Unconfirmed claim | **CORRECTED**: Confirmed Wise and international wire; classified `IBKR_LOCAL_THAI_BANK_RAIL = NOT_CONFIRMED`. |
| **FND-26** | MEDIUM | `FUTURES_BROKER_DUE_DILIGENCE_R0.md` | AMP Futures Thai eligibility implied as guaranteed approval. | AMP International Policy | Implied guarantee | **CORRECTED**: Clarified `THAI_RESIDENT_AMP = ELIGIBLE_TO_APPLY_SUBJECT_TO_COMPLIANCE`. |
| **FND-27** | LOW | `FUTURES_BROKER_DUE_DILIGENCE_R0.md` | Promotional adjectives used ("unmatched global financial strength", etc.). | Style Guidelines | Marketing prose | **NEUTRALIZED**: Replaced with factual, verifiable institutional metrics. Overall `FUTURES_BROKER = CANDIDATE_IDENTIFIED`. |
| **FND-28** | MEDIUM | `BROKER_ADAPTER_CONTRACT_V1_DRAFT.md` | Webull transport described as pure REST/WebSocket; runtime invariants presented as live code. | Webull Docs / System State | Inaccurate / Active claim | **CORRECTED**: Corrected transport to REST + gRPC trade streaming + WebSocket market data. Labeled `PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED`. |
| **FND-29** | HIGH | `SESSION_HANDOFF.md` | Commit lineage contained stale placeholders (`*(Recorded upon final commit)*`). | Git History | Stale placeholder | **CORRECTED**: Codified full verifiable commit lineage from seed through Pass #1. Pass #2 parent anchored to `59a8fb2c3b8e672f3bd036674cfb53a731fd2ff7`. |

---

## 4. Corrected Claims Summary

1. **Dime Product Distinction:** Dime! FCD - USD is a bank deposit product; Dime! USD is a securities trading cash balance. Promotional eligibility divergences are reconciled without conflict.
2. **Dime Sliding Commission 2026:** Modeled account-aware tiered buy commission (0.15% / 0.10% / 0.05%) based on cumulative monthly volume, effective through Dec 2026.
3. **Webull Authentication & Architecture:** App Key/App Secret, signed requests, access tokens, production 2FA, REST + gRPC trade event streaming + WebSocket market data, and separate market data entitlement.
4. **Thai Tax Valuation Options:** Codified Revenue Code § 9 choice between commercial bank daily rate and BOT daily reference rate with consistency requirement.
5. **CME Contract Settlement:** Verified `MCL` as financial cash settlement (NYMEX); `MGC` as physical delivery (COMEX); `M6E` as deliverable currency (CME FX).
6. **Decoupled Safety Buffers & Roll Conventions:** Separated CME exchange rules from ACASH candidate safety buffers (e.g. roll before FND) and volume rollover conventions.
7. **Broker Due Diligence Disentanglement:** Demoted un-normalized all-in costs and volatile margins; unconfirmed IBKR local Thai bank rail; confirmed AMP eligibility to apply.

---

## 5. Remaining Unresolved Claims & Open Investigation Items

1. **`DIME_CAT_FEE`:** Retained as `SOURCE_CONFLICT` ($0.000046 vs $0.000003 per share across active official pages).
2. **`THAI_RESIDENT_NINJATRADER`:** Retained as `BLOCKED` / `NOT_CONFIRMED` pending primary-source whitelist documentation.
3. **`IBKR_LOCAL_THAI_BANK_RAIL`:** Retained as `NOT_CONFIRMED` pending primary documentation of direct Thai bank partner deposit rails.

---

## 6. Model Assumptions Not Yet Calibrated

1. **`DIME_EXECUTION_SPREAD_MODEL`:** VOO/QQQM spread (1-2 bps), thematic stock spread (50-100 bps), and FX conversion drag (10-25 bps) are engineering heuristics requiring empirical tick/quote calibration.
2. **`FUTURES_ALL_IN_COST_MODEL`:** Cross-broker fee totals require contemporaneous multi-component calculation against identical contracts.

---

## 7. Operator Policy Inputs Required

1. **`PERSONAL_CAPITAL_ALLOCATION_POLICY`:** Capital allocation between Core Long-Term Investment Book and Trading Books remains `UNRESOLVED`.
2. **`CURRENT_HOLDINGS_BOOK_ASSIGNMENT`:** Formal assignment of existing positions (VOO, QQQM, TSM, PLTR, NOW, RKLB, RDW, SATL) to books is `UNRATIFIED`.
3. **`INVESTMENT_BENCHMARK_POLICY`:** Benchmarks (e.g. S&P 500, ACWI, Blended 80/20) remain `CANDIDATE_POLICY_UNRATIFIED`.

---

## 8. Implementation Claims Not Yet Implemented

1. **`PPDS_RUNTIME_IMPLEMENTATION`:** Data models, serialization, hash-chains, and broker adapters are draft specifications; runtime code is `NOT_IMPLEMENTED`.
2. **`WEBULL_UAT_TELEMETRY`:** Webull UAT environment is documented for research but `NOT_AUTHORIZED_FOR_USE`.

---

## 9. Security & Governance Gates

### 9.1 Broker Security Gates
- **`WEBULL_BROKER_SIDE_READ_ONLY_KEY`:** `NOT_PRIMARY_SOURCE_CONFIRMED`.
- **`WEBULL_READ_ONLY_INTEGRATION`:** `BLOCKED_PENDING_SECURITY_DESIGN`.
- A client-side HTTP proxy allowlisting GET requests is defense-in-depth, not equivalent to a broker-enforced read-only API key.

### 9.2 Tax Professional-Review Gates
- **`TAX_FX_METHOD`:** `HUMAN_PROFESSIONAL_POLICY_REQUIRED`.
- **`TAX_COST_BASIS_METHOD`:** `HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED` (FIFO, average, or specific lot selection for foreign equities).
- **`TAX_REMITTANCE_CHARACTERIZATION`:** `HUMAN_PROFESSIONAL_REVIEW_REQUIRED` (Characterization of foreign capital vs assessable income remittances under RD Orders 161/162).

### 9.3 Futures Contract & Delivery Gates
- **`DELIVERY_RISK_BUFFER_POLICY`:** `CANDIDATE_POLICY_UNRATIFIED` (Software liquidation/roll buffer prior to exchange FND / delivery termination).
- **`FUTURES_CONTINUOUS_ROLL_POLICY`:** `UNRESOLVED` (Deterministic roll rule required prior to production backtesting).
- **`FUTURES_BROKER`:** `CANDIDATE_IDENTIFIED` (IBKR leading candidate; zero capital authorized).

---

## 10. Final Audit Classification

```text
=================================================================
PPDS R0 INDEPENDENT EVIDENCE AUDIT CLASSIFICATION:
STATUS: PASS_WITH_UNRESOLVED_GATES
=================================================================
- IMPLEMENTATION TRUTH: PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED
- CAPITAL AUTHORITY: $0.00 (NO REAL ORDERS)
- EXECUTION PERMISSIONS: ZERO (ALL GATES HARD-LOCKED TO FALSE)
- CANONICAL MAIN BRANCH: UNTOUCHED (d9608c0a2353bd5ed41943e5fb893ef9648089d2)
- PRODUCTION EXECUTION / HYP_011: UNTOUCHED
- EVIDENCE RIGOR: PRIMARY-SOURCE ALIGNED & DEMARCATED
=================================================================
```
