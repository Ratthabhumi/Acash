# ACASH PPDS Session Handoff (R0 Architecture & Research Complete)

**Document:** `docs/ppds/SESSION_HANDOFF.md`
**System Module:** Personal Portfolio Decision Support (PPDS)
**Research Stage:** R0 Architecture, Due Diligence & Data Contracts
**Branch:** `research/ppds-r0-capital-broker-architecture-20260928`
**Base Canonical Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda)

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
All portfolio and sizing models drafted in this research phase represent accounting normalization and simulation logic only. The system has zero real trading authority, zero broker order placement capability, and zero live execution access.

---

## 2. Canonical Repository State & Pre-Observation Freeze

- **Canonical Main Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (Verified unchanged on `origin/main`).
- **HYP_011 Observation #0001 Integrity:** Completely frozen and untouched.
  - Target Session: `2026-09-28` (NYSE Regular Session).
  - Eligibility Cutoff: Strictly after `20:00:00 UTC` (`2026-09-28T20:00:00Z`).
  - Automated Timer: `acash-hyp011-observation-0001.timer` scheduled for ~`03:10 ICT` on `2026-09-29`.
  - Zero modification to homelab, service, wrapper, timer, prospective state files, or live broker configurations.

---

## 3. PPDS Mission & Core Philosophy

ACASH is expanding into a sovereign, broker-neutral **Capital Allocator and Decision Support System**.
- **Not an automated stock picker:** It does not blindly generate buy signals or force capital deployment.
- **Core Decision Mandate:** Answers whether new capital should remain `CASH` or be deployed into specific books (Investment Core/DCA, Satellite Conviction, Speculative Thematic, Equity Tactical, or Futures Macro).
- **First-Class Cash Allocation:** `NO_QUALIFIED_OPPORTUNITY -> HOLD_CASH` is a prioritized, fully valid system state.

---

## 4. Working Personal Portfolio Inventory (Non-Canonical Baseline)

*Notice: Ingested from operator descriptions and UI screenshots. Real cost-basis lots require official broker statement exports.*

| Portfolio Segment | Observed Holdings | Approximate Value / Magnitude | Custodian |
| :--- | :--- | :--- | :--- |
| **Long-Term / Growth** | `QQQM`, `VOO`, `PLTR`, `TSM`, `SOFI`, `NOW` | ~THB 69,465 | Dime! (KKP) |
| **Thematic / Space** | `SATL`, `RKLB`, `RDW`, `ITA`, `NASA`, `SIDU` | Discretionary Speculative | Dime! (KKP) |
| **Observed Bucket Labels**| "long-term growth", "space/thematic", "Sniper", "Trump Buy", "NBIS" | Total order of ~THB 100k | Dime! (KKP) |
| **Dime FCD Cash** | USD balance in Dime! FCD | ~USD 2,696.69 (~THB 90k at screenshot FX) | Dime! (KKP) |
| **Liquid THB Cash** | THB cash balance | ~THB 9,000 | Dime! (KKP) / Bank |

---

## 5. Multi-Book Architecture Summary

```text
PERSONAL CAPITAL
├── INVESTMENT BOOK (Generational wealth compounding, low turnover, benchmarked)
│   ├── CORE / DCA (Market & factor ETFs: VOO, QQQM)
│   ├── SATELLITE / CONVICTION (Quality businesses with verified thesis: TSM, PLTR)
│   └── SPECULATIVE / THEMATIC (High-narrative themes: Space tech; bounded cap)
└── TRADING BOOK (Tactical asymmetry, absolute return, active risk management)
    ├── EQUITY TACTICAL / SNIPER (Event-driven equity setups, Webull candidate)
    └── FUTURES / MACRO (Regulated CME Micro contracts: MNQ, MES, MGC, MCL, M6E)
```

**Anti-Contagion Rules:**
- Investment and Trading ledgers are completely decoupled.
- Trading drawdowns never draw capital or margin from the Investment Book.
- Inter-book capital transfers require explicit operator authorization records.

---

## 6. Dime! (KKP) Research & Execution Model

- **Standard Fees:** 0.15% commission (no minimum fee per trade) + 7% VAT on commission; first trade of each calendar month is commission-free.
- **Dime Club Level 1 Free Trade Day:**
  - Published schedule verified **through 30 September 2026** (dynamic promotional calendar, not guaranteed indefinitely).
  - US window: strictly **22:00 – 23:50 ICT**.
  - Eligible orders: BUY Market Orders specifying THB or USD amount (funded from Dime! FCD).
- **Execution Cost Waterfall:** Total friction includes commission + VAT + SEC (sales) + TAF (sales) + CAT + spread + slippage + FX + timing cost.
- **Timing vs. Commission Trade-off:** Never delay an accumulation trade for 10–14 days solely to save a 0.15% commission if expected timing/volatility risk exceeds the savings.

---

## 7. Webull Securities (Thailand) Open API Research

- **API Scope:** Trading, Market Data, Account telemetry, WebSocket streaming, historical data.
- **Commercial Cost:** Advertised as free ($0 API fees) at present.
- **Security Blocker:**
  - `WEBULL_READ_ONLY_INTEGRATION = BLOCKED_PENDING_SECURITY_DESIGN`
  - Ingestion of Webull credentials into ACASH is strictly blocked until official proof confirms that an API key can be generated with order-writing privileges technically disabled.

---

## 8. Futures Broker Due Diligence & CME Micro Universe

### CME Micro Instrument Specs:
- **`MNQ` (Micro Nasdaq-100):** $2.00/pt, tick 0.25 pt ($0.50/tick), cash-settled.
- **`MES` (Micro S&P 500):** $5.00/pt, tick 0.25 pt ($1.25/tick), cash-settled.
- **`MGC` (Micro Gold):** 10 troy oz, tick $0.10 ($1.00/tick), physically deliverable (mandatory roll/liquidation 3 days before First Notice Date).
- **`MCL` (Micro WTI Crude):** 100 bbl, tick $0.01 ($1.00/tick), cash-settled.
- **`M6E` (Micro EUR/USD):** 12,500 EUR, tick 0.0001 ($1.25/tick), physically deliverable (mandatory roll before expiration).

### Broker Ranking for Future Implementation:
1. **Interactive Brokers (IBKR) — Ranked #1:** Thailand confirmed on official country directory; micro commission $0.25/contract; free robust API; established Wise/wire rails. Conservative intraday margins.
2. **NinjaTrader / Tradovate — Ranked #2 (On Hold):** Purpose-built futures scalper with ~$50 day margins and $0.39 micro commission, but **Thai resident onboarding is NOT confirmed by primary source**.
3. **AMP Futures — Ranked #3:** Dedicated discount FCM, but restricts custom client-side daily loss limits.
4. **Ironbeam — Ranked #4 (Disqualified):** Prohibitive $249/mo developer API fee on inactive accounts.

---

## 9. Thai Tax Evidence Ledger (2026 Guidelines)

- **Statutory Foundation:** Thai Revenue Code Section 41 Paragraph 3 (180-day residency test) + Departmental Orders Paw 161/2566 & Paw 162/2566.
- **Tax Liability Principle:** Foreign assessable income (realized capital gains, dividends) remitted into Thailand by a Thai tax resident is subject to Personal Income Tax (PIT), with Foreign Tax Credits (FTC) applicable for US withholding taxes (W-8BEN 15%) under the US–Thai DTA.
- **Broker Neutrality:** Broker choice does not determine tax status; assessable income realization and remittance determine liability.
- **Status:** `TAX_INTERPRETATION_REQUIRES_HUMAN/PROFESSIONAL_REVIEW = true`. Ledger provides double-entry evidence exports for human and CPA review.

---

## 10. Formally Preserved Source Conflicts

1. **`DIME_FCD_VS_DIME_USD`:** Promotional fine print in Payday campaigns excludes "Dime! USD", while the Club terms allow "Dime! FCD". Preserved without forced reconciliation.
2. **`DIME_CAT_FEE`:** Conflicting CAT regulatory fee entries across published Dime pages. Parameterized dynamically.
3. **`THAI_RESIDENT_NINJATRADER`:** Foreign clients accepted generally, but Thailand-specific KYC whitelist remains unverified.
4. **`S2_GOVERNANCE_SEMANTICS`:** Stage S2 60 observed vs 60 contiguous calendar sessions remains on formal **HOLD**.

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
6. `docs/ppds/DIME_2026_EXECUTION_AND_FEE_MODEL.md` (Dime fee schedule, Club Level 1, friction waterfall)
7. `docs/ppds/WEBULL_OPEN_API_FEASIBILITY_R0.md` (Webull Thailand Open API study, credential security)
8. `docs/ppds/FUTURES_BROKER_DUE_DILIGENCE_R0.md` (4-broker due diligence matrix, IBKR vs NinjaTrader)
9. `docs/ppds/FUTURES_INSTRUMENT_UNIVERSE_R0.md` (CME Micro specs, roll calendar, delivery prevention)
10. `docs/ppds/THAI_TAX_LEDGER_REQUIREMENTS_2026.md` (Thai RD 2026 guidelines, remittance engine)
11. `docs/ppds/PPDS_DATA_CONTRACT_V1_DRAFT.md` (Canonical domain entities, DTOs, double-entry schemas)

---

## 13. Git Branch & Commit Ledger

- **Branch Name:** `research/ppds-r0-capital-broker-architecture-20260928`
- **Initial Handoff Commit SHA:** `f59b0d4578eafc69a52309c3de952c0e74fd95c4`
- **Final R0 Research Commit SHA:** *(Recorded upon final commit)*
- **Base Tree:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (`origin/main`)
- **Merge Status:** **HOLD** (Zero PRs, zero merges into `main`).

---

## 14. Exact Next Human Actions

1. Await automated execution and sealing of **HYP_011 Observation #0001** (~03:10 ICT on 2026-09-29).
2. Execute the independent, read-only post-run audit via `docs/governance/preobs_audit_20260928/OBSERVATION_0001_POST_RUN_AUDIT_CHECKLIST.md`.
3. Review the 14 parameter inputs in `docs/ppds/PERSONAL_CAPITAL_GOVERNANCE_V1_DRAFT.md` to establish the personal capital ceiling and risk boundaries.
4. Adjudicate Stage S2 semantics (60 observed vs 60 contiguous calendar sessions).
5. Post-Observation: authorize merge of `docs/readme-math-render-fix-preobs-20260928` and evaluate Phase A repository ruleset activation.
