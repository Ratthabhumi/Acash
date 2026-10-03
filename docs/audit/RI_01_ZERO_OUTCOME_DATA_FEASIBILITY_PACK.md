# RI-01 Zero-Outcome Data Feasibility Pack (PREPARED — NOT EXECUTED)

**Authorization boundary**: preparing questions only. Execution requires a
separate explicit human authorization scoped to zero-outcome feasibility.
No returns, no PnL, no Sharpe, no signal hit-rate, no parameter tuning —
those are OUT OF SCOPE for feasibility and must never be computed here.

## Feasibility questions (RI-01 opening-state momentum)

1. SIP daily bar availability: which sessions/symbols have complete
   `1Day` SIP bars for the HYP_011 universe (ACWI/AGG/SPY) over the
   feasibility window?
2. SIP minute bar availability: which sessions have complete intraday
   minute bars (session-open semantics: first bar timestamp vs official
   open_utc)?
3. Timestamp precision: what precision do bar timestamps carry (second?
   millisecond? timezone handling?), and is it sufficient to attribute an
   opening print without look-ahead?
4. Corporate-action adjustment semantics: are vendor `split`-adjusted
   closes authoritative for back-adjusted open attribution, or must raw
   closes + CA ledger be composed manually?
5. Symbol lifecycle: any ticker/CUSIP changes, halts, or late listings in
   the window that would corrupt a naive continuous series?
6. Data entitlement: which endpoints/feeds does the current credential
   tier cover (SIP delayed? full OPRA? historical depth to 2016?)?
7. Cost: what is the marginal cost (quota, dollars, latency) of the
   feasibility queries themselves?

## Method constraints

- Read-only queries against already-entitled endpoints only.
- Record coverage tables (session × symbol × availability), never
  performance statistics.
- Any gap → `DATA_UNAVAILABLE`, never interpolated.
- Output: a feasibility ledger (JSON), not a signal.
