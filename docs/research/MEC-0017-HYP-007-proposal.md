# Research Re-Inception Proposal: MEC-0017 / HYP_007

## 1. Metadata & Authority Lineage
- **Candidate Hypothesis ID:** `HYP_007`
- **Candidate Hypothesis Version:** `v1.0`
- **Mechanism Lineage:** `MEC-0017` (SPY Noise-Area Intraday Momentum Direct-SIP Replication)
- **Ancestor Hypotheses:**
  - `HYP_005` (Mechanism `MEC-0015`): Formally blocked non-falsified on primary commercial data entitlement ($199/mo).
  - `HYP_006` (Mechanism `MEC-0016`): Formally blocked non-falsified on early-M1 historical quote condition provenance (`c: ["?"]`).
- **Research Class:** `STRATEGY_NATIVE_EXECUTABLE_ECONOMIC_HYPOTHESIS`
- **Primary Objective:** `NET_ECONOMIC_PERFORMANCE_AFTER_REALISTIC_FRICTION`
- **Human Authorization Token:** `AUTHORIZE_HYP_007_DIRECT_SIP_FREE_DATA_FEASIBILITY_AND_CONDITIONAL_R1`

---

## 2. Scientific Motivation & Problem Statement
HYP_006 demonstrated that historical Alpaca SIP quotes prior to late April 2021 carry undifferentiated `?` condition codes originating from third-party vendor archives, preventing rigorous execution verification under SEC Rule 602.
However, empirical audit (`MEC-0017-HYP-007-direct-sip-feasibility-audit.md`) proves that starting April 26, 2021, Alpaca's direct SIP capture went live, delivering consolidated top-of-book quotes with granular CTA condition codes (`R`).

**Research Question:**
Does the frozen Noise-Area SPY intraday momentum strategy remain economically viable on a publication-exposed post-transition sample where Alpaca historical quotes originate from direct SIP capture and retain authoritative quote-condition semantics?

---

## 3. Scope & Sample Partitions
- **Target Instrument:** `SPY` (SPDR S&P 500 ETF Trust)
- **Primary Timeframe:** `1m` (NYSE Regular Trading Hours: 09:30 to 16:00 ET, 390 bars)
- **M1 Replication Window:** `2021-07-01` through `2024-04-30`
  - Start Date Rationale: Earliest conservative quarter boundary after direct-SIP transition (April 2021), providing a clean 2-month post-transition separation buffer.
  - Role: `PUBLICATION_EXPOSED_DIRECT_SIP_REPLICATION_SAMPLE` (not pristine OOS, not prospective).
- **M2 Stress Window:** `2024-05-01` onward
  - Status: `LOCKED_ZERO_ACCESS` (strictly firewalled).
- **Search Space Cardinality:** Exactly $K = 1$. Single preregistered specification. Zero parameter tuning.

---

## 4. Market Data Contract
- **Primary Bar Provider:** `ALPACA_HISTORICAL_SIP` (`/v2/stocks/SPY/bars`, `feed=sip`, `adjustment=raw`).
- **Primary Execution Quote Provider:** `ALPACA_HISTORICAL_SIP` (`/v2/stocks/quotes`, `feed=sip`, `sort=asc`).
- **Secondary Bar Cross-Check:** `HF_DATA_LIBRARY` (independent bar integrity cross-check only; zero quote authority).
- **Dividend Authority:** `STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS`.
- **Missing Bar Policy:** `FAIL_CLOSED_SESSION_EXCLUSION` (any missing minute bar excludes entire session).
- **Quote Executability:** Only condition code `R` is executable. Code `?` is strictly prohibited fail-closed.

---

## 5. Non-Negotiable Acceptance Criteria (G1–G7)
The acceptance gates are strictly inherited without relaxation:
- **G1 (Net Total Return):** $R_{\text{net}} > 0.0$
- **G2 (Net Annualized Sharpe):** $\text{Sharpe}_{\text{net}} \ge 1.00$
- **G3 (Max Drawdown):** $\text{MDD} \le 30.0\%$
- **G4 (Completed Trades):** $N_{\text{trades}} \ge 100$
- **G5 (Contract Integrity):** Zero contract, data, or execution violations.
- **G6 (2x Friction Net Return):** $R_{\text{2x\_stress}} > 0.0$
- **G7 (2x Friction Net Sharpe):** $\text{Sharpe}_{\text{2x\_stress}} \ge 0.75$

---

## 6. Execution & Capital Boundaries
- Capital Authority: **`$0.00`**
- `NO_REAL_ORDERS = true`
- Paper Trading: **`LOCKED`**
- Live Trading: **`LOCKED`**
- Market Data Access during R1: **`ZERO`**
