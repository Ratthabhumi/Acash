# ACASH PPDS Session Handoff (R0 Inception)

**Document:** `docs/ppds/SESSION_HANDOFF.md`  
**System Module:** ACASH Personal Portfolio Decision Support (PPDS)  
**Research Stage:** R0 Architecture & Broker Due Diligence  
**Branch:** `research/ppds-r0-capital-broker-architecture-20260928`  
**Base Canonical Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`  
**Date Context:** 2026-09-28  
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda)

---

## 1. Governance & Authority Boundaries (Strict Non-Negotiable)

In strict accordance with the ACASH Operator Decision Charter:
- **`REAL_CAPITAL_AUTHORITY`:** `$0.00` (Strictly Locked)
- **`PAPER_TRADING_AUTHORITY`:** `false`
- **`LIVE_TRADING_AUTHORITY`:** `false`
- **`NO_REAL_ORDERS`:** `true`
- **Order-Writing Capability:** Zero real orders, zero fills, zero capital movement, zero automated rebalancing.
- **Simulated Capital:** All numerical portfolio modeling in PPDS R0 is accounting normalization only. Simulated values must never be interpreted as real trading authorization.

---

## 2. Pre-Observation HYP_011 Execution Path Freeze

The canonical research event **HYP_011 / CORE-001 Observation #0001** is completely frozen on canonical `main` (`d9608c0a...`):
- **Target Session:** `2026-09-28` (NYSE Regular Trading Session)
- **Close Boundary:** `2026-09-28T20:00:00Z`
- **Automated Timer Dispatch:** `acash-hyp011-observation-0001.timer` scheduled for ~`03:10 ICT` on `2026-09-29` (`20:10 UTC` on `2026-09-28`).
- **Isolation Invariant:** PPDS R0 development is strictly isolated on branch `research/ppds-r0-capital-broker-architecture-20260928`. Zero changes to `main`, homelab services, timers, wrappers, environment variables, or observation state files are permitted.

---

## 3. PPDS Mission & Core Architecture Intent

ACASH is expanding beyond backtesting into a broker-neutral:
1. **Capital Allocator:** Decision engine evaluating whether new funds should remain cash or be deployed into specific books.
2. **Portfolio Decision Support System (PPDS):** Multi-book hierarchy separating Investment from Trading.
3. **Risk Engine:** Consolidated portfolio-level exposure, overlap, liquidity, and single-name risk monitoring.
4. **Broker Reconciliation Layer:** Standardized ledger reconciling multi-broker statements, fills, transactions, and FX.
5. **Tax & Evidence Ledger:** Evidence export layer supporting Thai Revenue Department 2026 overseas income/remittance compliance.

**Core Philosophy:** ACASH is **NOT** an automated stock picker. It answers:
- Should capital remain `CASH` or be deployed?
- Does capital belong to Investment (Core/DCA, Satellite/Conviction, Speculative/Thematic) or Trading (Equity Tactical, Futures/Macro)?
- If deploying, what instrument, book, risk ceiling, and execution venue?
- `NO_QUALIFIED_OPPORTUNITY -> HOLD_CASH` is a fully valid, prioritized system output.

---

## 4. Personal Portfolio Working Inventory (Screenshot-Derived / Non-Canonical)

*Notice: This inventory is derived from preliminary operator descriptions and UI screenshots. It does NOT constitute a reconciled cost basis or tax ledger.*

| Portfolio Segment | Observed Assets / Labels | Approximate Magnitude | Primary Custodian |
| :--- | :--- | :--- | :--- |
| **Long-Term / Growth** | `QQQM`, `VOO`, `PLTR`, `TSM`, `SOFI`, `NOW` | ~THB 69,465 | Dime! (KKP) |
| **Thematic / Space** | `SATL`, `RKLB`, `RDW`, `ITA`, `NASA`, `SIDU` | Discretionary / Speculative | Dime! (KKP) |
| **Existing Buckets Observed**| "long-term growth", "space/thematic", "Sniper", "Trump Buy", "NBIS" | Total ~THB 100,000 order of magnitude | Dime! (KKP) |
| **Dime FCD / Cash** | USD balance funded in Dime! FCD | ~USD 2,696.69 (~THB 90k at screenshot FX) | Dime! (KKP) |
| **THB Liquid Cash** | THB balance | ~THB 9,000 | Dime! (KKP) / Bank |

*Action Required:* Official broker account statements and transaction exports will be required to establish true FIFO/average-cost tax lots and baseline performance.

---

## 5. Proposed Multi-Book Capital Architecture

```text
PERSONAL CAPITAL
├── INVESTMENT BOOK
│   ├── CORE / DCA (Index ETFs, Global Equity/Bond anchor, low turnover)
│   ├── SATELLITE / CONVICTION (High-conviction quality individual equities)
│   └── SPECULATIVE / THEMATIC (High-narrative themes e.g. Space; bounded cap)
└── TRADING BOOK
    ├── EQUITY TACTICAL / SNIPER (Short-horizon equity setups, event-driven)
    └── FUTURES / MACRO (CME Micro contracts: MNQ, MES, MGC, MCL, M6E)
```

**Key Governance Firewall:**
- Investment and Trading maintain decoupled accounting, risk limits, and P&L attribution.
- Trading drawdowns must **never** draw capital automatically from the Investment Book.
- Inter-book transfers require explicit human authorization.
- The numerical Investment/Trading split is **NOT** assumed (no arbitrary 80/20 or 70/30 split is hardcoded); it remains `UNRESOLVED` pending explicit operator risk-policy inputs.

---

## 6. Broker Research Status & Provisional Roles

1. **Dime! (Kiatnakin Phatra Securities):**
   - **Role:** Existing Investment Book anchor (Long-term Core/DCA, Satellite, existing USD cash).
   - **Status:** Fee model and Dime Club Level 1 Free Trade Day rules analyzed; source conflicts identified in CAT fee and FCD vs USD campaign terminology.
2. **Webull Securities (Thailand):**
   - **Role:** Candidate Equity Tactical / Sniper book custodian & API integration target.
   - **Status:** Open API verified (Trading, Market Data, Account, WebSocket, no API fee currently). Credential security model requires read-only technical proof before any code integration.
3. **Futures Brokers (CME Micro Universe):**
   - **Role:** Dedicated Futures / Macro Trading Book custodian.
   - **Candidates:** NinjaTrader/Tradovate, Interactive Brokers (IBKR), Ironbeam, AMP Futures.
   - **Status:** Due diligence in progress. IBKR confirmed for Thai resident eligibility; NinjaTrader Thai KYC remains unverified by primary source.

---

## 7. Known Unresolved Source Conflicts & Scientific Holds

1. **`DIME_FCD_VS_DIME_USD`:** Campaign materials (e.g. Payday Sept 2026) exclude "Dime! USD" transactions, while the Dime Club page explicitly permits orders funded from "Dime! FCD". Primary source reconciliation required.
2. **`DIME_CAT_FEE`:** Official fee schedules and help center articles report conflicting CAT fee rates. Volatile fee schedule under research.
3. **`THAI_RESIDENT_NINJATRADER`:** Primary-source confirmation of Thai resident onboarding eligibility is absent on NinjaTrader; marked unconfirmed.
4. **`S2_GOVERNANCE_SEMANTICS`:** Stage S2 window definition (60 observed vs 60 contiguous calendar sessions) remains on formal **HOLD** pending human scientific adjudication.

---

## 8. Immediate Next Actions in R0 Research

1. Seed this initial `SESSION_HANDOFF.md` via commit and push to `origin/research/ppds-r0-capital-broker-architecture-20260928`.
2. Author primary research and architectural specification documents under `docs/ppds/`.
3. Complete due-diligence registers for Dime, Webull Open API, CME Micro Futures, and Thai 2026 Tax Ledger requirements.
4. Update this handoff with final synthesized findings and exact git verification ledgers.
