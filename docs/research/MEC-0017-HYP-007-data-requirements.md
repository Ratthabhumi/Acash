# Market Data Requirements Specification: MEC-0017 / HYP_007

## 1. Instrument & Universe
- **Target Symbol:** `SPY` (SPDR S&P 500 ETF Trust)
- **Asset Class:** US Equity ETF (Tape B)
- **Primary Trading Session:** NYSE Regular Trading Hours (`09:30:00` to `16:00:00` ET, exactly 390 one-minute bars).
- **Early Close Sessions:** Excluded from evaluation to preserve 390-bar session invariant.

---

## 2. Sample Partitions
- **M1 Replication Sample:**
  - Start Date: `2021-07-01`
  - End Date: `2024-04-30`
  - Provenance: Selected strictly via conservative data-quality boundary after direct-SIP transition (April 2021).
  - Role: `PUBLICATION_EXPOSED_DIRECT_SIP_REPLICATION_SAMPLE`
- **M2 Stress Sample:**
  - Start Date: `2024-05-01` onward
  - Role: `PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE`
  - Access State: `LOCKED_ZERO_ACCESS` (strictly prohibited in this task).

---

## 3. Provider Architecture & Roles
1. **Primary 1-Minute Bar Provider:** `ALPACA_HISTORICAL_SIP`
   - Endpoint: `GET /v2/stocks/SPY/bars?timeframe=1Min&feed=sip&adjustment=raw`
   - Format: UTC ISO timestamp, open, high, low, close, volume, trade_count, vwap.
2. **Secondary Bar Cross-Check Provider:** `HF_DATA_LIBRARY`
   - Role: `SECONDARY_INDEPENDENT_BAR_CROSS_CHECK_ONLY`
   - Strict boundary: Used solely to cross-check bar timestamps and volume aggregates; has ZERO quote, NBBO, or execution authority.
3. **Primary Execution Quote Provider:** `ALPACA_HISTORICAL_SIP`
   - Endpoint: `GET /v2/stocks/quotes?symbols=SPY&feed=sip&sort=asc`
   - Granular Quote Conditions: Enforces official Tape B catalog (`GET /v2/stocks/meta/conditions/quote?tape=B`).
   - Condition Policy:
     - Permitted: `{"R"}` (Regular, Two-Sided Open Quote).
     - Prohibited fail-closed: `{"?"}` (Legacy unresolved placeholder).
     - Prohibited special states: `{"N", "C", "L", "A", "B", "H", "E", "F", "U", "W", "4"}`.
     - Unmapped / unknown: Fail-closed immediately (`DataContractError`).
4. **Primary Dividend Authority:** `STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS`
   - Reconciled against official State Street SPDR historical distribution schedule.

---

## 4. Execution Fill Model
- Execution Model: `FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY`
- BUY Fill: `NBBO_Ask + $0.001/share adverse slippage`
- SELL Fill: `NBBO_Bid - $0.001/share adverse slippage`
- Spread Model: `EMBEDDED_IN_NBBO_FILL` (explicit half-spread deduction with NBBO is prohibited).
- Bar-based execution (Open of next minute, Close of current bar): `STRICTLY_PROHIBITED`.
- EOD Forced Flatten: First valid continuous SIP NBBO in `[15:59:00, 16:00:00) ET`. Closing auction (`4`, `C`) excluded.
