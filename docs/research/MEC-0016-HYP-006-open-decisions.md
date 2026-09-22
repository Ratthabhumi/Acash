# MEC-0016 / HYP_006: Pre-Inception Decisions Ledger

```text
[GOVERNANCE DECISION ARTIFACT: PRE-INCEPTION DECISIONS LEDGER]
[MECHANISM_ID: MEC-0016]
[CANDIDATE_HYPOTHESIS_ID: HYP_006]
[SUBJECT: PRE-INCEPTION ARCHITECTURAL, METHODOLOGICAL, AND PROVIDER DECISIONS]
[CURRENT_STATUS: PREINCEPTION_ACTIVE]
[EXACT_OPEN_BLOCKERS: 0]
[FEASIBILITY_VERDICT: FREE_DATA_FEASIBILITY_PASS]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/research/MEC-0016-HYP-006-open-decisions.md`
- **Governing Standard:** ACASH `AGENTS.md` (Single Canonical Authority, Strict Fail-Closed Contract, Statistical Dependence Awareness).

---

## 1. Decision Records Summary Table

| Decision ID | Topic | Status | Selected Option | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **MEC-0016-D01** | Replication Sample Window | `RESOLVED` | **Option A** (`2016-01-01` to `2024-04-30`) | Aligns with Alpaca inception date and preserves publication terminal date |
| **MEC-0016-D02** | Primary Market Data Provider | `RESOLVED` | **Option A** (`ALPACA_HISTORICAL_SIP`) | Zero-cost broker candidate with verified SIP bars & historical quotes |
| **MEC-0016-D03** | Secondary Bar Cross-Check | `RESOLVED` | **Option A** (`HF_DATA_LIBRARY`) | Independent 1m OHLCV bar comparison without quote splicing |
| **MEC-0016-D04** | Dividend Authority | `RESOLVED` | **Option A** (`STATE_STREET_SSGA_OFFICIAL`) | Sovereign sponsor distribution notices covering all 33 post-2016 events |
| **MEC-0016-D05** | Minimum Trade Count Gate | `RESOLVED` | **Option A** (Preserve $N \ge 100$) | Prevents opportunistic post-hoc relaxation for shorter sample |
| **MEC-0016-D06** | Alpaca 2016–2018 Quote Depth | `RESOLVED_PASS` | **Option A** (Verified on early dates) | Probed 2016-06-17, 2017-06-01, 2018-06-01 (9/9 HTTP 200) |
| **MEC-0016-D07** | Zero-Cost SIP Rate & Entitlement | `RESOLVED_PASS` | **Option A** (Documented & Verified) | Alpaca FAQ confirms old historical SIP requires no subscription; 200 req/min is throughput limit |
| **MEC-0016-D08** | Quote Conditions & Valid Policy | `RESOLVED_PASS` | **Option A** (Authoritative Mapping) | Bound to official Tape B metadata; `{'R', '?'}` acceptable with positive prices/sizes; reject non-firm/closed/crossed |
| **MEC-0016-D09** | Exact EOD Execution Semantics | `RESOLVED_PASS` | **Option A** (Continuous 15:59 NBBO) | Forced flat boundary 15:59:00 ET first valid NBBO in [15:59, 16:00); auction/MOC excluded; bar close prohibited |

---

## 2. Detailed Decision Records

### MEC-0016-D01: Replication Sample Window Selection
- **Status:** `RESOLVED`.
- **Verdict:** `2016-01-01` through `2024-04-30` (~8.3 years, 2,096 trading days).
- **Rationale:** Captures the complete history of free consolidated SIP equity bars from Alpaca while strictly honoring the publication-exposed terminal date (`2024-04-30`).

---

### MEC-0016-D02: Primary Market Data Provider Selection
- **Status:** `RESOLVED`.
- **Verdict:** Alpaca Markets Historical SIP.
- **Rationale:** Sole zero-cost provider candidate capable of providing 1-minute consolidated exchange bars and nanosecond NBBO quotes for execution fills.

---

### MEC-0016-D03: Secondary Bar Cross-Check Provider
- **Status:** `RESOLVED`.
- **Verdict:** HF Data Library (`hfdatalibrary.com` / Hugging Face).
- **Rationale:** High-frequency 1-minute OHLCV bar repository used strictly for independent bar sanity checking. Prohibited from trade execution or synthetic quote generation. Discrepancies classified hierarchically without arbitrary dollar tolerances.

---

### MEC-0016-D04: Corporate Action & Dividend Authority
- **Status:** `RESOLVED`.
- **Verdict:** State Street Global Advisors (SSGA) Official Historical Distributions.
- **Rationale:** Sovereign sponsor records governing SPY. All 33 post-2016 distributions cataloged.

---

### MEC-0016-D05: Minimum Completed Trade Count Gate
- **Status:** `RESOLVED`.
- **Verdict:** Preserve $N \ge 100$ completed trades unchanged.
- **Rationale:** Prevents post-hoc data-dependent relaxation. 100 trades across 8.3 years represents minimal statistical power to evaluate economic net profitability.

---

### MEC-0016-D06: Alpaca Historical SIP Quote Depth for 2016–2018
- **Status:** `RESOLVED_PASS`.
- **Empirical Evidence:** On 2026-09-22, a narrow non-strategy probe was executed across `2016-06-17`, `2017-06-01`, and `2018-06-01` at decision times `10:00, 12:00, 15:30 ET`.
- **Result:** All 9 boundaries returned HTTP 200 with valid, consolidated SIP quotes, positive bid/ask prices, positive sizes, and sub-millisecond to low-millisecond latencies. Documented in `docs/research/manifests/MEC-0016-alpaca-early-quote-contract-manifest.json`.

---

### MEC-0016-D07: Zero-Cost SIP Rate Limits & Entitlement Gating
- **Status:** `RESOLVED_PASS`.
- **Authority & Audit:** Official Alpaca documentation establishes that historical queries where `end <= current_time - 15 minutes` can query `feed=sip` without paid subscription. Standard account rate limits ($200$ requests/minute) represent an **operational throughput constraint** managed via asynchronous pagination pacing, not an entitlement barrier.

---

### MEC-0016-D08: Alpaca Quote Conditions & Valid-Quote Policy Binding
- **Status:** `RESOLVED_PASS`.
- **Authority:** Official Alpaca metadata endpoint (`GET /v2/stocks/meta/conditions/quote?tape=B`), archived in `docs/research/manifests/MEC-0016-alpaca-quote-conditions-tape-b.json`.
- **Resolution:**
  - Standard live/direct SIP quotes use condition code `'R'` ("Regular Market Maker Open").
  - Legacy historical archive quotes (< 2021) use condition code `'?'` ("Historical Vendor Unspecified Condition").
  - Acceptable executable conditions: `{'R', '?'}` provided all structural NBBO invariants hold: `bid_price > 0`, `ask_price > 0`, `bid_size > 0`, `ask_size > 0`, and `ask_price >= bid_price`.
  - Unacceptable conditions: `{'N', 'C', 'L', 'A', 'B', 'H', 'E', 'F', 'U', 'W', '4'}`.
  - Locked markets (`bid == ask`) allowed for execution if sizes > 0; crossed markets (`bid > ask`) strictly rejected.
  - Any unknown/unmapped condition code fails closed.

---

### MEC-0016-D09: Exact End-of-Day (EOD) Execution Semantics Binding
- **Status:** `RESOLVED_PASS`.
- **Authority:** Canonical `DEC-MEC015-11`, `MEC-0015-strategy-contract-audit.md` Section 8, and `MEC-0015-HYP-005-strategy-preregistration.md` Section 7.2.
- **Resolution:**
  - Final signal decision epoch: `15:30:00 ET` (evaluating completed bar `15:29:00`). If signal is FLAT, exit executes at `15:30:00 ET`.
  - Forced EOD flattening boundary: `15:59:00 ET`. Any position remaining open after 15:30:00 ET must be flattened at the first valid continuous SIP NBBO quote with timestamp $t_{\text{quote}} \in [\text{15:59:00.000}, \text{16:00:00.000})\text{ ET}$.
  - Execution fills: BUY at Ask + $0.001/share adverse slippage; SELL at Bid - $0.001/share adverse slippage.
  - Strictly zero overnight exposure. Closing auction / MOC crosses are excluded. Bar Close fills are strictly prohibited.
  - Fail-closed: If no valid quote exists before 16:00:00 ET, session is excluded under `DataContractError`.
