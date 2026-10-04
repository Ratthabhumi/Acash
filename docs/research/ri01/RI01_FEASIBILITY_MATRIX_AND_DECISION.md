# RI-01 Feasibility Matrix and Decision (ZERO-OUTCOME)

**Network requests performed**: 0. **Outcome metrics computed**: 0.
All provider facts below are `PROVEN_IN_REPO` or `UNKNOWN` (see
`RI01_PROVIDER_FEASIBILITY.md`). No assumption was converted into a PASS.

## 1. Matrix

| # | Requirement | Source | Available? | Deterministic? | PIT safe? | Cost | Blocker | Evidence | Verdict |
|---|-------------|--------|------------|----------------|-----------|------|---------|----------|---------|
| R1 | Instrument universe | Governance (to freeze) | Partial | Yes | Yes | $0 | Universe choice unmade | R0 intake §9 | `PASS_WITH_LIMITATION` |
| R2 | Exchange calendar CA-1 | In-repo | Yes | Yes | Yes | $0 | None | `NyseCa1Calendar`, hermetic tests herein | `PASS` |
| R3 | Session open semantics | In-repo | Yes | Yes | Yes | $0 | None | CA-1 + tests herein | `PASS` |
| R4 | Previous close authority | Alpaca (auction vs daily) | Unknown | Unknown | Unknown | Unknown | **Contract test unexecuted** | MEC-0014 §10.2 | `BLOCKED` |
| R5 | Opening print semantics | Trade/auction authority | Unknown | Unknown | Unknown | Unknown | **No trade-level authority** | This pack §1 | `BLOCKED` |
| R6 | RTH-complete 1Min raw | Alpaca SIP | Unknown (RI-01 scope) | In-principle | Unknown | Unknown | **Coverage/entitlement/depth unverified** | MEC-0015 (6 SPY sessions only) | `BLOCKED` |
| R7 | Daily bars | Alpaca SIP | Partial (1Day path exists, narrow) | Yes | Partial | Unknown | Depth/entitlement unverified | HYP_011 qual client | `PASS_WITH_LIMITATION` |
| R8 | Per-minute volume | Alpaca SIP | Unknown (RI-01 scope) | In-principle | Unknown | Unknown | Same as R6 | — | `BLOCKED` |
| R9 | TZ/DST handling | In-repo | Yes | Yes | Yes | $0 | None | CA-1 + tests herein | `PASS` |
| R10 | Corporate actions | Alpaca `/v1/corporate-actions` | Partial | Partial | **No (vintage)** | Unknown | **PIT vintage not guaranteed** | MEC-0015 §7.3 | `BLOCKED` |
| R11 | Symbol lifecycle | Vendor master | Unknown | Unknown | Unknown | Unknown | **Never contract-tested** | — | `BLOCKED` |
| R12 | Missing-bar policy | Governance | Yes (defined) | Yes | Yes | $0 | None | `FAIL_CLOSED_SESSION_EXCLUSION` | `PASS` |
| R13 | Per-field PIT proofs | Contract tests | No | — | — | $0 | **Unexecuted by design here** | `RI01_POINT_IN_TIME.md` | `BLOCKED` |
| R14 | Provider delay semantics | Alpaca SIP rules | Unknown (minute path) | — | Unknown | $0 | **Unverified for 1Min** | HYP_011 daily-path rule only | `BLOCKED` |
| R15 | Revision behavior | Vendor re-fetch test | Unknown | Unknown | Unknown | Unknown | **Never tested** | — | `BLOCKED` |

Verdict key: `PASS` (proven) / `PASS_WITH_LIMITATION` (proven-narrow, needs widening) /
`BLOCKED` (known gap with a designed test) / `UNKNOWN` (not yet characterized).

## 2. Decision

```text
RI01_DATA_FEASIBILITY = RI01_DATA_FEASIBILITY_INSUFFICIENT_EVIDENCE
```

Rationale: methodology is CONSTRUCTIBLE (calendar, bar semantics, exclusion
policy, PIT labelling, evidence envelope are all defined and partly proven),
but 8 of 15 requirements are `BLOCKED` on evidence that can only be produced
by entitled network probes executed under separate authorization. This pack
deliberately performed zero of those probes. Nothing here justifies PASS; and
nothing proves impossibility either, so BLOCKED would overclaim — the honest
state is insufficient evidence with a precise shopping list (§3 below).

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
