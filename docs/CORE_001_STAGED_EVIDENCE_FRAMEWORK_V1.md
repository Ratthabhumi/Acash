# CORE-001 Staged Evidence Framework v1

**Document:** `docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md`
**Status:** AUTHORIZED GOVERNANCE STRUCTURE (human-ratified, pre-prospective)
**Ratified:** before prospective Observation #0001 (observed count = 0 at ratification)
**Scope:** governance / documentation only. No strategy, threshold, or authority change beyond what is stated here.

Labels used: CURRENT FACT | AUTHORIZED GOVERNANCE STRUCTURE | HARD GATE |
NON-DECISIVE CHECKPOINT | REQUIRES SEPARATE HUMAN AUTHORIZATION

---

## 1. Purpose

CURRENT FACT: CORE-001's current hypothesis is HYP_011 — Global 80/20
Strategic Allocation Core (ACWI 80% / AGG 20%; SPY = independent gating
benchmark). Historical status:
`HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW` (corrected
authority commit `77f5610ce63015f014c5283980a01a48536f5841`).

AUTHORIZED GOVERNANCE STRUCTURE: this framework stages the path from
historical support to possible live authorization as discrete,
fail-closed evidence stages. It answers *"what evidence is required
before the next authorization may even be considered"* — never *"is the
strategy profitable."*

Short prospective evidence is NOT a miniature backtest used to select a
winner. S1/S2 exist primarily to validate prospective operational
integrity, identify implementation/data/accounting failures, detect
catastrophic contradictions, and establish evidence sufficient to
consider paper execution. The framework must not create pressure to
optimize on 20/60-session performance, require short-period SPY
outperformance, or change HYP_011 after observing short-window outcomes.

---

## 2. Authority scope / non-authority

AUTHORIZED GOVERNANCE STRUCTURE: stage structure, stage semantics,
S2 quantitative guardrails (§5), transition and breach semantics,
CORE-002 parallel-research rule, no-moving-goalposts rule.

NOT AUTHORIZED NOW: paper execution, live execution, real capital,
automatic paper/live transitions, HYP_011 tuning, S3 numeric execution
limits, live capital amount, any falsification verdict on HYP_011.

Current authorities (unchanged by this amendment):
`PAPER_AUTHORIZED=false`, `LIVE_AUTHORIZED=false`, `LIVE_LOCKED=true`,
`REAL_CAPITAL=$0.00`, `NO_REAL_ORDERS=true`.

---

## 3. Current status

CURRENT FACT:
- Scientific prospective boundary: 2026-09-25 →
  `MISSED_UNOBSERVED_DUE_TO_AUTHORIZATION_LOCK` (no backfill permitted).
- Operational activation: 2026-09-28. Observation #0001 target: canonical
  session 2026-09-28 (open 13:30 UTC = execution semantics; close
  20:00 UTC = observation eligibility, strictly after close).
- Observed eligible sessions = 0; completed scheduled annual
  rebalances = 0. Current stage = PRE-S1 / awaiting Observation #0001.
- Canonical main pin: `d9608c0a2353bd5ed41943e5fb893ef9648089d2`.
- Corrected historical baseline (descriptive): start $100,000 → end
  218852.857740; total return 1.1885285774; Sharpe 0.7082199886;
  max drawdown 0.27068044647.

---

## 4. Stage S0 — Historical support

CURRENT FACT: `HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW`.
Meaning: prerequisite for prospective observation; historical support
only. NOT paper authorization, NOT live authorization, NOT proof of
future profitability.

---

## 5. Stage S1 — Operational sanity (ratified exact semantics)

AUTHORIZED GOVERNANCE STRUCTURE. Window: first 20 ACTUALLY OBSERVED
eligible sessions. S1 completes only after 20 actually observed sessions
AND every expected eligible session through the 20th observed session is
accounted for as OBSERVED or explicitly MISSED/UNOBSERVED with
adjudication. An adjudicated miss stays MISSED: no count increment, no
reconstruction, no silent backfill.

Purpose: prove the prospective machinery works on genuinely new
sessions. Primary focus: operational/integrity evidence, NOT
short-window profitability.

HARD GATE (all conjunctive): 20 observed sessions accounted; misses
adjudicated; no silent backfill; no duplicate ordinal/session; no
state-chain corruption; atomic observation/state write+seal succeeds;
Alpaca raw/split provenance satisfies frozen contract; corporate-action
treatment follows frozen economic-relevance rules;
cash/position/receivable/equity reconciliation coherent; SPY benchmark
independent; `NO_REAL_ORDERS=true` throughout; paper false; live
locked; capital $0; no unresolved implementation defect capable of
invalidating performance evidence; no unauthorized
strategy/architecture/accounting/CA/state/timing modification.

If all pass: `OPERATIONALLY_SANE`. This does NOT mean profitable, paper
authorized, live eligible, or future profitability proven. S1 has NO
profitability gate (report performance descriptively only).

---

## 6. Stage S2 — Short prospective qualification

### 6.1 Window semantics (corrected)

AUTHORIZED GOVERNANCE STRUCTURE: S1 checkpoint = after 20 actually
observed sessions. S2 accumulation continues Observations 21–60. BUT the
S2 qualification decision at Observation 60 uses the COMPLETE first
60-observed-session window: Observations 1–60 inclusive. S2 window
length = exactly 60 ACTUALLY OBSERVED eligible sessions — NOT a
40-session window. Misses do not count, must be adjudicated, and delay
qualification until 60 sessions are actually observed. All S2 metrics
use the full 60-session sequence plus the equity immediately preceding
Observation #1 (same convention as the historical calibration).

### 6.2 Ratified hard performance safety guardrails

At the 60-observed-session checkpoint (all HARD GATE, conjunctive):

- **G-S2-P1 — Maximum drawdown: PASS requires 60-session MDD < 25.0%.**
  BLOCK on >= 25.0%. Includes pre-Observation-#1 equity; frozen
  peak-to-trough semantics; no future observations.
- **G-S2-P2 — Cumulative return floor: PASS requires 60-session
  cumulative return > -20.0%.** BLOCK on <= -20.0%
  (`equity_after_obs_60 / equity_before_obs_1 - 1`). Emergency
  contradiction/safety floor — NOT a positivity, Sharpe, or
  SPY-outperformance requirement.
- **G-S2-P3 — Single-session extreme loss: PASS requires no daily
  portfolio return <= -10.0% within Observations 1–60.** Any breach →
  `PAPER_ELIGIBILITY_BLOCKED_PENDING_HUMAN_REVIEW` — even if verified a
  genuine market event. Explanation determines root cause
  (market / corporate action / accounting / data / provenance /
  implementation / state / other / UNKNOWN); a valid explanation does
  NOT auto-waive the boundary. Only a later explicit human governance
  decision may adjudicate progression.
- **G-S2-P4 — Evidence/anomaly integrity: PASS requires no unresolved
  material anomaly** (return, accounting, provenance, CA, state,
  implementation). Any unresolved material anomaly →
  `EVIDENCE_INVALID_OR_BLOCKED`, prevents `PAPER_ELIGIBLE`.

### 6.3 S2 integrity gates (all 24 conjunctive)

S1 `OPERATIONALLY_SANE` validly issued; 60 actually observed sessions;
every expected session accounted for; no silent backfill; no
look-ahead; no duplicate ordinal/session; state chain intact; sealing
intact; market-data provenance valid; CA handling per frozen contract;
accounting reconciles; SPY independent; strategy frozen; no
unauthorized material change; no unresolved evidence-invalidating
defect; `NO_REAL_ORDERS=true`; paper unauthorized; live locked; capital
$0.00; G-S2-P1..P4 pass. No compensating score, no weighted average, no
software override.

### 6.4 Diagnostic-only metrics (MUST report, MUST NOT gate)

Annualized Sharpe; return sign (beyond the -20% floor); SPY
relative performance; realized volatility; stress-path relative
performance; historical percentile location. In particular NOT
required: Sharpe > 0, Sharpe ≥ 0.5, return > 0, return > SPY, lower
drawdown than SPY over 60 sessions. Historical G1–G6 criteria are NOT
short-horizon S2 gates.

---

## 7. S2 decision state machine

- Evidence/integrity invalid → `EVIDENCE_INVALID_OR_BLOCKED`
- Evidence valid but G-S2-P1/P2/P3 breached →
  `PAPER_ELIGIBILITY_BLOCKED_PENDING_HUMAN_REVIEW`
- S1 prerequisite unmet → `S1_NOT_QUALIFIED`
- Fewer than 60 observed → `S2_INSUFFICIENT_OBSERVATIONS`
- All S1 + integrity + P1..P4 pass → `PAPER_ELIGIBLE`

`PAPER_ELIGIBLE != PAPER_AUTHORIZED`. `PAPER_AUTHORIZED` remains FALSE
until separate explicit human authorization. No software component may
convert eligibility to authorization automatically. A guardrail breach
is NOT `HYP_011_FALSIFIED` unless an independently ratified
falsification rule says so; no rescue tuning permitted.

---

## 8. Stage S3 — Paper validation

REQUIRES SEPARATE HUMAN AUTHORIZATION: `PAPER_ELIGIBLE` → explicit
human paper authorization → `PAPER_AUTHORIZED=true` → S3 may begin. No
process may submit/activate/pre-authorize/schedule paper execution now.
Purpose: validate execution-system behavior shadow observation cannot
exercise (order construction, broker API, fills, slippage, rejects,
partial fills, reconciliation, restart/recovery, duplicate protection,
idempotency, stale-state, restriction/kill, scheduling reliability).
Strategy stays frozen; no tuning on paper performance. Success →
`CORE_001_OPERATIONALLY_VALIDATED_IN_PAPER` (NOT live authorization).
Paper failures are root-caused first
(DATA/ACCOUNTING/EXECUTION/BROKER/INFRASTRUCTURE/GOVERNANCE/STRATEGY-PERFORMANCE/UNKNOWN;
UNKNOWN fails closed) — never silently treated as strategy failure.

Future paper-execution authorization package must bind (minimum):
broker/environment identity, account, symbols, order types, max notional,
idempotency, reconciliation, restart/recovery, stale-data, rejects,
partial fills, restriction/kill, scheduler ownership, credential
authority, audit/logging, explicit NO REAL ORDER boundary. (Not created
by this amendment.)

---

## 9. Stage S4 — Intermediate checkpoints (NON-DECISIVE CHECKPOINT)

126 observed eligible sessions (~six market months) and 252 (~one market
year). Report: cumulative return, annualized Sharpe, max drawdown,
realized volatility, stress behavior, SPY-relative behavior,
turnover/rebalance behavior, operational incidents, shadow/paper
divergence, rebalance/accounting continuity. They do NOT authorize
live, terminate HYP_011, trigger optimization, or permit retrospective
threshold changes. Warranted redesign → NEW hypothesis, never rescue
tuning.

---

## 10. Stage S5 — Long-horizon confirmation

Preserved: >= 504 ACTUALLY OBSERVED eligible sessions AND >= 2
completed scheduled annual rebalances. Misses, synthetic sessions,
backfills never count; initial allocation is not a scheduled rebalance.
Characterized as HIGH-CONFIDENCE LONG-HORIZON CONFIRMATION (it is not a
pre-paper waiting room — paper eligibility lives at S2). Completion
permits `LIVE_ELIGIBILITY_REVIEW`; never auto-authorizes live.

---

## 11. Stage S6 — Live capital authorization

REQUIRES SEPARATE HUMAN AUTHORIZATION: separate review + explicit
authorization; no automatic transition from S5 or paper. Current:
`LIVE_AUTHORIZED=false`, `LIVE_LOCKED=true`,
`REAL_CAPITAL_AUTHORITY_USD=0.00`, `NO_REAL_ORDERS=true`. No live
dollar amount ratified. Future first deployment intends a deliberately
small capital tier (amount NOT invented here); future package must bind
capital cap, max notional, max daily loss, drawdown kill, allowlist,
restriction policy, suspension/reactivation governance.

---

## 12. Observation accounting semantics

OBSERVED ELIGIBLE SESSION ≠ EXPECTED ELIGIBLE SESSION ACCOUNTED FOR.
S1 needs 20 actually observed + all expected sessions through the 20th
accounted for; S2 needs 60 actually observed + all expected through the
60th accounted for. Adjudicated misses stay in the operational record
but never increment the observed counter. The 2026-09-25 session stays
`MISSED_UNOBSERVED_DUE_TO_AUTHORIZATION_LOCK` forever.

---

## 13. Failure / breach semantics

- Evidence/implementation failure (corrupt chain, duplicate, accounting
  mismatch, invalid provenance, missing CA authority, evidence-affecting
  defect, unauthorized backfill, look-ahead) →
  `EVIDENCE_INVALID_OR_BLOCKED`: fail closed, stop progression, preserve
  evidence, require human adjudication. NOT automatic falsification.
- Performance guardrail breach (valid evidence) →
  `PAPER_ELIGIBILITY_BLOCKED_PENDING_HUMAN_REVIEW`: no
  `PAPER_ELIGIBLE`, no auto-paper, preserve everything, no tuning, no
  automatic falsification.
- S1 operational failure → no `OPERATIONALLY_SANE`; human adjudication
  required.

---

## 14. No mid-stage moving goalposts

Once S1 begins its requirements may not be weakened on observed S1
outcomes. S2 quantitative guardrails were ratified before S2 begins; no
S2 threshold may be created/weakened after observing S2 performance and
applied retroactively. Amendments are additive, timestamped,
prospective-only unless explicitly justified. If a material S2 rule is
unratified when S2 would begin, S2 progression is BLOCKED — never invent
a threshold at runtime.

---

## 15. CORE-002 parallel research + information barrier

CORE-002 MAY proceed in parallel once CORE-001 runs shadow/paper — but
only as a separately preregistered hypothesis/family with independent
thesis, contracts, partitions, gates; never a rescue/tweak of HYP_011.
Post-freeze CORE-001 prospective outcomes must not optimize CORE-002
unless predeclared in CORE-002's design. Permitted: independent
hypothesis/rationale/partitions/preregistration, strategy-neutral
infrastructure reuse. Not permitted: choosing rules to fix a recent
CORE-001 loss, tuning against CORE-001 prospective observations, or
opportunistic use of CORE-001 paper failures. CORE-002 gains no
paper/live authority from CORE-001's.

---

## 16. Calibration evidence (pre-prospective, descriptive)

Source: sealed corrected HYP_011 ledgers (`data/hyp_011/equity_baseline.json`
SHA `fa626c32…`, `equity_stress.json` SHA `55599c68…`, manifest
`HYP_011_R3_CORRECTED_REPRODUCIBILITY_RESULT.json`), 2264 sessions
2016-01-04→2024-12-31. Rolling N-session windows use N consecutive
eligible sessions + pre-window equity (100000 analytical for window 0;
the initial $100,000 is not a standalone pre-session ledger row — its
value is encoded by frozen starting-AUM semantics and the first-row
running peak). Frozen Sharpe (252/ddof=1/rf=0), frozen MDD, vol =
sample stdev × √252. Single-session breach counts = 60-session windows
containing ≥1 daily return below the threshold (NOT day counts).

| Window | Cumret min | Cumret p1/p5 | MDD p95/p99/max | Worst daily |
|---|---|---|---|---|
| 20 (2245w) | -25.67% | p5 -4.81% | max 25.67% | — |
| 60 (2205w) | -24.86% | p1 -14.49%, p5 -8.71% | p95 13.73%, p99 = max 27.07% | -8.649% (2020-03-16) |
| 126 (2139w) | -20.10% | — | max 27.07% | — |
| 252 (2013w) | -21.50% | — | max 27.07% | — |
| Stress 60 (2205w) | -24.87% | — | max 27.08% | -8.652% |

Threshold context: MDD strictly >25% in 43/2205 ≈ 1.95%; cumret
strictly <-20% in 6/2205 ≈ 0.27%; no calibrated 60-session window
contained a daily return strictly below -10% (windows containing a
daily <-5%: 67; <-7.5%: 62).

RATIFIED (predeclared before Observation #1, from human authority, not
optimized): **MDD < 25%**, **cumret > -20%**, **every daily > -10%**.
These are conservative safety boundaries, not optimal targets,
predictions, or robustness proofs.

---

## 17. Pre-observation non-contamination assertion

CURRENT FACT: this framework and its S2 thresholds were ratified while
prospective observed count was 0; Observation #0001 NOT yet observed; no
prospective result used; calibration used only sealed historical
artifacts; zero new market-data access during calibration or
ratification. This ordering must never be rewritten as post-Observation.

---

## 18. Ratified vs not-authorized (summary)

AUTHORIZED NOW: framework structure; S1 = 20 observed; S2 = full
60-observed window (Obs 1–60); S2 gates MDD<25% / cumret>-20% /
daily>-10% + 24 integrity gates + breach/decision semantics; 126/252
checkpoints; 504+2 long-horizon rule; CORE-002 allowance with barrier.
NOT AUTHORIZED NOW: paper/live/real capital/auto-transitions/tuning/S3
numeric limits/live amount.

---

*End of canonical document. Amendments must be additive and separately ratified.*
