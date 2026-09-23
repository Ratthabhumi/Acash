# HYP_009 Pre-R2 Execution-Accounting Clarification (ADDITIVE, PRE-RESULT)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_PRE_R2_ACCOUNTING_CLARIFICATION_AND_R2_M1_EXECUTION]
[TYPE: ADDITIVE_PRE_R2_BOOKKEEPING_CLARIFICATION]
[SEALED_BEFORE_ANY_M1_RESULT_OBSERVATION]
[R1_SEAL_UNMODIFIED]
```

- **Document ID:** `docs/phase14/HYP_009_PRE_R2_EXECUTION_ACCOUNTING_CLARIFICATION.md`
- **Manifest:** `docs/phase14/manifests/HYP_009_PRE_R2_EXECUTION_ACCOUNTING_CLARIFICATION.json`
- **HYPOTHESIS:** `HYP_009` (`R1_PREREGISTERED_SEALED`) | **CORE:** `CORE-001`

R1 freezes the scientific strategy but underspecifies simulation bookkeeping.
This clarification binds bookkeeping BEFORE any market-data access and BEFORE
any M1 result. It does NOT modify the R1 manifest, the R1 registration record,
the preregistration document, or any gate/partition/provider contract.

---

## 1. Simulated Capital Normalization

- `SIMULATED_STARTING_AUM_USD = 100000.00` (simulation normalization only).
- `CAPITAL_AUTHORITY_USD = 0.00` (unchanged). Paper `NOT_AUTHORIZED`.
  Live `LOCKED`. `NO_REAL_ORDERS = true` (unchanged).
- `SIMULATED_AUM != CAPITAL_AUTHORITY` — explicitly distinguished.

## 2. Position Quantity / Cash Accounting

- Whole shares only. No fractional shares in canonical M1.
- `CASH -> LONG`: `shares = floor(available_cash / adverse_execution_fill_price)`.
  Residual cash stays in CASH earning `0.0`. No borrowing, no margin, no negative
  cash. If `shares <= 0`: FAIL CLOSED.
- `LONG -> CASH`: sell all shares. `LONG -> LONG` / `CASH -> CASH`: no transaction.
- No periodic rebalancing while state is unchanged.

## 3. Dividend Economic Accounting (No Double-Counting)

- Signal series keeps frozen `G_t = (P_t + D_t) / P_{t-1}` ex-date economics.
- Portfolio: owning SPY across an official ex-date creates a `DIVIDEND_RECEIVABLE`
  (`shares_entitled × authoritative cash distribution per share`), recognized on
  ex-date, counted in equity from ex-date. Receivable becomes spendable simulation
  cash on the official payable date; before payable date it MUST NOT size a new
  purchase. Payable date unavailable from qualified authority and no separately
  qualified official payable-date authority exists → `BLOCKED_DIVIDEND_PAYMENT_DATE_CONTRACT`.
- No dividend counted twice.

## 4. Split Accounting

- Signal prices `adjustment=split`; execution/valuation `adjustment=raw`.
- Raw holdings adjusted only via a qualified split event. Split implied by
  raw-vs-split data without qualified authoritative event →
  `BLOCKED_UNBOUND_SPLIT_AUTHORITY`. If none in the authorized window, record
  `NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW` (no generalization outside the window).

## 5. Daily Portfolio Valuation

- EOD equity = cash + shares × RAW official daily close + outstanding dividend
  receivables. No after-hours, no adjusted close for valuation.
- Daily net return `EQUITY_t / EQUITY_{t-1} - 1`. First M1 reference equity `100000.00`.
- Sharpe on daily net returns (252 / ddof=1 / rf=0); zero variance → FAIL CLOSED.
- Max drawdown from daily EOD net equity curve. Total return `ENDING/100000 - 1`.

## 6. M1 Terminal Valuation (2020-12-31 Boundary)

- M1 ends `2020-12-31`. Do NOT fetch 2021-01-01 or later prices to close/value M1.
- LONG at M1 end: value at authorized 2020-12-31 RAW close. No forced
  liquidation, no fictitious terminal exit friction.
- A month-end signal using 2020-12-31 may be recorded as
  `PENDING_NEXT_PARTITION_EXECUTION_NOT_EXECUTED` if execution falls outside M1.
  It MUST NOT trigger any 2021 data request.

## 7. Benchmark Accounting (SPY Buy & Hold, for G4)

- Starting equity `100000.00`; begins on FIRST eligible M1 session open; 100%
  whole-share deploy with baseline 2 bps adverse buy slippage;
  `shares = floor(100000 / benchmark_entry_fill)`; residual cash earns `0.0`.
- Hold continuously through M1. Same raw valuation, dividend entitlement, split
  handling, residual-cash treatment. No rebalancing, no forced M1-end liquidation.
- Benchmark drawdown from its daily EOD equity curve over the identical M1
  interval. G4: `CORE_MDD < BENCHMARK_MDD` strict; equality FAILS G4.
- Benchmark uses no strategy signal and is never retroactively optimized.

## 8. Upstream Pins (Verified at Seal)

- R1 manifest SHA: `ded1528d78f92003ab538a1ade7b9e047ed7306feaac4faa3270c67df27fce7c`
- Preregistration SHA: `6813f3a5870c9027801f510f61a7a17cae01ebc7706b5b94fcb3334236202177`
- HYP_009 record SHA: `fb855542e86aa91139a0c7cdbedaad60de113ccbf679fe3e12a7465bcae13f2d`

## 9. Authority Boundary

Accounting clarification only. Zero market-data access. Zero signals/P&L.
M2/M3/quarantine/prospective untouched and locked. Next: R2 M1 data
qualification under separate stage gating (currently BLOCKED — see
`docs/phase14/HYP_009_DATA_ENTITLEMENT_BLOCK_001.md` when present).
