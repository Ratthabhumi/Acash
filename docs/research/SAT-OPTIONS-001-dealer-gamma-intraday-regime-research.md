# SAT-OPTIONS-001 — Dealer-Gamma Intraday Regime Research (ARCHIVE ONLY)

```text
RESEARCH_BRANCH_ID = SAT-OPTIONS-001
STATE = RESEARCH_ARCHIVE_ONLY
HYPOTHESIS_ID = NONE
MECHANISM_ID = NONE
PREREGISTRATION = NONE
BACKTEST_AUTHORIZATION = NONE
DATA_ACCESS_AUTHORIZATION = NONE
```

- **Document ID:** `docs/research/SAT-OPTIONS-001-dealer-gamma-intraday-regime-research.md`
- **Authorization:** `AUTHORIZE_SAT_OPTIONS_001_RESEARCH_ARCHIVE_DOCUMENTATION`
- **Canonical HEAD at archive:** `065a3b4cd81f8d2befb4e61e4348f1061e3f425d`
- **Role:** documentation-only encoding of externally completed research.
  No hypothesis created. No preregistration. No backtest. No data access.
  No literature research performed in this task.

This branch is preserved for FUTURE satellite research only and is explicitly
separate from `CORE-001` / `HYP_009`. It has ZERO authority over CORE-001.

---

## 1. High-Level Research Conclusion

Public option Open Interest and gamma-related information may contain useful
microstructure information, but the strongest empirical mechanism is NOT
"large OI strike = automatic support/resistance."

The more defensible mechanism is:

```text
OPTIONS_POSITIONING_PROXY
→
DEALER_HEDGING_DEMAND
→
CONDITIONAL_INTRADAY_VOLATILITY
AND
CONDITIONAL_MOMENTUM_OR_REVERSAL
```

Scientific distinction:

- positive dealer gamma tends to imply hedging flows that oppose underlying moves;
- negative dealer gamma tends to imply hedging flows that reinforce underlying moves;
- this may create conditional reversal vs continuation behavior;
- liquidity interacts materially with this mechanism.

Do NOT phrase this as guaranteed profitability.

## 2. Data-Timing Limitation (Binding for Future Work)

`OFFICIAL_OPTION_OPEN_INTEREST_IS_NOT_INTRADAY_LIVE_POSITION_DATA`.

Public OI observed during a trading session generally represents the previous
night's end-of-day open-interest snapshot. Therefore GEX based on
`YESTERDAY_OI × CURRENT_GAMMA` is NOT equivalent to live dealer inventory.
Intraday changes may occur in spot, implied volatility, time-to-expiry, and
option gamma while the official OI count still reflects the prior-night
snapshot. This limitation is especially important for 0DTE options.

## 3. Dealer-Sign Identification Problem (Binding for Future Work)

`OPEN_INTEREST_ALONE_DOES_NOT_IDENTIFY_DEALER_POSITION_SIGN`.

OI tells how many contracts remain open. It does NOT reveal, by itself, which
participant is long, which is short, dealer inventory sign, or dealer net gamma
sign by strike. Retail-style assumptions (dealer short all calls; dealer long
all puts; call gamma positive / put gamma negative as dealer-inventory
convention) must be treated as MODEL ASSUMPTIONS, not observed facts.
No silent dealer-sign assumption is permitted in future ACASH research.

## 4. Public-OI GEX Usefulness

Public-OI-based GEX may still be useful as a REGIME PROXY, especially for
non-0DTE structures, but its reliability is materially lower for 0DTE because
intraday position formation may not be represented by previous-night OI.
Future ACASH research must distinguish `NON_0DTE_OI_BASED_GAMMA_PROXY` from
`0DTE_FLOW_ESTIMATED_GAMMA`. They MUST NOT be silently combined into one
data-generating process.

## 5. Claims to Avoid (NOT ESTABLISHED GENERALLY)

- large OI strike is always support;
- large OI strike is always resistance;
- gamma wall always pins price;
- touching one standard deviation automatically implies mean reversion;
- +1SD / -1SD zones guarantee 65–75% reversal;
- high IV predicts market direction;
- intraday OI shown on a chart is necessarily live official OI.

Do not encode any of these as ACASH assumptions.

## 6. IV / Expected-Move Interpretation

Implied volatility contains information about future realized volatility and
expected movement magnitude. It is more naturally interpreted as a RANGE /
VOLATILITY information variable than as a directional alpha signal.

Canonical conceptual approximation (research context only, NOT a strategy,
no numerical threshold authorized):

```text
EXPECTED_MOVE_1D ≈ SPOT × IV × sqrt(1 / 252)
```

## 7. Future Satellite Candidate Order

- **SATELLITE_A** — `GAMMA_REGIME_X_FUTURE_INTRADAY_VOLATILITY`: estimated gamma
  regime → future short-horizon realized volatility. Direction to test: positive
  gamma → lower subsequent realized volatility; negative gamma → higher.
- **SATELLITE_B** — `GAMMA_REGIME_X_INTRADAY_MOMENTUM_REVERSAL`: past intraday
  return × estimated dealer gamma regime → future intraday return. Direction to
  test: negative gamma → stronger continuation/momentum; positive gamma →
  stronger reversal.
- **SATELLITE_C** — `STRIKE_LOCAL_PINNING_OR_WALL_EFFECTS`. Lowest priority:
  higher model risk, higher data-mining risk, weaker general evidence, greater
  dependency on strike-level positioning assumptions.

## 8. Preferred Future Market Scope (Scope Only, No Dataset Authorized)

- Options source: `SPX_OPTIONS` (structurally more relevant for index-option
  dealer gamma research than SPY options alone).
- Underlying response candidates: `ES`, `SPY`.

## 9. Likely Future Data Requirements (Requirements Only — Do NOT Fetch)

Historical SPX option chain; OI by strike/expiration; IV or quotes sufficient
for Greeks; point-in-time timestamps; underlying intraday SPX/ES/SPY prices;
expiration metadata; contract multiplier; liquidity metrics; realized
volatility; optional trade prints, aggressor-side inference, opening/closing
classification, participant/inventory information if available.
No provider is selected in this task.

## 10. Future Control Variables (Design Considerations Only — Nothing Frozen)

Liquidity; realized volatility; implied volatility; time of day; macro
announcement days; expiration bucket; 0DTE vs non-0DTE; opening gap; previous
intraday return. No control specification frozen. No regression model authorized.

## 11. 0DTE Caution

0DTE is a distinct research problem: same-day positions may open and close
intraday without ever appearing in official end-of-day OI. Future 0DTE work
should preferably use `FLOW_ESTIMATED_POSITIONING` rather than treating
previous-night OI as live 0DTE dealer inventory. No 0DTE hypothesis is created
in this task.

## 12. Evidence Classification

STRONGER_EVIDENCE: dealer gamma can affect intraday volatility dynamics;
positive vs negative gamma may create reversal vs continuation differences;
liquidity matters as an interaction variable; IV contains information about
future volatility; expiration-related pinning has documented evidence.

WEAKER_OR_CONDITIONAL_EVIDENCE: strike-level "wall" effects as generic intraday
support/resistance; retail GEX sign conventions; direct directional prediction
from IV alone; fixed 1SD reversal probabilities.

MODEL_RISK: inferring dealer position sign from public OI; treating
previous-night OI as live intraday inventory; mixing 0DTE and non-0DTE gamma
reconstruction; silently assuming customer/dealer side.

## 13. Source References (Topic-Level Only)

Per the documentation-only boundary, only the supplied topic-level references
are preserved; no new literature research was performed and no bibliographic
fields are invented:

- intraday momentum and gamma-related hedging;
- Gamma Fragility;
- 0DTE market-maker gamma and volatility;
- Cboe evidence on 0DTE market impact;
- public-OI dealer-gamma reconstruction;
- expiration pinning;
- implied volatility and realized-volatility forecasting.

```text
SOURCE_METADATA_TO_VERIFY_BEFORE_FORMAL_PREREGISTRATION
```

## 14. Governance Status

- Branch: `SAT-OPTIONS-001 = RESEARCH_ARCHIVE_ONLY`
- Hypothesis / mechanism / preregistration / backtest / data authority: NONE
- Paper `NOT_AUTHORIZED`; live `LOCKED`; capital `$0.00`; `NO_REAL_ORDERS=true`
- CORE-001 / HYP_009: NOT modified, NOT reinterpreted.

No next execution authorization is created by this task. Future Satellite A/B/C
hypotheses, if ever opened, require separate human authorization under new
hypothesis identifiers.
