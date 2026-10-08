# HYP011 V3 proposal and availability preparation

Status: proposed, unratified, undeployed. Preserve the production runtime
`6395b384893ac0160b4ce8df3f4bcc0d332b3d9e`. This task does not inspect or
change the host, `/home/mew/Acash`, systemd, secrets, external state or timers.

The [V2 closure dossier](../audit/HYP011_V2_OBS1_FORENSIC_CLOSURE_20261007.md)
records host offline at dispatch, no observation and zero sample advancement.
These are verified repository record contents, not freshly collected host
telemetry. Preserve its 2026-10-05 authority/intent as retired evidence;
never replay them. V1 Observation #1 and all economic seals remain immutable.

## Scientific decision surface

| Design | Comparability | Operational robustness | Cost |
|---|---|---|---|
| Fresh independent contiguous segment; any miss terminates | Preserves existing observed-session economics, no ambiguous gap dividend/peak bridge | Requires host availability; restart needs fresh preregistration, not automated selection | Smallest change; may waste segments under repeated outages |
| Preregister missing-session protocol | Requires a new estimand and explicit dividend, return-path and drawdown treatment; observed subset is not the old contiguous sample | Can represent missingness, but missing-not-at-random availability can bias interpretation | New scientific experiment and considerably more validation |

Recommend the **fresh contiguous segment**, conditional on availability being
demonstrated first. Do not repeatedly restart until a favorable path appears;
register all terminated segments and attempts so survivorship/optional-stopping
effects remain visible. No pooling V1/V2/V3, no post-result parameter changes,
no rescue of old hypotheses. A missing-session protocol remains a separately
ratified experiment, not a patch that retroactively changes V1/V2.

Frozen economics reuse `shadow_ops.build_initial_state` and
`validate_initial_state`: simulated AUM 100000.00, zero holdings/receivables,
empty hash chain and zero observations. Real capital remains 0.00 with paper/live
false and NO_REAL_ORDERS true. No change to allocations, instruments, friction,
corporate-action authority, sample targets or acceptance gates.

The [unissued proposal](HYP011_V3_UNISSUED_PROPOSAL.json) leaves session/runtime
unresolved. Offline `shadow_v3_preparation.prepare_initial_state` checks fresh
V3 namespaces, future trading session, no inherited state/authority, locks and
no-catchup policy, then returns a state **preview** using canonical helpers.
It issues no authority, creates no state file and has no runner integration.
`assess_missing_observation` returns an advisory missingness classification,
never advances a sample, and never concludes host offline from a missing file.

## Availability and post-boot reconciliation design

Keep empirical timer `Persistent=false`. Derive schedule from canonical
`candidate_schedule_time`: calendar close +15 minutes SIP delay +5 minutes
margin; handle NYSE holidays, half-days and DST in UTC. After the scheduled
dispatch, missing evidence is unconfirmed; at the **next trading session open**
it becomes MISSED_UNOBSERVED under F14. Neither case initiates provider requests.

Proposed independent monitoring contract (not installed):

- A separately powered observer records UTC heartbeat receive times, missing
  heartbeat intervals and its own availability. Heartbeat gaps are evidence of
  unreachability, not proof of power loss. No API credentials or market calls.
- Operator defines sampling interval and availability acceptance criteria before
  V3 ratification. Record host boot ID, journal continuity, time synchronization,
  timer next/last trigger and service invocation locally. Alert destination and
  any hosting cost need their own authorization; nothing sends alerts here.
- Post-boot, inspect intended target/deadline, actual observation bytes/chain,
  authority/attempt ledger, timer/service journal and boot intervals. Write a
  separate immutable forensic record via existing evidence writer after review;
  do not mutate scientific state/observation count. Preserve raw contradictory
  evidence; absent observation does not prove absent request/attempt.
- No catch-up, automatic re-arm, retry, or state advancement. A missed segment
  terminates; a replacement requires fresh future session, pre-open intent and
  separately issued authority. Do not reuse this preview as a dispatch record.

Known immediate bottleneck in the closure record: **host availability**.
Underlying cause (mains failure, PSU/hardware, operator shutdown, BIOS behavior,
network outage) is **UNKNOWN** in this task. Before spending, collect UPS/router
and host event evidence; safely inspect BIOS AC-restoration setting and physical
power situation with the operator. BIOS auto-power-on/UPS can mitigate power
events but do not prove reliable uptime. External hosting is a later cost/privacy
decision, not an assumed cure. Require an independent availability rehearsal
over intended dispatch times before committing another prospective segment.

## Future operator deployment boundary

First ratify a new V3 contract and fix a genuinely future session, unique segment,
state/authority namespace, exact tested runtime and economic locks. The current
runner/activation validator explicitly accepts **V2**, so these templates are
**not deployment-ready**. A dedicated reviewed V3 runner/authority integration,
full hermetic CI, preflight evidence and rollback plan are prerequisites, not
permission to rename V2 artifacts. Do not run the V2 wrapper for V3.

Only after separate deployment/activation authorization may the operator
prepare a new isolated host checkout, fresh external root and reviewed units;
verify the existing pin/units/state first, preserve rollback artifacts, perform
zero-network preflight, then separately authorize/arm the approved future
observation. No deployment command is supplied as though the missing V3 runner
already existed. Homelab deployment and V3 activation remain **NOT_AUTHORIZED**.
