# MEC-0013-PRICE-ONLY-DRAFT — Price-Only Opening Range Breakout Pre-Registration Scaffold

```text
[HUMAN-ACCEPTED FOR PRE-REGISTRATION COMPLETION]
[NON-NORMATIVE]
[NO EMPIRICAL AUTHORITY]
[NO BACKTEST AUTHORITY]
[NOT HYP_003]
[MEC-0013 REMAINS ARCHIVED]
```

**Document ID:** `docs/phase14/mec_0013_price_only_draft_scaffold.md`  
**Object:** Research-design scaffold for a decoupled, price-only opening range breakout formulation on SPY.  
**Purpose:** Pre-register the mathematical geometry, bounded ex-ante parameter grid, and data authority links without requiring VWAP (D14) or authorizing empirical backtesting.  
**Ratification Status:** Human-accepted on 2026-09-18 (Decision C3 Option A) for pre-registration completion only.  
**Date:** 2026-09-18  
**Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)  
**Authority:** Strict Fail-Closed (`AGENTS.md`). Zero empirical claims, zero return calculations, zero backtests.

---

## 1. Governance & Boundary Status

- **Working Object Name:** `MEC-0013-PRICE-ONLY-DRAFT`
- **Scaffold Standing:** `HUMAN-ACCEPTED FOR PRE-REGISTRATION COMPLETION` (Decision C3 Option A, 2026-09-18).
- **MEC-0013 Standing:** Remains `ARCHIVED` / `NOT PROMOTED` per ratified Human Decisions `MEC-0013-D01` and `MEC-0013-D02`.
- **Hypothesis Standing:** `HYP_003` is **NOT CREATED** (absent repository-wide).
- **Inception Gate R1:** **NOT STARTED** / `ResearchReInceptionGate` not invoked.
- **Empirical Backtesting Engine:** **STRICTLY LOCKED**.
- **Trading Authority:** Paper `NOT AUTHORIZED`, Live `LOCKED`, Capital `$0.00`, `NO_REAL_ORDERS=true`.
- **D13 Canonical Status:** `PARTIALLY RESOLVED (AVAILABILITY/DEPTH: RETIRED; PIT/VINTAGE: OPEN)`.
- **D14 Canonical Status:** `BLOCKED (AUTHORITY-CONDITIONAL / OPEN)`.
- **Data Boundary:** Zero live network calls or probes are authorized or executed by this scaffold.

---

## 2. B1 — Fixed Research Scope

The research design is strictly bounded to the following parameters:

| Dimension | Frozen Value | Governance & Authority Basis |
|---|---|---|
| **Instrument** | `SPY` (SPDR S&P 500 ETF Trust) | Single-instrument US cash equity proxy. Dynamic multi-stock universes and cross-sectional constituent rankings are excluded to prevent survivorship bias. |
| **Market Data Feed** | Consolidated SIP 1-Minute Aggregates | Unadjusted raw trade-day aggregates (`feed=sip`, `timeframe=1Min`, `adjustment=raw`). |
| **Session Authority** | CA-1 NYSE Sovereign Trading Calendar | Core Regular Trading Hours `[09:30:00, 16:00:00) America/New_York` (390 bars) and Early Close `[09:30:00, 13:00:00)` (210 bars). Pre-market (04:00–09:30 ET) and after-hours (16:00–20:00 ET) are explicitly excluded from breakout detection. |
| **Universe Scope** | Single instrument only (`SPY`) | Zero constituent selection, zero sector rotation. |
| **Price Basis** | Unadjusted Intraday Trade-Day Price Levels | Intraday price triggers and range boundaries are computed on raw trade-day tape levels ($P_{\text{raw}}$). Cash distributions and corporate actions are handled downstream in forward return accounting. |
| **Signal Family** | `PRICE-ONLY OPENING RANGE BREAKOUT` | Primary breakout signals depend strictly on price extremes observed during the frozen opening-range interval. |

### Explicit Exclusions from Primary Signal Lane:
The following components are strictly excluded from the primary price-only signal definition:
- **Volume-Weighted Average Price (VWAP):** Decoupled from primary signal lane. D14 point-in-time consolidated volume is NOT a dependency for price-only testing.
- **Volume Filters / Thresholds:** Zero volume surge or relative volume gates in the primary signal.
- **Macro / Volatility Regime Classifiers:** Excluded from initial pre-registration grid.
- **Multi-Stock / Basket Ranking:** Excluded.
- **Fundamental Data & Corporate Filings:** Excluded.
- **News / Sentiment Feeds:** Excluded.
- **Machine Learning Models:** Zero algorithmic model weights or feature selection.
- **Post-Hoc Optimization Indicators:** Moving average filters, RSI, Bollinger Bands, and ATR filters are excluded from the primary hypothesis census.

---

## 3. B2 — Opening-Range Research Cells (Bounded Ex-Ante Grid)

To prevent parameter fishing and comply with ACASH anti-HARKing governance ($K \le 6$), the primary research grid is bounded strictly to **4 deterministic geometry cells**:

$$\text{Grid} = \{\Delta T_{\text{OR}} \in \{5\text{m}, 15\text{m}\}\} \times \{\text{Direction} \in \{\text{LONG}, \text{SHORT}\}\} \implies K_{\text{primary}} = 4$$

### 3.1 Declared Primary Hypothesis Census ($K = 4$)

| Cell ID | Opening Range Window ($\Delta T_{\text{OR}}$) | Breakout Direction | Local Time Window (ET) | Bar Count in OR | Primary Evaluation Horizon |
|---|---|---|---|---|---|
| `ORB_5M_LONG` | 5 minutes | LONG | `09:30:00` to `09:35:00` | 5 bars (`09:30`–`09:34`) | Ex-ante frozen post-window |
| `ORB_5M_SHORT` | 5 minutes | SHORT | `09:30:00` to `09:35:00` | 5 bars (`09:30`–`09:34`) | Ex-ante frozen post-window |
| `ORB_15M_LONG` | 15 minutes | LONG | `09:30:00` to `09:45:00` | 15 bars (`09:30`–`09:44`) | Ex-ante frozen post-window |
| `ORB_15M_SHORT` | 15 minutes | SHORT | `09:30:00` to `09:45:00` | 15 bars (`09:30`–`09:44`) | Ex-ante frozen post-window |

### 3.2 Opening-Range Mathematical Geometry

For session date $d$ under CA-1 authority and opening range interval $T_{\text{OR}}(d) = [t_{\text{open}}, t_{\text{open}} + \Delta T_{\text{OR}})$:

$$\text{OR}_{\text{high}}(d) = \max_{t \in T_{\text{OR}}(d)} \text{High}_t$$

$$\text{OR}_{\text{low}}(d) = \min_{t \in T_{\text{OR}}(d)} \text{Low}_t$$

$$\text{OR}_{\text{width}}(d) = \text{OR}_{\text{high}}(d) - \text{OR}_{\text{low}}(d)$$

### 3.3 Breakout Observation Definition
Breakout observation commences strictly at $t \ge t_{\text{open}} + \Delta T_{\text{OR}}$ (e.g. at or after `09:35:00 ET` for the 5m window, and at or after `09:45:00 ET` for the 15m window).
- **First-Break-Only Principle:** Only the earliest breakout event per session date is eligible for primary trial evaluation. Subsequent or recurrent breaches on the same session are excluded to eliminate serial auto-correlation.
- **Zero Historical Computation:** These geometry rules are mathematical specifications only. Zero empirical calculations or returns have been computed.

---

## 4. B3 — Parameters That Must Remain Human-Open

The following parameters are NOT chosen by this implementation scaffold. They represent explicit research-design decisions that must be ratified by the Human Operator prior to pre-registration freeze:

| Parameter Field | Description / Scope | Open Alternatives (Human Choice Required) |
|---|---|---|
| **1. Breakout Confirmation** | Rule determining when a breakout is deemed triggered. | **A:** High/Low touch (`High_t > OR_high` or `Low_t < OR_low`)<br>**B:** Close-through (`Close_t > OR_high` or `Close_t < OR_low`)<br>**C:** Buffer touch (`Close_t > OR_high + \delta`) |
| **2. Entry Timing & Latency** | Bar on which execution is simulated. | **A:** Immediate at breakout minute bar close ($T$ close)<br>**B:** Next-bar open ($T+1$ open)<br>**C:** Limit order at boundary level |
| **3. Directional Lane** | Final research hypothesis structure. | **A:** Symmetric two-sided ($K=4$, testing both Long and Short)<br>**B:** Long-only primary ($K=2$, testing Long 5m/15m only) |
| **4. Stop-Loss Rule** | Protective risk-exit boundary. | **A:** Opposite boundary ($\text{OR}_{\text{low}}$ for Long, $\text{OR}_{\text{high}}$ for Short)<br>**B:** Midpoint ($\frac{\text{OR}_{\text{high}} + \text{OR}_{\text{low}}}{2}$)<br>**C:** Multiplier of OR width ($1.0 \times \text{OR}_{\text{width}}$)<br>**D:** None (pure time-horizon exit) |
| **5. Exit / Holding Horizon** | Holding horizon for trade resolution. | **A:** Fixed time horizon (e.g. 30m, 60m, 120m)<br>**B:** End-of-day close (15:59 ET)<br>**C:** Target multiple of range width ($1.0 \times \text{OR}_{\text{width}}$) |
| **6. End-of-Day Flattening** | Mandatory overnight inventory liquidation rule. | **A:** MOC (Market-on-Close at 15:59 ET continuous bar)<br>**B:** Auction cross (16:00 ET official NYSE closing auction print) |
| **7. Transaction-Cost Model** | Execution friction deduction. | **A:** Zero cost (gross benchmark only)<br>**B:** Fixed institutional friction: 1.0 bps roundtrip<br>**C:** Fixed institutional friction: 1.6 bps roundtrip<br>**D:** Dynamic spread model |
| **8. Slippage Model** | Execution adverse impact assumption. | **A:** 0.0 bps (passive/midpoint assumption)<br>**B:** 0.5 bps per side adverse fill on breakout market orders |
| **9. Execution Price Convention** | Price reference used for simulated fill. | **A:** Stated bar Close<br>**B:** Next-bar Open<br>**C:** Conservative worst-price (High for buy, Low for sell) |
| **10. Auction Print Handling** | Treatment of the `09:30:00 ET` opening auction print. | **A:** Include `09:30` open as official consolidated auction price<br>**B:** Require first continuous match timestamp |
| **11. IS / OOS Partition Dates** | Chronological partition boundaries. | **IS Window:** Human-specified range (e.g. 2017-01-01 to 2023-12-31)<br>**OOS Window:** Held-out period (e.g. 2024-01-01 to 2026-09-10)<br>**Blind Period:** Protected from exploratory review |
| **12. Embargo / Purge Rules** | Data separation around partition seams. | **A:** Zero embargo (intraday trades do not span sessions)<br>**B:** 1-day embargo between IS and OOS boundaries |
| **13. Data-Quality Threshold** | Minimum data health required to admit a session. | **A:** 100% complete (390/390 bars required; missing bar => session dropped)<br>**B:** Maximum 1 missing bar allowed outside opening range |
| **14. Session Exclusion Policy** | Handling of early closes and market halts. | **A:** Exclude all CA-1 early close days (13:00 ET) from primary sample<br>**B:** Include early close days with adjusted 210-minute horizon |

---

## 5. B4 — Anti-HARKing Protocol & Invariants

Prior to any empirical data exposure or return simulation, the following safeguards are frozen:

1. **Census Constraint ($K \le 6$):** The primary hypothesis census is strictly fixed at $K = 4$ cells (5m/15m $\times$ Long/Short). No candidate cells may be added after reviewing empirical outcomes.
2. **Zero Selective Deletion:** No cell in the $K=4$ grid may be discarded, hidden, or reclassified because of weak, negative, or unprofitable performance. All 4 cells must be reported in the census ledger.
3. **Formal Amendment Policy:** Any modification to parameter definitions, confirmation rules, or cost models after inspecting In-Sample data constitutes a new candidate revision and invalidates prior OOS holdouts.
4. **Decoupling from D14 (VWAP):** The primary research lane remains 100% price-only. Reassessment or resolution of D14 (provider VWAP authority) is NOT a prerequisite for evaluating this price-only scaffold.
5. **No Sovereign Hypothesis Promotion:** This scaffold does **NOT** register `HYP_003` and does **NOT** authorize `ResearchReInceptionGate` (R1).

---

## 6. B5 — Data Authority References

This scaffold links directly to the following canonical ACASH evidence and data authorities:

1. **Historical SIP Qualification Implementation:** `src/acash/data/qualification/` (`AlpacaHistoricalSipClient`, `HistoricalBarValidator`, `HistoricalSipQualificationEngine`).
2. **Verified Multi-Year SIP Evidence Packages:** Four verified single-session packages spanning 9 years (1,560 continuous 1-minute regular-session bars, 0 errors, sealed digests):
   - `2017-09-15` (`SIP-QUAL-SPY-ac03e51c`)
   - `2020-09-15` (`SIP-QUAL-SPY-c924ae70`)
   - `2023-09-15` (`SIP-QUAL-SPY-19647058`)
   - `2026-09-15` (`SIP-QUAL-SPY-280f1628`)
   *(Note: Raw JSON files in `var/data/qualification` are machine-local and git-ignored per repo safety rules; canonical audit trail resides in committed memos).*
3. **CA-1 Calendar Authority:** `src/acash/data/calendar/nyse_ca1.py` (`NyseCa1Calendar`) providing official NYSE trading session schedules, exact 390/210 minute grids, and pinned artifact provenance for 2013–2026.
4. **MEC-0013 D13/D14 Reassessment Memo:** `docs/phase14/mec_0013_d13_d14_reassessment_evidence.md`.
