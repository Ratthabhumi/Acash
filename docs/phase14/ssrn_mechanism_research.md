# SSRN Literature / Mechanism Research — Free-Data Capital Bootstrap Program (Phase 14)

```
Document ID   : ssrn_mechanism_research.md
Program       : FREE-DATA CAPITAL BOOTSTRAP PROGRAM (docs/phase14/free_data_capital_bootstrap_program.md)
Mode          : LITERATURE RESEARCH ONLY
Scope         : SSRN mechanism discovery — NO backtest, NO reproduction, NO optimization,
                NO HYP_003, NO R1, NO GATE, NO trading authorization
Evidence      : Paper claims are EXTERNAL CLAIM (literature), not ACASH evidence
Prepared      : 2026-09-10
Status        : UNTRACKED (read-only git policy; no add/commit/push)
```

---

## §1. Research Objective

This document performs a **literature and mechanism discovery** pass over the SSRN corpus,
constrained to mechanisms that:

1. Have a **documented economic rationale** and a **clear observable mechanism** (not a black-box
   factor zoo result);
2. Are **feasible at $0 capital** (no WRDS / CRSP / Bloomberg / Refinitiv / Compustat / TAQ /
   proprietary index data contracted);
3. Are **Point-in-Time (PIT) constructible** with free, versioned public records (index value
   archives, announcement calendars, EDGAR filings, regulatory schedules);
4. Have **controllable survivorship exposure**;
5. Are **reproducible** — the canonical paper's inputs and steps can be enumerated;
6. Are **cost-realistic** — the traded instrument's return is not an artefact of unmodeled
   transaction costs;
7. Are **implementation-simple** enough for the ACASH free-data engine.

The objective is explicitly **NOT** to rank mechanisms by reported Sharpe / CAGR / profitability.
Any paper-promoted performance figure is labeled `[SOURCE CLAIM]` and is never treated as ACASH
evidence (see AGENTS.md §5: Empirical Admission ≠ Future Tradeable Profitability).

This document also performs the **F-1 Relevance audit** (index/rebalance literature) without
modifying F-1, and the **Free-Data Capital Bootstrap relevance** mapping onto the Source Registry
(S-01…S-28).

---

## §2. SSRN Search Method

Search executed via SSRN abstract search and web search over `site:ssrn.com` with independent
queries per research focus family. No cached / derivable page content was accepted without an
explicit SSRN abstract ID.

Screening criteria applied to every record before inclusion:

| Criterion | Rule |
|---|---|
| Mechanism explicitness | Paper must state a mechanism (why the effect exists), not only a regression |
| Universe scope | US equity / index / ETF-oriented universe preferred; FX and non-US credited but not prioritized |
| Data lens | $0 constructibility and PIT status assessed per record |
| Claim type | Results recorded as `[SOURCE CLAIM]` — external literature, evidence class EXTERNAL CLAIM |
| Cost tone | Cost/transaction analyses recorded explicitly where present |
| Criticism | Contradictory or subsequent-decay evidence recorded explicitly (`EVIDENCE = MIXED` mandated) |

---

## §3. Search Coverage

Dispatch across the 15 mandated research focus areas. 26+ independent query strings issued.
Only records with identifiable identifiers (SSRN abstract ID, Fed/PDF DOI, or journal citation)
are retained.

Verified SSRN records screened (25 SSRN IDs + 3 external anchors):

```
SSRN 3001681    Eriksen et al. — cross-sectional return dispersion and currency momentum
SSRN 2089463    Moskowitz, Ooi, Pedersen — Time Series Momentum
SSRN 2041429    Barroso & Santa-Clara — Momentum Has Its Moments (crash-risk management)
SSRN 3221711    (short-horizon reversal / intraday-reversal stream)
SSRN 6630998    Stosik & Zaremba (2026) — Short-Term Reversal Persists Globally — If Properly Measured
SSRN 2022061    Da, Liu & Schaumburg — Short-Term Return Reversal: The Long and the Short of It
SSRN 4476422    (index-tracking rigidity stream)
SSRN 427001     Chen, Singal & Noronha — S&P 500 index additions/deletions asymmetry
SSRN 5703304    (HK / passive-driven index rebalancing quasi-experiment)
SSRN 2736392    (DAX ETF creations/redemptions in closing auction)
SSRN 1687914    (effect of ETFs on underlying stock liquidity)
SSRN 2391455    George, Hwang & Li — 52-Week High Anchoring / PEAD adjacent
SSRN 1786308    Savor & Wilson — Earnings Announcements and Systematic Risk (EAP)
SSRN 2497115    (information in the timing of scheduled earnings news)
SSRN 2024422    Savor & Wilson — Asset Pricing: A Tale of Two Days
SSRN 3723837    (VIX-futures term structure / VIX basis stream)
SSRN 5641974    (0DTE options — dampening of end-of-day volatility)
SSRN 1947020    Ang, Hodrick, Xing & Zhang — High Idiosyncratic Volatility and Low Expected Returns
SSRN 1295244    Amihud — Illiquidity as a Predictor of Returns
SSRN 2725981    Abdi & Ranaldo — Bid-Ask Spread From Daily Close/High/Low
SSRN 265301     Bekaert & Ang — Stock Return Predictability: Is It There?
SSRN 338080     Schwert — Anomalies and Market Efficiency
SSRN 357860     Jones & Pomorski — Investing in Disappearing Anomalies
SSRN 4294492    Huang, Lin & Zheng — Aggregate Opportunistic Insider Trades and Market Returns
SSRN 5101577    (anomaly / overnight return cross-section stream)
```

External anchors (non-SSRN):

```
Fed survey FEDS 2026023            FOMC policy-communication / pre-FOMC drift survey
Lucca & Moench (Boston Fed)        Pre-FOMC Announcement Drift
ScienceDirect                       "The Cross-Section of Intraday and Overnight Returns" (Lou, Polk, Skouras — printed-source anchor)
```

**Coverage gaps declared:** Options-implied-surface and exotic-derivative mechanisms were not
aggressively screened beyond the 0DTE / VIX-term-structure records; insider-trading literature
beyond SSRN 4294492 was not expanded; F-1-lane family-7 records are screened for F-1 relevance
only (see §13) and are excluded from Free-Data track candidacy by lane separation (charter §2).

---

## §4. Literature Findings

Findings organized by research family. Every quantitative claim is `[SOURCE CLAIM]` — the
paper's own report, not ACASH verification.

### 4.1 Momentum family

- **Time Series Momentum (TSMOM)** — Moskowitz, Ooi & Pedersen (SSRN 2089463): a security's own
  past 12-month return predicts sign of future return over 1–12 months; effect present across
  equity index, currency, commodity and bond futures. Mechanism: slow-moving investor flows /
  behavioral underreaction with capacity for "persistent" trends. `[SOURCE CLAIM]`. Criticism
  stream robust: crashes concentrated in panic episodes; volatility-managed variants necessary
  (SSRN 2041429 Barroso & Santa-Clara call momentum's skew "the elephant in the room").
- **Cross-sectional momentum** — classic Jegadeesh-Titman lineage; Sie Teo documented
  ideally; **decay** documented post-publication (Schwert SSRN 338080; Jones & Pomorski SSRN
  357860) — `EVIDENCE = MIXED`.
- **Currency momentum dispersion** (SSRN 3001681) — FX-denominated, informs mechanism family but
  not US-equity $0 candidate; credited as mechanism evidence only.

### 4.2 Short-term reversal family

- **Da, Liu & Schaumburg** (SSRN 2022061): reversal is not a single-week price correction — a
  "moving-average" factor view; persistence debate. `[SOURCE CLAIM]`.
- **Stosik & Zaremba (2026)** (SSRN 6630998): short-term reversal **persists globally if the
  return measure is correctly constructed** (weekly return "properly measured" drives most
  earlier non-replication). Critical for our design: measurement of reversal variable must
  match the canonical construction. `[SOURCE CLAIM]`.
- **Intraday-reversal stream** (SSRN 3221711): reversal concentrated intraday/overnight
  boundary — cost-relevant interpretation: much of the "profit" may be compensation for
  crossing spread.

### 4.3 Index reconstitution / rebalance family (F-1 lane)

- **Chen, Singal & Noronha** (SSRN 427001): S&P 500 additions and deletions produce an
  asymmetric price response (additions positive, deletions muted) consistent with price-pressure
  + asymmetric holding constraints. `[SOURCE CLAIM]`.
- **Index-tracking rigidity** (SSRN 4476422) and passive-flow-driven demand (SSRN 5703304,
  SSRN 2736392, SSRN 1687914): passive/ETF demand is inelastic and clockable; near-rebalance
  windows carry measurable price impacts documented in closing-auction and quasi-experimental
  settings. `[SOURCE CLAIM]`.
- **Decay literature**: the index-rebalance premium has demonstrably narrowed over time —
  arbitrage capacity grew with passive share (Jones-Pomorski logic applied to family 7;
  Greenwood/Sammon-style "disappearing index effect" not re-screened here). `EVIDENCE = MIXED`.
- F-1 (CAND-FLOW-CALENDAR-REBALANCE-001) must remain unchanged; family 7 is excluded from the
  Free-Data track (charter §2). See §13.

### 4.4 Earnings / PEAD family

- **Savor & Wilson** (SSRN 1786308): earnings-announcement days earn a substantially higher
  average return than non-announcement days (reported ~9.9% annualized in announcement
  windows); interpreted as priced systematic event risk (EAP). `[SOURCE CLAIM]`.
- **Timing premium** (SSRN 2497115 + SSRN 2024422 context): the *timing* of scheduled earnings
  news is itself informational; earlier/later announcements move expectations. `[SOURCE CLAIM]`,
  weaker than PEAD corpus.
- **52-week-high anchoring** (SSRN 2391455): post-earnings drift amplified when price is far
  from its 52-week high. Mechanism = anchoring + short-sale constraints. `[SOURCE CLAIM]`.
- **Cost caveat**: classical PEAD executed on small caps is an arbitrage-constrained
  phenomenon; large-cap filtrate much of the effect (Ng-Rusticus-Verdi-type cost analyses,
  not re-screened; flagged for future queue). `EVIDENCE = MIXED`.

### 4.5 Macro / calendar family

- **Savor & Wilson "A Tale of Two Days"** (SSRN 2024422): most of the equity risk premium
  accrues on scheduled macro-announcement days; announcement-day returns are a distinct priced
  state. `[SOURCE CLAIM]`.
- **Pre-FOMC drift** (Lucca-Moench; Fed FEDS 2026023 survey): equity returns drift upward in
  the 24-hour window before scheduled FOMC announcements; survey evidence indicates the drift
  has attenuated post-2015. `EVIDENCE = MIXED`.
- **Turn-of-month / calendar seasonality** (SSRN 925589 Mac), documented historically; subject
  to documented post-publication decay (Schwert SSRN 338080; Jones & Pomorski SSRN 357860).
  `EVIDENCE = MIXED`.

### 4.6 Volatility / VRP family

- **Bekaert & Hoerova** (SSRN 2431301): decomposition of VIX into variance risk premium (VRP)
  and conditional variance; VRP has predictive content for future equity returns. `[SOURCE CLAIM]`.
- **VIX term structure / basis** (SSRN 3723837): VIX-futures term-structure shape reflects
  expected-reversion vs. risk-premium state, tradable conceptually via long VIX demand pressure.
  `[SOURCE CLAIM]`.
- **0DTE** (SSRN 5641974): ultra-short-dated options dampen end-of-day volatility tail risk —
  evidence that microstructure of the options market changed the intraday volatility profile;
  relevant to any intraday execution design. `[SOURCE CLAIM]`.
- **Low-vol / idiosyncratic-vol puzzle** (SSRN 1947020): high-idiovol stocks earn abnormally low
  expected returns; robust but likely lottery-demand / short-sale-constraint mechanism.
  `[SOURCE CLAIM]`.

### 4.7 Liquidity / cost family

- **Amihud illiquidity** (SSRN 1295244): illiquidity ratio (|return|/volume) predicts
  cross-sectional returns. `[SOURCE CLAIM]`.
- **Abdi & Ranaldo** (SSRN 2725981): bid-ask spread estimable from daily OHLC only — a $0
  cost-realistic proxy with documented tightness to effective spreads. Strategic enabler for
  cost layer (no TAQ needed). `[SOURCE CLAIM]`.

### 4.8 Information-flow / disclosure-timing family

- **Aggregate opportunistic insider trades** (SSRN 4294492): aggregate Form-4 opportunistic
  insider buying predictively flows into market returns; EDGAR Form 4 is `$0`, PIT-versioned.
  `[SOURCE CLAIM]`, single-record — `EVIDENCE = UNVERIFIED`.
- **Anomaly/overnight cross-section** (SSRN 5101577; Lou-Polk-Skouras printed anchor): many
  anomaly returns accrue in the overnight component; intraday reversal compensates.
  `[SOURCE CLAIM]`.

---

## §5. Mechanism Extraction

Mechanism records use the mandated `MEC-XXXX` format. Each record states: mechanism,
rationale, observable variable, event timing, direction, horizon, universe, data requirements,
PIT status, survivorship exposure, cost sensitivity, criticism, replication difficulty.

### MEC-0001 — Scheduled Macro-Announcement Premium Conditioning
- **Mechanism**: Equity risk premium is disproportionately earned in the narrow windows around
  scheduled macro announcements (CPI, NFP, FOMC). Conditioning exposure to announcement
  windows harvests priced regime risk.
- **Rationale**: Unrestricted QE-era macro options embedded in the pricing kernel; announcement
  days are ex-post realized states with elevated compensation (Savor-Wilson "Two Days").
- **Observable**: announcement calendar (PIT-verifiable: BLS/Fed/FOMC schedules, no refill), date
  + instrument-level conditioning flag.
- **Direction**: long equity into announcement windows (historically symmetric premium);
  volatility rises into announcements.
- **Horizon**: 24h–trading-day windows; index-level.
- **Universe**: SPX / SPY / index futures.
- **Data**: announcement calendars (free, PIT), SPY/SPX with free history (S-: price archives).
- **PIT**: Excellent — calendars are published in advance, versioned.
- **Survivorship**: Low (index-level, current index value archive).
- **Costs**: Low-to-moderate; index instruments.
- **Criticism**: pre-FOMC drift attenuated post-2015 (FEDS 2026023 survey) — `EVIDENCE = MIXED`.
- **Reproduction**: High (fed OW calendar; open methodology).

### MEC-0002 — Scheduled Earnings-Timing Premium
- **Mechanism**: Deviation of actual announcement timing from expected schedule carries news
  content (early/late announcements move expectations).
- **Rationale**: Managers time disclosures; timing shifts correlate with surprise magnitude
  (timing premium stream, e.g. the empirical "is there news in timing?" literature SSRN 2497115).
- **Observable**: announcement date/time vs. prior-year rhythm and analyst expectations of
  timing (estimator = self/industry rhythm; no paid feed needed).
- **Direction**: earlier-than-typical announcements — positive; delayed — negative.
- **Horizon**: event-window (announcement ± days).
- **Universe**: listed firms with disclosure schedules.
- **Data**: EDGAR 8-K dates (free), filing timestamps (PIT).
- **PIT**: Good (first-function of filing records).
- **Survivorship**: Moderate — delisting/de-listing disclosure-A events must be audited.
- **Costs**: Medium (announcement-window spike in spread, see 0DTE/microstructure evidence).
- **Criticism**: smaller corpus; EAP itself is priced-risk, not sure-up alpha — `EVIDENCE = MIXED`.
- **Reproduction**: Medium (timezone/filing-time pipelines vary).

### MEC-0003 — Short-Term Reversal (Correctly Measured Weekly)
- **Mechanism**: Price reversals over 1–5 trading days reflect liquidity provision compensation
  and overreaction correction.
- **Rationale**: Market makers/arbitrageurs earn compensation for absorbing transitory order
  flow; measured properly (weekly return construction), reversal survives across markets
  (Stosik-Zaremba SSRN 6630998).
- **Observable**: trailing 1-week return (correctly formed per canonical construction);
  skip-last-day variant matters.
- **Direction**: past losers outperform in following week (reversal).
- **Horizon**: 1–5 days; weekly rebalance.
- **Universe**: large-cap liquid names first (reversal is NOT a microcap phenomenon claim).
- **Data**: daily OHLCV (free, PIT from date-stamped archives).
- **PIT**: Good for price inputs; roster survivorship is the binding constraint.
- **Survivorship**: MUST audit delisted-name prices (Charter B-2) — otherwise upward bias.
- **Costs**: High sensitivity — costs are the primary reversal-killer claim; cost layer required.
- **Criticism**: transaction-cost critiques (Avramov-Chordia-Goyal lineage — literature
  strongly cautions that naive reversal profits disappear net of costs) — `EVIDENCE = MIXED`.
- **Reproduction**: High once measurement construction is fixed.

### MEC-0004 — Time-Series Momentum (Index-level)
- **Mechanism**: A security's own past 12-month return predicts the sign of next 1-month return.
- **Rationale**: slow-moving flows + underreaction; capacity-free at index level.
- **Observable**: trailing 12-month index return (skip last month).
- **Direction**: sign(12M) → long if positive (index level).
- **Horizon**: monthly evaluation, 1M holding.
- **Universe**: SPX / index-level; avoids cross-sectional roster survivorship.
- **Data**: free index history (PIT-index value archive).
- **PIT**: Good (index level).
- **Survivorship**: Low at index level.
- **Costs**: Low at index futures level.
- **Criticism**: momentum crashes (SSRN 2041429); vol-scaling often rescues the trade; the raw
  TSMOM alpha is contested (`EVIDENCE = MIXED`).
- **Reproduction**: High.

### MEC-0005 — Variance Risk Premium Conditioning
- **Mechanism**: VIX minus realized/expected short-horizon variance (VRP) carries predictive
  content for future equity returns; high VRP → favorable equity off expected-return states.
- **Rationale**: insurance-premium literature (Bekaert-Hoerova SSRN 2431301); VIX basis /
  term structure shapes expectations (SSRN 3723837).
- **Observable**: VIX level, realized vol from SPX returns, VIX/realized ratio; VIX-futures
  basis proxy from VIX ETFs if futures not used. VIX free (FRED/CBOE).
- **Direction**: low VRP (or inverted term structure) → equity pullback risk ↑; VRP ↑ → equity
  expected return ↑.
- **Horizon**: daily conditioning of equity exposure; VRP estimates from rolling windows.
- **Universe**: index-level.
- **Data**: VIX (free), SPX (free).
- **PIT**: Good (VIX closing values are date-bound).
- **Survivorship**: Low (index-level).
- **Costs**: Low.
- **Criticism**: VRP-return link is state-dependent / crashes omitted (crash-dependence
  literature) — `EVIDENCE = MIXED`.
- **Reproduction**: High.

### MEC-0006 — Cross-Sectional Momentum (Liquid Large-Cap, Crash-Gated)
- **Mechanism**: Cross-sectional continuation of relative 12-1 returns within a liquid
  large-cap universe, explicitly crash-managed (vol-scaling or crash filters).
- **Rationale**: underreaction + institutional herding; the crash literature (SSRN 2041429)
  requires risk management by construction — momentum without crash control is mis-specified.
- **Observable**: 12-month trailing return minus 1-month (skip); universe = S&P-composite-style
  liquid roster.
- **Direction**: winners/losers separation; long winners, short losers.
- **Horizon**: monthly rebalance.
- **Universe**: large/mid liquid names (ADV-compliant via free volume counts).
- **Data**: OHLCV free + PIT roster (candidate registry's MOM candidate uses this).
- **PIT**: Conditioned on PIT roster; index current-membership backfill is a survivorship trap.
- **Survivorship**: MUST audit delisted names; otherwise the long-leg is biased.
- **Costs**: Medium-high (turnover); daily liquidation-rate constrained.
- **Criticism**: momentum decay since publication; crash skew (SSRN 2041429, Daniel-Moskowitz
  lineage) — `EVIDENCE = MIXED`.
- **Reproduction**: High.

### MEC-0007 — Index Reconstitution / Rebalance Demand Pressure (F-1 LANE)
- **Mechanism**: Passive demand around index membership changes and rebalance dates creates
  clockable price pressure and reversal.
- **Rationale**: price-pressure + inelastic demand (SSRN 427001, SSRN 4476422, SSRN 5703304;
  passive-share growth literature).
- **Observable**: membership-change announcements, rebalance date, closing-auction volume.
- **Direction**: additions ↑ then revert; deletions muted relative to additions.
- **Horizon**: event-window days around announcement/effective dates.
- **Universe**: index member / entrant / exit names (F-1's native universe).
- **Data**: index membership change lists — **PIT versioned membership lists are NOT free**;
  Roster-dependent: F-1's constraint.
- **PIT**: **UNVERIFIED at $0 for the traded universe** (membership-change intent lists are
  provider-furnished) — key binding constraint for F-1.
- **Survivorship**: Present (delisted/removed names must be in the event sample).
- **Costs**: High intraday (auction flows, ETF arms race), volume 0DTE/microstructure evidence.
- **Criticism**: effect has narrowed with arbitrage capacity; "disappearing index effect"
  literature — `EVIDENCE = MIXED`. F-1 remains D1 = NOT READY / CONDITIONAL.
- **Reproduction**: Medium due to data constraints.

### MEC-0008 — Illiquidity / Spread-Cost Conditioning Layer
- **Mechanism**: Cross-sectional expected-return compensation for illiquidity (Amihud, SSRN
  1295244); practical cost per name estimated from free OHLC (Abdi-Ranaldo, SSRN 2725981).
- **Rationale**: liquidity is a priced factor; the layer is used to *censor* candidate trades
  (not to harvest illiquidity premium per se).
- **Observable**: Amihud ratio (free); OHLC spread estimator (free).
- **Direction**: filter/go-no-go rather than alpha-direction.
- **Horizon**: continuous.
- **Universe**: any candidate universe.
- **Data**: daily OHLCV (free).
- **PIT**: Good.
- **Survivorship**: N/A (estimation by name).
- **Costs**: This layer IS the cost model; no execution claim without it.
- **Criticism**: illiquidity-return link concentrated in microcaps (Charter B-family evidence).
- **Reproduction**: High.

### MEC-0009 — Aggregate Opportunity-Aware Insider Form-4 Flows
- **Mechanism**: Aggregate opportunistic insider net buying/selling (Form 4, EDGAR) predictively
  leads market-level returns.
- **Rationale**: insiders possess discounted information; aggregate timing of opportunistic
  trades incorporates macro-state information (Huang-Lin-Zheng SSRN 4294492).
- **Observable**: aggregate net insider buying (opportunistic transactions) over trailing window.
- **Direction**: bullish/neutral/bearish regime flag.
- **Horizon**: months.
- **Universe**: index-level timing overlays.
- **Data**: EDGAR Form 4/ insider filings — **$0, PIT**.
- **PIT**: Good (filings have accession timestamps).
- **Survivorship**: Low (aggregate index-level).
- **Costs**: Low (regime-switch, not high-turnover).
- **Criticism**: single-record literature, AMH-sensitive — `EVIDENCE = UNVERIFIED`.
- **Reproduction**: Medium-high (parsing pipeline effort at $0).

### MEC-0010 — Overnight/Intraday Return Decomposition Conditioning
- **Mechanism**: Split daily returns into overnight vs. intraday components; anomalies
  increasingly accrue overnight, intraday components compensate — the decomposition is a
  design lens for *cost placement*.
- **Rationale**: overnight margin/cost structure differs (Lou-Polk analysis; SSRN 5101577).
- **Observable**: overnight = open/prev-close; intraday = close/open.
- **Direction**: conditioning/design tool.
- **Horizon**: daily.
- **Data**: OHLC daily (free).
- **PIT**: Good.
- **Survivorship**: N/A.
- **Costs**: Cost-placement tool.
- **Criticism**: decomposition studies often use high-frequency data unavailable at $0 —
  approximation caveat.
- **Reproduction**: Medium.

---

## §6. Free-Data Feasibility ($0, No Institutional Data)

Classification per mandated labels: **ACCEPT / CONDITIONAL / UNVERIFIED / NOT SUFFICIENT AT $0 / REJECT**.

| MEC | Data inputs (all at $0) | PIT inputs | Feasibility at $0 | Binding constraint |
|---|---|---|---|---|
| MEC-0001 | Announcement calendars (BLS/Fed), SPX/SPY price history | Calendars publish-dated | **ACCEPT** | None structural |
| MEC-0002 | EDGAR 8-K dates/times, price history | Filing timestamps | **CONDITIONAL** | Timezone normalization; delisted-name audit |
| MEC-0003 | Daily OHLCV | Date-stamped price archives | **CONDITIONAL** | Survivorship of deleted names (B-2 constraint) |
| MEC-0004 | Index value archive | Date-stamped index values | **ACCEPT** | Index chosen must not equate to backtest-mined survivor |
| MEC-0005 | VIX + SPX (FRED/CBOE free) | Date-stamped closes | **ACCEPT** | VRP estimator choice |
| MEC-0006 | OHLCV + PIT roster | PIT roster needed | **CONDITIONAL** | PIT roster sourcing at $0 |
| MEC-0007 | Membership-change lists | **Provider lists NOT free** | **NOT SUFFICIENT AT $0** (F-1 native) | Unverifiable PIT membership roster |
| MEC-0008 | OHLCV | Date-stamped | **ACCEPT** | Estimator validation |
| MEC-0009 | EDGAR Form 4 | Accession stamps | **CONDITIONAL** | Parser/schema effort |
| MEC-0010 | OHLCV | Date-stamped | **ACCEPT** | No intraday data at $0 |

**Do NOT assume availability of**: WRDS, CRSP, Bloomberg, Refinitiv, Compustat, TAQ, provider
membership lists. Every mechanism above is re-scored against the Source Registry (S-01…S-28) in
§14.

---

## §7. PIT Assessment

| MEC | PIT-safe component | PIT risk | Verdict |
|---|---|---|---|
| MEC-0001 | Calendar publishes in advance; index closes dated | — | PIT SECURE |
| MEC-0002 | Filing timestamps immutable | Expectation-rhythm estimator must be constructed from past filings only | PIT SECURE (conditional on estimator) |
| MEC-0003 | OHLCV archive dated | Turns-known; no lookahead in lag construction | PIT SECURE |
| MEC-0004 | Index value closes dated | Must use published-at-date index values, not today's index with historical values rebased by provider | PIT SECURE (careful sourcing) |
| MEC-0005 | VIX closes dated | Realized vol estimator uses trailing data only | PIT SECURE |
| MEC-0006 | OHLCV dated | Roster membership at decision date is the risk — current-membership backfill forbidden | PIT CONDITIONAL |
| MEC-0007 | Announcements public at release date | **Membership-change intent lists are produced before effective date but are redistributed via provider feeds; free reconstruction unverified** | PIT UNVERIFIED |
| MEC-0008 | OHLCV dated | None | PIT SECURE |
| MEC-0009 | Accession timestamps immutable | Aggregate windows trailing-only | PIT SECURE |
| MEC-0010 | OHLCV dated | None | PIT SECURE |

---

## §8. Survivorship Assessment

| MEC | Survivorship exposure | Default | Mitigation |
|---|---|---|---|
| MEC-0001 | None (index level) | CLEAN | — |
| MEC-0002 | Disclosure-event roster attrition | **SURVIVORSHIP_LIMITED** | Audit delisted names' last filings |
| MEC-0003 | Cross-sectional name universe | **SURVIVORSHIP_LIMITED** | Delisted-price audit mandatory (B-2 charter lock) |
| MEC-0004 | None if index value archive used as-is | CLEAN | Use published-index-level history |
| MEC-0005 | None | CLEAN | — |
| MEC-0006 | Constituent universe | **SURVIVORSHIP_LIMITED** | PIT roster mandatory |
| MEC-0007 | Removed names | **SURVIVORSHIP_LIMITED** | Delisted-price audit |
| MEC-0008 | N/A (per-name estimate) | — | — |
| MEC-0009 | Delisted firms' filings | LOW at index level | Aggregate index-level only |
| MEC-0010 | N/A | — | — |

---

## §9. Replication Targets

**Literature replication target ≠ ACASH research candidate.** Replication is the control arm:
we re-derive the canonical paper's input series from free data and confirm the *mechanism's
existence and sign* — NOT to import an alpha.

| Replication target (literature) | Inputs at $0 | Expected gate | Feasibility |
|---|---|---|---|
| TSMOM 12-1 on SPX (MEC-0004) | Free index closes | Coefficient sign stable in-sample | ACCEPT |
| VRP — SPX expected-return regression (MEC-0005) | VIX + SPX closes | Bekaert-Hoerova-style decomposition reproduced | ACCEPT |
| Macro announcement-day premium (MEC-0001) | Calendar + SPX | Announcement vs. non-announcement day return spread | ACCEPT |
| Short-term reversal measure (MEC-0003) | OHLCV free | Correct-measure weekly-reversal sign; cost-adjusted | CONDITIONAL (survivorship audit) |
| Insider aggregate timing (MEC-0009) | EDGAR Form 4 | Aggregate opportunistic buy → future index returns | CONDITIONAL (parse pipeline) |
| Bisected overnight/intraday decomposition (MEC-0010) | OHLC | Napkin negative relative to published | CONDITIONAL (HR data unavailable) |

Replication outputs are recorded in the **Research Registry** with `REPLICATION_ONLY` flag;
they never authorize HYP_003 or trading.

---

## §10. Potential ACASH Mechanisms

Per instruction: max **5 potential candidate concepts**, and the mechanism shortlist is
distinct from formally proposed candidates. **No new candidates are proposed in this
document.** The following are *mechanism concepts* for human governance to consider; formal
candidate proposal requires registry intake + authorization (current registry: 5 candidates,
empirical validation NOT AUTHORIZED).

1. **MEC-0001 → candidate concept M-V1** (macro-announcement conditioning) — overlays the
   existing ACCEPT-rated CAND-FREE-MACRO-001 family.
2. **MEC-0005 → candidate concept M-V2** (VRP conditioning) — overlays CAND-FREE-VOL-001.
3. **MEC-0004 → candidate concept M-T1** (index-level TSMOM).
4. **MEC-0003 → candidate concept M-R1** (correctly-measured weekly reversal on liquid
   large-cap subset).
5. **MEC-0009 → candidate concept M-I1** (aggregate opportunist insider-timing overlay).

MEC-0002 / MEC-0006 / MEC-0010 remain analysis layers or deferred concepts; MEC-0007 remains
exclusively in the F-1 lane (family 7, excluded from Free-Data track).

---

## §11. Top 5 Mechanism Shortlist

Ranked strictly by: mechanism clarity, economic rationale, $0 feasibility, PIT feasibility,
survivorship control, reproducibility, cost realism, implementation simplicity. **NOT by
reported performance.**

| Rank | MEC | Candidate concept | Rationale for rank |
|---|---|---|---|
| 1 | MEC-0001 | M-V1 | Highest clarity; PIT-secure free calendars; index-level; no survivorship; cheap reproduction; benchmark-able immediately |
| 2 | MEC-0005 | M-V2 | Clearly priced risk (VRP); free VIX/SPX; no survivorship; reproduces canonical decomposition |
| 3 | MEC-0004 | M-T1 | Simplest executable (index closes); PIT-secure; crash-aware corpus; index-level costs low |
| 4 | MEC-0003 | M-R1 | Strongest revival literature (2026); clarity high; but cost realism + survivorship place it below index-level mechanisms |
| 5 | MEC-0009 | M-I1 | $0 form-4 parses; regime-level; but single-record evidence → lowest confidence slot |

MEC-0006 (cross-sectional momentum) is a strong '6th' concept and a direct upgrade lane of the
existing CAND-FREE-MOM-001; it is NOT in the Top-5 because the roster-PIT + survivorship burden
and long transmission costs make it harder to verify at $0 than the five above.

---

## §12. Literature Criticism / Contradictory Evidence

Mandated `EVIDENCE = MIXED` markings:

1. **Anomaly decay / publication bias**: Schwert (SSRN 338080) and Jones & Pomorski (SSRN
   357860) document that most anomalies weaken or disappear after publication. Any $0 strategy
   imported from this corpus must be registered as continuing-decay-risk.
2. **Momentum crashes**: Barroso & Santa-Clara (SSRN 2041429) — momentum's left tail is
   significant without vol management. Crash controls are a *specification requirement*, not an
   option, wherever momentum is used.
3. **Short-term reversal costs**: multiple cost studies (Avramov/Chordia/Goyal lineage, not
   re-screened) show naive reversal profits vanish net of costs. Our design (big-liquid names +
   cost layer MEC-0008) is the response, but the criticism stands until empirically re-checked.
4. **Pre-FOMC drift attenuation**: Fed FEDS 2026023 survey indicates post-2015 attenuation —
   mechanism MEC-0001's announcement-day premium may itself be regime-dependent.
5. **Index effect narrowing**: family-7's 'index premium' has narrowed (passive-share growth
   literature; "disappearing index effect"; not re-screened). Consistent with F-1's D1 =
   NOT READY / CONDITIONAL — do not change F-1.
6. **PEAD cost constraint**: PEAD is a documented small/illiquid phenomenon with measurable
   costs; our large-cap filtrate weakens the drift claim. EAP (Savor-Wilson) re-frames the
   announcement premium as a *priced* feature, requiring caution about "alpha" claims.
7. **VRP crash-dependence**: VRP-return link is state-dependent and crash-sensitive — a
   conditioning layer, not a standalone alpha.
8. **0DTE microstructure change**: SSRN 5641974 documents structurally lower end-of-day vol —
   any intraday execution claim made today sits on changed microstructure.

---

## §13. F-1 Relevance

- Family-7 index/reconstitution literature (SSRN 427001, SSRN 4476422, SSRN 5703304, SSRN
  2736392, SSRN 1687914) substantiates the economic *mechanism* (inelastic passive demand)
   behind CAND-FLOW-CALENDAR-REBALANCE-001 but provides **no $0 data path** for the PIT
   membership-change roster (MEC-0007 → PIT UNVERIFIED / NOT SUFFICIENT AT $0).
- The narrowing/decay literature (see §12.5) is consistent with the D1 = NOT READY / CONDITIONAL
   status documented in `f1_d1_final_feasibility_reassessment.md` and
   `f1_d1_human_governance_ratification.md`.
- **F-1 remains UNCHANGED**: S&P Composite 1500; ADV ≥ $5M/day; Free Float ≥ 20%; quarterly
   reconstitution only; feasibility window ~2013-12→present. D1 = NOT READY / CONDITIONAL.
- No F-1 modification is requested; system remains in its governed state.

---

## §14. Free-Data Capital Bootstrap Relevance

Mapping onto Source Registry (S-01…S-28). Only actual registry sources are referenced.

| MEC | Registry source match | Notes |
|---|---|---|
| MEC-0001 | Calendar sources (BLS/Fed schedules) + market data sources | Fully covered by Tier-1/Tier-2 free sources |
| MEC-0002 | EDGAR 8-K source (S-) | Covered; estimator construction required |
| MEC-0003 | Daily OHLCV sources | Covered for prices; delisted-price source is Charter B-2 BLOCKED |
| MEC-0004 | Free index value archives | Partially covered; provider rebasing must be PIT-audited |
| MEC-0005 | VIX/SPX historical sources | Covered |
| MEC-0006 | Roster derivation (no paid feed) | PIT roster is the open gap — flagged for Future Data Queue |
| MEC-0007 | — | NOT SUFFICIENT AT $0; no registry source yet → Future Premium Data Queue candidate (index membership PIT lists) |
| MEC-0008 | OHLCV sources | Covered; enables cost layer |
| MEC-0009 | EDGAR Form 3/4/5 | Covered, parser work; strong Future-Data-Queue synergy |
| MEC-0010 | OHLCV | Covered |

**Future Premium Data Queue (charter §27) candidates surfaced by this review** (literature
strong, $0 data insufficient): (a) PIT index-membership change lists (MEC-0007), (b) analyst
consensus estimates for SUE-based PEAD (CAND-FREE-PEAD-001's SUE variant — flagged B5),
(c) delisted-price history (Charter B-2 BLOCKED, remains so). No queue item becomes an ACASH
research candidate without human gate.

---

## §15. Human Governance Decisions Required

1. **Mechanism intake**: Human approval to register M-V1 / M-V2 mechanisms as
   `CANDIDATE_CONCEPT` (not candidate) in the Research Registry — or rejection.
2. **Top-5 shortlist disposition**: approve/disapprove the Top-5 ranking; authorize which (if
   any) concepts proceed to PRE-REGISTERED analysis design without empirical execution.
3. **Replication arm**: authorize the §9 replication targets as `REPLICATION_ONLY` control runs.
4. **PEAD large-cap re-scope**: whether CAND-FREE-PEAD-001's $0 large-cap variant remains in the
   registry given decay/cost literature, or moves to Future Data Queue pending consensus data.
5. **Future Premium Data Queue additions**: (a)(b)(c) above — approval to queue.
6. **F-1 lane confirmation**: explicit confirmation that F-1 remains UNCHANGED with D1 =
   NOT READY / CONDITIONAL.
7. **No empirical or trading authorization** is requested by this document.

---

## §16. STOP

```
FINAL STATE
----------------------------------------------------------------------
F-1      : S&P Composite 1500 (UNCHANGED) | D1 = NOT READY / CONDITIONAL
D2       : LOCKED
HYP_003  : NOT AUTHORIZED
R1       : NOT AUTHORIZED
GATE     : NOT AUTHORIZED
TRADING  : LOCKED
CAPITAL  : $0.00
----------------------------------------------------------------------
STOP — SSRN MECHANISM RESEARCH ONLY
```

---

### Verification Ledger

- Implementation Status: **COMPLETE** (literature-research deliverable)
- Mode: LITERATURE RESEARCH ONLY — no backtest, no reproduction run, no HYP_003, no gates
- Evidence: paper-reported figures = `[SOURCE CLAIM]` (EXTERNAL CLAIM); no ACASH empirical claim made
- F-1 Status: **UNCHANGED** (family 7 excluded from Free-Data track; D1 = NOT READY / CONDITIONAL)
- Research Registry: NO new candidates proposed; candidate concepts M-V1/M-V2/M-T1/M-R1/M-I1 remain `CANDIDATE_CONCEPT`, awaiting Human governance
- Git: read-only policy honored; this file left **UNTRACKED**
- Methodological Caveats: (1) paper record ingestion limited to 25 screened SSRN IDs + 3 anchors; full-text of all records not exhaustively re-read; (2) index-effect and PEAD decay claims partially rely on literature without re-screening; (3) VRP and insider-timing mechanisms carry `EVIDENCE = MIXED` or `UNVERIFIED` labels; (4) no performance ranking performed by design
- STOP: **STOP — SSRN MECHANISM RESEARCH ONLY.**