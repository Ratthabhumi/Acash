# Research Intake — Market Structure / Quant Concepts

**Document Type:** RESEARCH INTAKE / KNOWLEDGE CAPTURE (durable, governance-safe)
**Status:** CAPTURED — NOT AUTHORIZED FOR EMPIRICAL VALIDATION
**Version:** 1.0

> **Read this first.** This document is a *research intake / knowledge-capture artifact only*. It records
> concepts surfaced from trading/quant social-media content. It does **NOT** create HYP_003, does **NOT**
> assign any hypothesis ID, does **NOT** authorize any research or execution activity, and must never be
> interpreted as strategy authorization.

---

## 1. Purpose

Capture, classify, and preserve useful market-structure and quant concepts identified from five pieces of
trading/quant social-media content, so that future ACASH research can evaluate them under governance
without re-discovery or misremembering their epistemic status.

Core principle being recorded:

```text
FEATURE != EDGE
INFORMATION != PREDICTIVE VALUE
MODEL != PERFORMANCE
```

Every claim in this document is tagged with an explicit evidence label (see §13). No source claim is
upgraded to a fact merely by being captured here.

---

## 2. Governance Boundary

The following remain **unchanged** by this document:

| Item | State |
| :- | :- |
| D17-E | HOLD |
| MEC-0013 | ARCHIVED / Option C |
| HYP_003 | NOT CREATED |
| R1 | NOT STARTED |
| Backtest | LOCKED |
| Live trading | LOCKED |
| ACASH canonical capital | $0 |

Maintained distinction:

```text
INFRASTRUCTURE READY
!= STRATEGY QUALIFIED
!= PAPER AUTHORIZED
!= LIVE AUTHORIZED
```

**This document does NOT authorize:** any hypothesis creation, research start, backtest, Paper run,
Live run, data feed creation, data purchase, dependency addition, strategy/E3/E3.5/E3.6 code change,
infrastructure change, or deployment.

---

## 3. Source Summary

| Source | Topic | Nature |
| :- | :- | :- |
| 1 | Order Flow / Footprint / Liquidity | EDUCATIONAL/SOCIAL MEDIA CLAIMS |
| 2 | Quant Pipeline / Probability / Clustering | EDUCATIONAL/SOCIAL MEDIA CLAIMS |
| 3 | Quant Programming Languages / GetCracked | EDUCATIONAL CONTENT (engineering) |
| 4 | "80/20" NASDAQ Level Strategy | DISCRETIONARY TRADING CONCEPT |
| 5 | GEX / 0DTE / Open Interest / Gamma | MARKET-STRUCTURE CONCEPT (modelled estimate) |

All five are SOURCE CLAIMS. None is a peer-reviewed study. None is treated as empirical evidence in this
document.

---

## 4. Order Flow / Footprint / Liquidity

### Source claims

- Order flow can provide useful information about short-term market behavior, execution, and liquidity. `SOURCE CLAIM`
- Footprint charts and liquidity heatmaps can provide additional market detail. `SOURCE CLAIM`
- Better information does not automatically produce better performance. `SOURCE CLAIM / INFERENCE`
- The same tool and strategy can produce different outcomes across traders because implementation,
  entry, exit, risk, and interpretation differ. `SOURCE CLAIM / INFERENCE`
- Order flow does not reveal the full intent of participants. `INFERENCE`
- A large sell order could represent opening a short, closing a long, hedging, market making, or part of
  a larger execution. `SOURCE CLAIM` (illustrative; disposition of a single order is generally UNKNOWN to a
  market observer)
- Order flow should therefore be treated as information, not automatically as an edge. `RESEARCH PRINCIPLE`

### ACASH interpretation

Potential future data/features (captured for the Research Track only):

- executed trade flow
- order-flow imbalance
- footprint-derived features
- displayed liquidity
- liquidity changes
- volume dynamics

### Research principle

```text
ORDER FLOW = INFORMATION
ORDER FLOW != AUTOMATIC EDGE
```

Any future use must test incremental predictive value rather than assume profitability.
`RESEARCH PRINCIPLE`

---

## 5. Quant Pipeline / OOS / Regime Stability

### Source claims

- Multi-asset inputs can feed quantitative models. `SOURCE CLAIM`
- Feature engineering, probability scoring, and trade clustering are legitimate components of quant
  research. `SOURCE CLAIM`
- A clean quantitative pipeline does not guarantee performance. `SOURCE CLAIM / INFERENCE`
- Historical relationships can fail when: market regime changes, volatility changes, correlations
  break, market microstructure changes, transaction costs change, liquidity changes. `INFERENCE` (widely
  supported; still covers SOURCE CLAIM)
- Historical probability estimates are not sufficient if they are unstable out of sample. `RESEARCH PRINCIPLE`
- Professional trading can combine quantitative processes with discretionary interpretation and risk
  protocols. `SOURCE CLAIM`

### ACASH interpretation — general research design principle

```text
MODEL QUALITY != PERFORMANCE
```

A candidate model should eventually be evaluated through:
`Train → Validation → Out-of-sample → Walk-forward → Regime analysis → Cost/slippage analysis → Paper
observation → Human review` — see §9.

Potential evaluation dimensions (captured as future principles, NOT new functionality):

- Expected Value
- Sharpe
- Drawdown
- Turnover
- Win rate
- Calibration
- Stability
- Robustness across regimes

**Do not implement these as new ACASH functionality in this task.** `GOVERNANCE BOUNDARY`

---

## 6. Quant Engineering Languages

### Source content

C++ · Python · Rust · Java · C · q/kdb+ — framed around quant engineering and different levels of
systems/low-latency work. `SOURCE CLAIM`

### ACASH interpretation

Potential long-term engineering knowledge: C++, concurrency, operating systems, networking, low-latency
systems, systems architecture, Python for research, q/kdb+ concepts for high-performance time-series
workloads. `RESEARCH CANDIDATE (knowledge)`

### Boundary

Do **NOT** optimize ACASH for HFT or low latency merely because these technologies exist. `NOT WHAT THIS
TRACK IS FOR`

```text
OPTIMIZE AFTER MEASURING A REAL BOTTLENECK.
```

Current ACASH execution track is not an HFT implementation. This source is therefore:

```text
LONG-TERM ENGINEERING KNOWLEDGE
```
not
```text
TRADING EDGE
```

---

## 7. 20/80 Level Concept

### Source content

An intraday approach using price levels such as `20` and `80`: price approaches a level, trader watches
for an immediate reaction, enters if the level appears respected, targets relatively small intraday
moves, stops may be moved to break-even after favorable movement. `SOURCE CLAIM`

### ACASH interpretation

```text
FUTURE HYPOTHESIS CANDIDATE   (NO hypothesis ID — MUST NOT be assigned here)
```

Potential research question:

> "Do recurring 20/80 price levels contain statistically significant incremental information about
> short-term reversal/continuation behavior?"

Potential future test design:

```text
P(reversal | level touch)   vs   appropriate control/baseline conditions
```

Any eventual test must account for: spread, slippage, fees, execution assumptions, selection bias,
look-ahead bias, multiple testing, out-of-sample performance. `REQUIRED TEST CONDITIONS`

**IMPORTANT:** This does **NOT** create HYP_003. No hypothesis ID may be assigned in this document.
`GOVERNANCE BOUNDARY`

---

## 8. GEX / 0DTE / Options Positioning

### Source content

gamma exposure, zero-DTE options, open interest, convexity exposure, Delta-Gamma Taylor expansion,
gamma heatmaps, dealer hedging, EMA, flags, volume confirmation. `SOURCE CLAIM`

### ACASH interpretation

Options positioning can influence short-term market behavior. `INFERENCE`

Potential future features: GEX, gamma concentration by strike, expiry structure, 0DTE exposure, open
interest, implied volatility, convexity-related measures, estimated dealer hedging pressure.
`RESEARCH CANDIDATE (features)`

### LIMITATION (must be permanently recorded)

```text
GEX = USEFUL ESTIMATED MARKET-STRUCTURE FEATURE
GEX != GROUND TRUTH OF POSITIONING
```

GEX is a **MODELLED ESTIMATE**, not direct observation of true dealer positioning. Do NOT represent GEX as
"smart money positioning", "exact dealer intent", or "the true market map". `RESEARCH PRINCIPLE`

Sources of uncertainty include: assumptions about dealer positioning; assumptions about hedging;
incomplete visibility of participant books; offsetting positions in other expiries/products; alternative
hedging instruments; changes in volatility; changes in market structure. `UNKNOWN` (magnitude of each in a
given market context)

Potential future research question:

> "Does estimated options positioning provide incremental predictive information after controlling for
> price, volatility, volume, and other baseline features?"

**DO NOT create HYP_003.** `GOVERNANCE BOUNDARY`

---

## 9. Unified Research Architecture

Captured conceptual architecture (FUTURE REFERENCE ONLY — not a request to implement now):

```text
                        ACASH
                          │
                  ┌───────┴───────┐
                  │               │
            Market Data       Alternative Data
                  │               │
           ┌──────┼──────┐   ┌────┼─────┐
           │      │      │   │    │     │
         Price  Volume  Vol  OF  GEX   OI
                                  │
                                  │
                            0DTE Structure
                                  │
                  ┌───────────────┘
                  ▼
            Feature Engineering
                  │
                  ▼
           Hypothesis Testing
                  │
            ┌─────┴─────┐
            │           │
           IS          OOS
            │           │
            └─────┬─────┘
                  ▼
            Walk Forward
                  │
                  ▼
           Regime Analysis
                  │
                  ▼
           Cost / Slippage
                  │
                  ▼
              Paper
                  │
                  ▼
           Human Review
```

This is a FUTURE RESEARCH ARCHITECTURE. It is NOT a request to implement these features now.
`GOVERNANCE BOUNDARY`

---

## 10. Feature != Edge Principle

Recorded explicitly — treat the following as information/features/tools, NOT automatic sources of alpha:

- Order Flow
- Footprint
- GEX
- 0DTE
- EMA
- Volume
- Liquidity
- AI
- Quant models
- Probability visualizations
- 3D visualizations

A candidate feature becomes interesting only if evidence supports:

```text
Feature → Signal → Expected Value → after costs → stable out of sample → stable across regimes →
survives realistic execution assumptions → survives Paper observation
```

Preferred ACASH research question:

> "Does this information add incremental predictive value?"

**NOT:** "Is this tool used by smart money?" **NOT:** "Does this look sophisticated?" **NOT:**
"Does social media claim it works?" `RESEARCH PRINCIPLE`

---

## 11. Research Candidate Ranking

| # | Candidate | Priority | Status |
| :- | :- | :- | :- |
| 1 | Quant OOS / regime testing | VERY HIGH | Research principle |
| 2 | GEX / options positioning | HIGH | Future research candidate |
| 3 | Order Flow | HIGH | Future research candidate |
| 4 | Liquidity / footprint | HIGH | Future research candidate |
| 5 | 20/80 levels | MEDIUM | Future hypothesis candidate — **no hypothesis ID** |
| 6 | EMA + flag + volume | LOW/MEDIUM | Baseline feature candidates |
| 7 | 3D probability visualization | LOW (as a trading feature) | Visualization concept, not edge |
| 8 | C++ / low latency | LONG TERM | Engineering knowledge |
| 9 | GetCracked | LONG TERM | Optional quant-dev/system learning resource — NOT a strategy source |

---

## 12. Execution Track Separation

**Do NOT introduce GEX, Order Flow, Footprint, 20/80, or any new research feature into the E3/E3.5
Paper Engine merely because they were identified here.** E3.6 is infrastructure integration.

```text
RESEARCH TRACK
  ↓ research intake
  ↓ governance
  ↓ hypothesis authorization
  ↓ research/testing
  ↓ qualification

SEPARATE FROM

EXECUTION TRACK
  ↓ E0 → E1 → E2 → E3 → E3.5 → E3.6 → Paper observation
```

Progress in the Execution Track must NOT be interpreted as validation of these research candidates.
`GOVERNANCE BOUNDARY`

---

## 13. Source Quality

For each source, distinguish (recorded for future readers):

1. **What the speaker claims** — always `SOURCE CLAIM`, never upgraded to fact.
2. **What is a reasonable market-structure concept** — `INFERENCE` / `RESEARCH CANDIDATE`.
3. **What remains unproven** — `UNPROVEN`.
4. **What could potentially be tested** — `RESEARCH CANDIDATE` (test design only; no authorization).
5. **What ACASH should NOT conclude** — explicit negative boundaries (e.g., GEX ≠ ground truth, order
   flow ≠ edge, model ≠ performance, tool ≠ alpha).

Evidence vocabulary used throughout this document:
`FACT` · `SOURCE CLAIM` · `INFERENCE` · `RESEARCH CANDIDATE` · `UNPROVEN` · `UNKNOWN`

Educational/social-media claims are **never** converted into facts by this document.

---

## 14. What ACASH Should Test Eventually

(Research-track direction only; requires governance authorization before implementation.)

- Whether any candidate feature adds **incremental predictive value** over baseline (price, volume,
  volatility) — per §5 and §10.
- Out-of-sample / walk-forward stability and regime robustness of any candidate signal.
- GEX / options-positioning features: does estimated options positioning provide incremental predictive
  information after controlling for baseline features?
- Order-flow / footprint / liquidity features: incremental predictive value of flow imbalance, footprint
  dynamics, displayed liquidity changes.
- 20/80 levels (if ever pursued under a proper hypothesis): reversal probability conditional on level
  touch versus appropriate controls, with full cost/selection/look-ahead/multiple-testing corrections.

All of the above remains **Future Research Candidates** until governance authorizes formal hypothesis
status.

---

## 15. What ACASH Must NOT Assume

```text
- Order flow is an automatic edge
- GEX is ground truth of dealer positioning / "smart money" intent
- Better information always produces better performance
- A clean quant pipeline or model quality guarantees performance
- Historical relationships remain stable out of sample / across regimes
- Source claims from social-media content are empirical evidence
- Execution Track progress validates these research candidates
- This document authorizes any research or trading activity
```

`FACT` (as recorded governance/stance documents; binding via this intake and AGENTS.md).

---

## 16. Governance Confirmation

This document:

- Creates **NO** hypothesis ID and does **NOT** create HYP_003.
- Modifies **NO** existing hypothesis, mechanism (MEC-0011/0013), or registry.
- Starts **NO** research activity (R1 remains NOT STARTED).
- Modifies **NO** governance construct: D17-E = HOLD; MEC-0013 = ARCHIVED / Option C; HYP_003 = NOT
  CREATED; R1 = NOT STARTED; Backtest = LOCKED; Live = LOCKED; Capital = $0.
- Changes **NO** production, application, infrastructure, strategy, E3/E3.5/E3.6, feed, dependency, or
  configuration.
- Is a durable knowledge-capture artifact in `docs/research/` addressing:
  `FEATURE != EDGE. INFORMATION != PREDICTIVE VALUE. MODEL != PERFORMANCE.`

---

*EOF — Research intake captured without governance movement.*