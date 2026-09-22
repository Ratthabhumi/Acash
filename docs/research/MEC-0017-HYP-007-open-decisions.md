# Open Decisions Log: MEC-0017 / HYP_007

## Decision Inventory & Resolution Ledger

### MEC-0017-D01: Target Asset Selection
- **Status:** `RESOLVED_PASS`
- **Decision:** Target asset is `SPY` (SPDR S&P 500 ETF Trust).
- **Lineage:** Inherited from MEC-0015 and MEC-0016.

### MEC-0017-D02: Primary Bar Provider Selection
- **Status:** `RESOLVED_PASS`
- **Decision:** Primary 1-minute bar provider is `ALPACA_HISTORICAL_SIP` (`feed=sip`, `adjustment=raw`).
- **Authority:** Direct Alpaca SIP historical API.

### MEC-0017-D03: Secondary Bar Role
- **Status:** `RESOLVED_PASS`
- **Decision:** Hugging Face Data Library serves as `SECONDARY_INDEPENDENT_BAR_CROSS_CHECK_ONLY`. Zero execution quote authority.

### MEC-0017-D04: Direct-SIP Transition Boundary & M1 Start Date
- **Status:** `RESOLVED_PASS`
- **Decision:** M1 start date is frozen at `2021-07-01`.
- **Rationale:** Empirical quote census (`MEC-0017-alpaca-direct-sip-transition-manifest.json`) established that legacy `?` quotes ceased on April 23, 2021, and direct SIP quotes (`R`) commenced on April 26, 2021. Selecting July 1, 2021 provides a conservative two-month operational separation buffer after the transition, ensuring zero provenance contamination.

### MEC-0017-D05: Terminal M1 Date & M2 Firewall
- **Status:** `RESOLVED_PASS`
- **Decision:** M1 terminal date is `2024-04-30`. M2 (`>= 2024-05-01`) is strictly firewalled (`LOCKED_ZERO_ACCESS`).

### MEC-0017-D06: Quote Condition Policy
- **Status:** `RESOLVED_PASS`
- **Decision:** Only official regular quotes (`R`) from Alpaca's Tape B catalog are executable. Legacy placeholder `?` is strictly prohibited fail-closed. Non-firm, slow, closing, and auction quotes are rejected.

### MEC-0017-D07: Execution Fill Model
- **Status:** `RESOLVED_PASS`
- **Decision:** `FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY` with embedded spread and standalone adverse slippage ($0.001/share). Bar-based fills (Open/Close) are strictly prohibited.

### MEC-0017-D08: Exact EOD Execution Semantics
- **Status:** `RESOLVED_PASS`
- **Decision:** Forced flatten at first valid continuous SIP NBBO in `[15:59:00, 16:00:00) ET`. Closing auction and MOC orders excluded.

### MEC-0017-D09: Search Space Cardinality
- **Status:** `RESOLVED_PASS`
- **Decision:** Exactly $K = 1$. Single baseline specification. No lookback search, no threshold search, no asymmetric tuning.

### MEC-0017-D10: Acceptance Gates Invariance
- **Status:** `RESOLVED_PASS`
- **Decision:** Acceptance criteria G1–G7 are preserved without relaxation (G4 $N \ge 100$, G2 Sharpe $\ge 1.00$, G7 2x stress Sharpe $\ge 0.75$).

---

## Blockers
- **Open Methodological Blockers:** `0`
- **Status:** All decisions resolved. Ready for Step R1 Registration.
