# RI-01 Feasibility Matrix and Decision (ZERO-OUTCOME)

**Network requests performed**: 0. **Outcome metrics computed**: 0.
All provider facts below are `PROVEN_IN_REPO` or `UNKNOWN` (see
`RI01_PROVIDER_FEASIBILITY.md`). No assumption was converted into a PASS.

## 1. Matrix

Availability is NOT one field. Each requirement is classified on five
independent axes; collapsing them would hide exactly the evidence gaps that
matter. `UNKNOWN` means uncharacterized (never convert to PASS by assumption).

| # | Requirement | API_CAPABILITY | ENTITLEMENT | COVERAGE | PIT_SAFETY | REVISION | OVERALL |
|---|-------------|----------------|-------------|----------|------------|----------|---------|
| R1 | Instrument universe | n/a (governance) | n/a | n/a | n/a | n/a | `PASS_WITH_LIMITATION` (choice unmade) |
| R2 | Exchange calendar CA-1 | Proven in-repo | n/a | Full (2013–2026) | Proven | n/a | `PASS` |
| R3 | Session open semantics | Proven in-repo | n/a | Full | Proven | n/a | `PASS` |
| R4 | Previous close authority | Testable path (trades + O/6 conditions documented) | Unknown | Unknown | Unknown | Unknown | `BLOCKED` (contract test unexecuted) |
| R5 | Opening print semantics | Testable path (trades + O/Q conditions documented) | Unknown | Unknown | Unknown | Unknown | `BLOCKED` (no trade-level authority yet) |
| R6 | RTH-complete 1Min raw | **Documented** (1Min/sip/raw) | Unknown | Unknown (RI-01 scope; 6 SPY sessions proven) | Unknown | Unknown | `BLOCKED` |
| R7 | Daily bars | **Documented** + narrow in-repo path | Unknown | Partial (narrow) | Partial | Unknown | `PASS_WITH_LIMITATION` |
| R8 | Per-minute volume | **Documented** (same endpoint) | Unknown | Unknown (RI-01 scope) | Unknown | Unknown | `BLOCKED` |
| R9 | TZ/DST handling | Proven in-repo | n/a | Full | Proven | n/a | `PASS` |
| R10 | Corporate actions | **Documented with warning** (no creation-time guarantee) | Unknown | Partial | **No** (historical vintage unrecoverable; SSE prospective path unimplemented) | **No** (historical) | `BLOCKED` |
| R11 | Symbol lifecycle | **Documented** (asof + rename-day lag admitted) | Unknown | Unknown | Unknown (lag) | n/a | `BLOCKED` (contract test unexecuted) |
| R12 | Missing-bar policy | Defined (`FAIL_CLOSED_SESSION_EXCLUSION`) | n/a | n/a | n/a | n/a | `PASS` |
| R13 | Per-field PIT proofs | Methodology defined | n/a | n/a | Unexecuted by design | n/a | `BLOCKED` |
| R14 | Provider delay semantics | **Documented** (historical SIP `end` ≥ 15 min) | Unknown (credential-specific) | n/a | n/a | n/a | `PASS_WITH_LIMITATION` (bounded verification still needed) |
| R15 | Revision behavior | Untested | Unknown | Unknown | Unknown | Unknown | `BLOCKED` |

OVERALL key: `PASS` (proven) / `PASS_WITH_LIMITATION` (proven-narrow or
documented-but-unverified-in-our-tier, needs widening) / `BLOCKED` (known
gap with a designed test).

Count: 8 `BLOCKED` (R4, R5, R6, R8, R10, R11, R13, R15), 3
`PASS_WITH_LIMITATION` (R1, R7, R14), 4 `PASS` (R2, R3, R9, R12).
R14 moved out of `BLOCKED` on the now-quoted official FAQ wording
(historical SIP `end` ≥ 15 min); every other row keeps its prior verdict —
nothing was regraded merely to shrink the count.

## 2. Decision

```text
RI01_DATA_FEASIBILITY = RI01_DATA_FEASIBILITY_INSUFFICIENT_EVIDENCE
```

Rationale: methodology is CONSTRUCTIBLE (calendar, bar semantics, exclusion
policy, PIT labelling, evidence envelope are all defined and partly proven),
and official documentation now settles API capability for minute bars,
SIP delay, asof mapping, trade conditions, and the CA vintage warning — but
8 of 15 requirements remain `BLOCKED` on evidence that can only be produced
by entitled network probes executed under separate authorization
(entitlement, RI-01-scope coverage, close/open authority, lifecycle and PIT
contracts, revision behavior). This pack deliberately performed zero of those
probes. Nothing here justifies PASS; and nothing proves impossibility either,
so BLOCKED would overclaim — the honest state is insufficient evidence with
a precise shopping list (§3 below).

## 3. Evidence that would change the decision (authorized probes, NOT done here)

1. Entitlement + depth + coverage + stability + revision + cost probes
   (`RI01_PROVIDER_FEASIBILITY.md` §3), date- and symbol-bounded.
2. Prior-close authority contract test (auction cross vs daily close).
3. Symbol-lifecycle + dividend-vintage contract review.
4. Each probe recorded under `RI01_EVIDENCE_CONTRACT.md` envelopes.

## 4. Next phase

```text
NEXT_PHASE = HOLD (preregistration NOT proposed yet)
```

If the probes above ever flip every `BLOCKED` row, the NEXT separate phase
would be `RI-01 PREREGISTRATION`, freezing hypothesis, features, signal,
timing, universe, exclusions, thresholds, cost model, metrics, sample split,
and falsification criteria BEFORE any outcome evaluation. That phase is
neither proposed nor executed here.

## 5. Safety ledger

- `HOMELAB_MODIFIED = false`, `HYP011_MODIFIED = false`
- `REAL_CAPITAL_AUTHORITY = $0.00`, `PAPER_TRADING_AUTHORITY = false`,
  `LIVE_TRADING_AUTHORITY = false`, `NO_REAL_ORDERS = true`
- `NETWORK_REQUESTS_PERFORMED = 0`, `OUTCOME_METRICS_COMPUTED = 0`
- No broker orders, no PPDS real financial data, no HYP_011 changes.
