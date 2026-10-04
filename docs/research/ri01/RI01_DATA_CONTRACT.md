# RI-01 Data Contract — Minimum Observable Inputs (ZERO-OUTCOME FEASIBILITY)

**Status**: `FEASIBILITY_ONLY` — defines what would be needed, not what is approved.
**Hypothesis**: RI-01 opening-state momentum (R0 intake `SUPPORTED_MECHANISM`, Shortlist A).
**Instrument / frequency / provider**: `NOT_YET_DETERMINED` — nothing here preregisters them.
**Outcome metrics**: NOT AUTHORIZED — no return, PnL, Sharpe, hit-rate, or tuning in this pack.

Reference candidate (ILLUSTRATIVE ONLY, following the Gao et al. 2018 replication
lineage in `docs/research/MEC-0014-market-intraday-momentum-research-intake.md`):
US equity index exposure via a single liquid ETF (e.g. SPY), NYSE calendar CA-1.
This is a scoping illustration, NOT a preregistration.

---

## 1. DATA REQUIRED (all must be PASS or the segment cannot start)

| # | Input | Exact meaning | Why required |
|---|-------|---------------|--------------|
| R1 | Instrument universe | Frozen symbol list + MIC/exchange per symbol | Without it, coverage tables are undefined |
| R2 | Exchange calendar | CA-1 (`NyseCa1Calendar`): trading sessions, opens, closes, holidays, half-days | Session mapping, DST-correct UTC bounds |
| R3 | Session open semantics | Official RTH open instant per session (09:30 ET regular; half-day variants) | Anchors every opening-state timestamp |
| R4 | Previous close semantics | Single authoritative prior-session close (official close/auction cross vs bar close — exactly one, contract-tested) | The $r_1$ predictor starts at prior close; ambiguity here corrupts the predictor definition |
| R5 | Opening print / first-trade semantics | Which print counts as the opening observation (auction cross vs first continuous trade) and its timestamp meaning | Opening-state attribution without look-ahead |
| R6 | Minute bars, RTH-complete | 1-minute OHLCV, all 390 regular-session minutes (pro-rata on half-days), raw (unadjusted) | Opening-interval construction (e.g. 09:30→10:00 ET) |
| R7 | Daily bars | 1-day OHLCV SIP for corporate-action alignment and cross-checks | Dividend/split anchoring, gap accounting |
| R8 | Volume per minute bar | Non-negative share volume, zero allowed but explicit | Missing-vs-zero-volume distinction; halt detection |
| R9 | Timezone + DST handling | America/New_York session wall time; UTC storage; DST transitions derived from calendar, never hand-offset | Spring-forward/fall-back session length changes |
| R10 | Corporate actions | Ex-date, cash amount, payable date, split ratio per symbol (official source) | Raw-price continuity across distributions/splits |
| R11 | Symbol lifecycle | Ticker/CUSIP changes, halts, late listings, delistings in-window | Naive continuous series corruption |
| R12 | Missing-bar policy | `FAIL_CLOSED_SESSION_EXCLUSION`: any missing required minute → session excluded, never imputed | No silent forward-fill (MEC-0015 precedent) |
| R13 | Point-in-time availability | Per-field observability timestamp (see `RI01_POINT_IN_TIME.md`) | No look-ahead by construction |
| R14 | Provider delay semantics | Delayed-SIP accessibility boundary (resolved value, not assumption) | Eligibility instant for any future live use |
| R15 | Revision behavior | Whether the vendor revises bars after first publication, and how revisions are detectable | Revised-history backtests ≠ tradable history |

## 2. DATA NICE TO HAVE (improves precision; absence does not block)

| # | Input | Role |
|---|-------|------|
| N1 | Opening auction cross prints (dedicated auction endpoint) | Disambiguates R4/R5 without bar-close proxies |
| N2 | SIP NBBO quotes near decision boundaries | Executable-fill realism (MEC-0015 precedent); not needed for pure statistical replication |
| N3 | Pre-market / post-market bars | Overnight gap decomposition research (explicitly out of first scope) |
| N4 | Second venue/tape for cross-verification | Vendor-error detection |
| N5 | Corporate-action announcement timestamps | Announcement-vs-ex-date PIT refinement |

## 3. Explicit non-requirements for feasibility

- No execution/friction model (belongs to preregistration, not feasibility).
- No volatility/volume conditioning sets (quarantined secondary specifications).
- No macro-news calendars (quarantined).
- No options/GEX inputs (no authoritative feed; stays an untested explanatory hypothesis).

## 4. Contamination guardrails (binding on any future phase)

- HYP_007 intraday parameters/findings MUST NOT be recycled into RI-01 choices (R0: MEDIUM-HIGH contamination risk).
- HYP_003 consumed 2017–2022 SPY 1Min as in-sample for ORB; the 2023–2026 holdout stays sealed until explicit human authorization.
- Feasibility itself touches ZERO market data (synthetic fixtures only), so it cannot contaminate anything.
