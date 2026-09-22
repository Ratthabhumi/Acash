# MEC-0016 / HYP_006: Data Requirements Specification

```text
[RESEARCH GOVERNANCE ARTIFACT: DATA REQUIREMENTS SPECIFICATION]
[MECHANISM_ID: MEC-0016]
[CANDIDATE_HYPOTHESIS_ID: HYP_006]
[SUBJECT: MARKET DATA, QUOTE, AND CORPORATE ACTION CONTRACTS FOR POST-2016 REPLICATION]
[PRIMARY_BAR_PROVIDER: ALPACA_HISTORICAL_SIP]
[PRIMARY_QUOTE_PROVIDER: ALPACA_HISTORICAL_SIP]
[SECONDARY_BAR_CROSS_CHECK: HF_DATA_LIBRARY]
[PRIMARY_DIVIDEND_AUTHORITY: STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS]
[TARGET_SYMBOL: SPY]
[PROPOSED_M1: 2016-01-01 THROUGH 2024-04-30]
[STATUS: PREINCEPTION_SPECIFICATION]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/research/MEC-0016-HYP-006-data-requirements.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Literature Alignment, Unit & Space Discipline).

---

## 1. Instrument & Universe Specification
- **Primary Asset:** SPDR S&P 500 ETF Trust (`SPY`).
- **Asset Class:** US Equity ETF.
- **CUSIP:** `78462F103`.
- **Trading Venues:** All US consolidated exchanges (Tape B, SIP consolidated tape).
- **Trading Hours:** Regular Trading Hours (RTH) only: `09:30:00 ET` through `16:00:00 ET` ($390$ minutes per standard non-early-close session).

---

## 2. 1-Minute Bar Data Contract (Alpaca Primary)

### 2.1 Schema & Invariants
Each minute bar must contain:
- `timestamp`: Nanosecond or microsecond timestamp converted to `America/New_York`.
- `open`: Strictly positive floating/decimal price ($> 0$).
- `high`: $\ge \max(\text{open}, \text{close})$ ($> 0$).
- `low`: $\le \min(\text{open}, \text{close})$ ($> 0$).
- `close`: Strictly positive floating/decimal price ($> 0$).
- `volume`: Nonnegative integer ($\ge 0$).
- `adjustment`: `raw` (unadjusted prices preserve exact execution triggers).

### 2.2 Timestamp Mapping Convention
- **Provider Labeling:** Left-edge of the 1-minute interval:
  $$\text{bar\_timestamp} = \text{start of interval } [T, T + 1\text{min})$$
- **Decision Mapping:**
  - Author conceptual decision at `10:00:00 ET` consumes the completed minute bar covering `[09:59:00, 10:00:00)`.
  - In Alpaca SIP, this bar is labeled `09:59:00 ET`.
  - Representative mappings: `10:00 -> 09:59`, `10:30 -> 10:29`, `12:00 -> 11:59`, `15:30 -> 15:29`.

### 2.3 Strict Missing-Bar Policy (Inherited from HYP_005)
- **Policy:** `FAIL_CLOSED_SESSION_EXCLUSION`.
- If any required minute is missing in a standard 390-minute eligible session:
  - Exclude the entire trading session from strategy execution.
  - Zero forward-filling, zero linear interpolation, zero synthetic bar generation.
  - No relaxation permitting $\le 5$ missing bars.

---

## 3. Historical Quote Data Contract (Alpaca Primary)

### 3.1 Execution Boundary Fill Contract
$$\text{Execution Rule: } \text{FIRST\_VALID\_SIP\_NBBO\_AT\_OR\_AFTER\_EXECUTION\_BOUNDARY}$$
- Decision evaluation boundary: $T \in \{10:00:00, 10:30:00, \dots, 15:30:00 \text{ ET}\}$.
- Look for quote records where:
  $$\text{sip\_timestamp} \ge T$$
- Select the first record satisfying the authoritative quote validity contract.
- **BUY Fill Price:** $\text{Ask} + \$0.001/\text{share}$ (standalone adverse slippage).
- **SELL Fill Price:** $\text{Bid} - \$0.001/\text{share}$ (standalone adverse slippage).
- **Quote Timeout Policy:** No arbitrary timeout is invented. If no valid quote is available within the authoritative query retrieval window, the fill fails closed.

### 3.2 Quote Validity & Condition Filters
A quote is valid if and only if:
1. `bid_price > 0` and `ask_price > 0`.
2. `bid_size > 0` and `ask_size > 0`.
3. `ask_price >= bid_price` (crossed market quotes with `bid > ask` are strictly rejected).
4. `is_locked` ($\text{bid} == \text{ask}$) is admitted only if marked valid by consolidated SIP conditions.
5. Condition Code Mapping: Bound to existing canonical MEC-0015 quote qualification evidence. Generic condition filters lacking explicit canonical code mapping are classified:
   $$\text{REQUIRES\_AUTHORITATIVE\_CONDITION\_CODE\_BINDING}$$

---

## 4. Corporate Action & Dividend Contract (SSGA Sovereign)

- **Authority:** State Street Global Advisors (SSGA) Official Historical Distributions.
- **Coverage:** All **33 quarterly distributions** in the `2016-01-01` through `2024-04-30` sample.
- **Required Fields:** `ex_date`, `record_date`, `payable_date`, `cash_distribution`.
- **Strategy Usage:** On dividend ex-dates, adjust previous regular session close:
  $$\text{prev\_close\_adjusted} = \text{close}_{d-1} - \text{cash\_distribution}_d$$

---

## 5. Secondary Bar Cross-Check Contract (HF Data Library)

- **Role:** Independent cross-validation of 1-minute OHLCV bars.
- **Discrepancy Classification Hierarchy:**
  - `EXACT_MATCH`: Bars match identically within floating representation.
  - `EXPECTED_ADJUSTMENT_DIFFERENCE`: Discrepancy explained by verified dividend/split adjustments.
  - `PROVIDER_SEMANTIC_DIFFERENCE`: Documented exchange feed or volume aggregation difference.
  - `UNEXPLAINED_DISCREPANCY`: Material discrepancy requiring investigation.
- **Strict Boundary:** No arbitrary dollar tolerance is assumed. HF Data Library is **never** used for quote execution, trade simulation, or signal generation.

---

## 6. Fail-Closed Boundaries & Firewall
1. **Missing Minute Bars:** Any missing bar in standard session $\implies$ session exclusion.
2. **Missing Quotes:** Inability to retrieve valid NBBO at/after boundary $\implies$ fail closed.
3. **M2 Firewall:** Any request for market data on or after `2024-05-01` raises `OutdatedSampleViolation` and immediately halts execution.
